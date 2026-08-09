import uuid

from .content import compose_caption, create_variants
from .models import CampaignCreate, CampaignView, Platform
from .repository import campaign, create_campaign_records


def create_campaign(data: CampaignCreate) -> CampaignView:
    campaign_id = str(uuid.uuid4())
    images = create_variants(campaign_id)
    captions: dict[Platform, str] = {
        platform: compose_caption(platform, data.title, data.body, str(data.url))
        for platform in ("instagram", "x")
    }
    create_campaign_records(campaign_id, data, captions, images)
    return get_campaign(campaign_id)


def get_campaign(campaign_id: str) -> CampaignView:
    value = campaign(campaign_id)
    if value is None:
        raise LookupError("campaign not found")
    return CampaignView.model_validate(value)


