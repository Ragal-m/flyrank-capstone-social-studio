from pathlib import Path

from PIL import Image

from app.content import compose_caption, create_variants


def test_platform_image_dimensions():
    variants = create_variants("dimension-test")
    with Image.open(variants["instagram"]) as image:
        assert image.size == (1080, 1080)
        assert image.getpixel((540, 540)) == (99, 230, 190)
    with Image.open(variants["x"]) as image:
        assert image.size == (1600, 900)
        assert image.getpixel((800, 450)) == (99, 230, 190)
    assert Path(variants["instagram"]).exists()
    assert Path(variants["x"]).exists()


def test_platform_captions_are_distinct():
    instagram = compose_caption(
        "instagram", "A title", "A practical story for builders", "https://example.com"
    )
    x_caption = compose_caption(
        "x", "A title", "A practical story for builders", "https://example.com"
    )
    assert instagram != x_caption
    assert "#learning" in instagram
    assert len(x_caption) <= 280

