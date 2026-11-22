"""Bounding-box helpers. A box is [x1, y1, x2, y2] in source pixels, origin top-left."""

from __future__ import annotations

from typing import Sequence

Box = list[int]


def clamp_box(box: Sequence[float], width: int, height: int) -> Box:
    x1, y1, x2, y2 = box
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    x1 = max(0, min(width, round(x1)))
    x2 = max(0, min(width, round(x2)))
    y1 = max(0, min(height, round(y1)))
    y2 = max(0, min(height, round(y2)))
    return [x1, y1, x2, y2]


def area(box: Sequence[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def intersection(a: Sequence[float], b: Sequence[float]) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    inter = intersection(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


def containment(a: Sequence[float], b: Sequence[float]) -> float:
    """Share of the smaller box that lies inside the other."""
    smaller = min(area(a), area(b))
    return intersection(a, b) / smaller if smaller > 0 else 0.0


def pad_box(box: Sequence[float], fraction: float, width: int, height: int) -> Box:
    w = box[2] - box[0]
    h = box[3] - box[1]
    dx = w * fraction
    dy = h * fraction
    return clamp_box([box[0] - dx, box[1] - dy, box[2] + dx, box[3] + dy], width, height)


def valid_box(box: object, width: int, height: int) -> bool:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return False
    if not all(isinstance(v, (int, float)) for v in box):
        return False
    x1, y1, x2, y2 = box
    return 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height


def view_to_source(box: Sequence[float], offset: Sequence[float], scale: float) -> list[float]:
    """Map a box drawn on a view image back to source pixels.

    A view shows the source region starting at `offset` (x, y), resized by `scale`
    (view px = source px * scale).
    """
    ox, oy = offset
    return [ox + box[0] / scale, oy + box[1] / scale, ox + box[2] / scale, oy + box[3] / scale]
