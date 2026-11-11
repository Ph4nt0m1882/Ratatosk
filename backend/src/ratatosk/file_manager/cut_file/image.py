from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def prepare_image_for_preview(
    image_path: Path,
    max_dimension: int = 1280,
    quality: int = 80,
) -> bytes:
    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img)  # fix orientation based on EXIF data

        if getattr(img, "is_animated", False):  # skip animated images
            img.seek(0)

        if img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            img = img.convert("RGBA")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="WEBP", quality=quality, method=4)
        return buf.getvalue()
