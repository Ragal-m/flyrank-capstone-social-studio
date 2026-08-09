import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, status

from .db import migrate
from .fake_platform import router as fake_platform_router
from .models import CampaignCreate, CampaignView, DeliveryEvent
from .repository import apply_delivery_event, queue_campaign_now, save_token
from .security import encrypt_token, fresh_timestamp, verify_signature
from .service import create_campaign, get_campaign
from .settings import get_settings
from .worker import worker_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    save_token("instagram", encrypt_token("fake-token-instagram"))
    save_token("x", encrypt_token("fake-token-x"))
    stop = asyncio.Event()
    task = None
    if get_settings().enable_worker:
        task = asyncio.create_task(worker_loop(stop))
    yield
    stop.set()
    if task:
        await task


app = FastAPI(title="FlyRank Social Studio", version="1.0.0", lifespan=lifespan)
app.include_router(fake_platform_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/campaigns", response_model=CampaignView, status_code=status.HTTP_201_CREATED)
def create_campaign_route(data: CampaignCreate) -> CampaignView:
    return create_campaign(data)


@app.get("/campaigns/{campaign_id}", response_model=CampaignView)
def campaign_route(campaign_id: str) -> CampaignView:
    try:
        return get_campaign(campaign_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/campaigns/{campaign_id}/publish", status_code=status.HTTP_202_ACCEPTED)
def publish_campaign_route(campaign_id: str) -> dict:
    try:
        get_campaign(campaign_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    queued = queue_campaign_now(campaign_id)
    return {"campaign_id": campaign_id, "queued_posts": queued}


@app.post("/webhook/social-delivery")
async def delivery_webhook(
    request: Request, x_social_signature: str = Header(default="")
) -> dict:
    body = await request.body()
    if not verify_signature(body, x_social_signature):
        raise HTTPException(status_code=400, detail="invalid webhook signature")
    try:
        event = DeliveryEvent.model_validate_json(body)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="invalid webhook body") from error
    if not fresh_timestamp(event.timestamp):
        raise HTTPException(status_code=400, detail="stale webhook")
    try:
        applied = apply_delivery_event(
            event.event_id,
            event.idempotency_key,
            event.platform_post_id,
            event.status,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"accepted": applied}


