from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import Platform
from .settings import get_settings


PLATFORM_SPECS = {
    "instagram": {"size": (1080, 1080), "label": "INSTAGRAM"},
    "x": {"size": (1600, 900), "label": "X"},
}

BRAND_VOICE = "Clear, useful, confident, and free of hype."
PLATFORM_RULES = {
    "instagram": "Warm storytelling, short paragraphs, and three relevant hashtags.",
    "x": "Direct and energetic, no more than 280 characters, one strong takeaway.",
}


def compose_caption(platform: Platform, title: str, body: str, url: str) -> str:
    summary = " ".join(body.split())[:180]
    if platform == "instagram":
        return f"{title}\n\n{summary}\n\nRead more: {url}\n\n#learning #backend #buildinpublic"
    room = 280 - len(url) - 2
    message = f"{title}: {summary}"
    return f"{message[:room].rstrip()}\n{url}"


def composed_prompt(platform: Platform, title: str, body: str) -> str:
    return "\n".join(
        [
            f"Brand voice: {BRAND_VOICE}",
            f"Platform rules: {PLATFORM_RULES[platform]}",
            f"Content title: {title}",
            f"Content summary: {' '.join(body.split())[:500]}",
        ]
    )


def source_image(path: Path) -> Image.Image:
    image = Image.new("RGB", (1800, 1200), "#102a2a")
    draw = ImageDraw.Draw(image)
    draw.ellipse((650, 250, 1150, 750), fill="#63e6be")
    draw.rectangle((480, 760, 1320, 900), fill="#1c7ed6")
    draw.text((60, 60), "SOCIAL STUDIO", fill="white", font=ImageFont.load_default())
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return image


def cover_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_ratio = size[0] / size[1]
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        width = round(image.height * target_ratio)
        left = (image.width - width) // 2
        crop = image.crop((left, 0, left + width, image.height))
    else:
        height = round(image.width / target_ratio)
        top = (image.height - height) // 2
        crop = image.crop((0, top, image.width, top + height))
    return crop.resize(size, Image.Resampling.LANCZOS)


def create_variants(campaign_id: str) -> dict[Platform, str]:
    directory = Path(get_settings().artifact_dir) / campaign_id
    original_path = directory / "source.png"
    original = source_image(original_path)
    variants: dict[Platform, str] = {}
    for platform, spec in PLATFORM_SPECS.items():
        output = cover_crop(original, spec["size"])
        draw = ImageDraw.Draw(output)
        draw.rectangle((0, output.height - 56, output.width, output.height), fill="#000000")
        draw.text((24, output.height - 38), spec["label"], fill="white")
        path = directory / f"{platform}.png"
        output.save(path)
        variants[platform] = str(path)
    return variants


