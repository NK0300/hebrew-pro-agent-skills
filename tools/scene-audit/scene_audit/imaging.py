"""Pillow helpers: hashing, opening, resizing, drawing numbered boxes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps

Image.MAX_IMAGE_PIXELS = None  # print renders are large; files are the user's own

SEVERITY_COLORS = {
    "critical": (220, 38, 38),
    "medium": (234, 138, 0),
    "minor": (37, 99, 235),
}
OBJECT_COLOR = (16, 150, 72)
COUNT_COLOR = (168, 0, 168)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_rgb(path: Path) -> Image.Image:
    """Open read-only and return an RGB copy. EXIF rotation is applied, as viewers do."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            background.alpha_composite(img)
            img = background
        return img.convert("RGB")


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        return img.size


def fit_scale(width: int, height: int, max_side: int) -> float:
    longest = max(width, height)
    return min(1.0, max_side / longest) if longest else 1.0


def resize(img: Image.Image, scale: float) -> Image.Image:
    if abs(scale - 1.0) < 1e-6:
        return img.copy()
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    return img.resize(size, Image.LANCZOS)


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def draw_boxes(
    img: Image.Image,
    boxes: Iterable[tuple[Sequence[float], str, tuple[int, int, int]]],
    scale: float = 1.0,
) -> Image.Image:
    """Draw labelled rectangles. Boxes are in source pixels; `scale` maps them to img."""
    out = img.copy()
    draw = ImageDraw.Draw(out)
    line = max(2, round(max(out.size) / 600))
    text_size = max(14, round(max(out.size) / 90))
    fnt = font(text_size)
    for box, label, color in boxes:
        x1, y1, x2, y2 = (v * scale for v in box)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=line)
        if label:
            tx, ty = x1 + line, max(0, y1 - text_size - 2 * line)
            bbox = draw.textbbox((tx, ty), label, font=fnt)
            draw.rectangle([bbox[0] - line, bbox[1] - line, bbox[2] + line, bbox[3] + line], fill=color)
            draw.text((tx, ty), label, fill=(255, 255, 255), font=fnt)
    return out


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=False)
