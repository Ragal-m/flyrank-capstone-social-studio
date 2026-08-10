from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import migrate
from .fake_platform import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    yield


app = FastAPI(title="FlyRank Fake Social Platform", lifespan=lifespan)
app.include_router(router)
