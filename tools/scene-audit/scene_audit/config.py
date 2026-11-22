"""Book configuration: locating and loading book.yaml, and the book's folders."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_NAME = "book.yaml"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

SEVERITIES = ["critical", "medium", "minor"]
SEVERITY_RANK = {name: index for index, name in enumerate(SEVERITIES)}

DEFAULTS: dict[str, Any] = {
    "book": "",
    "paths": {
        "scenes": "scenes",
        "spec": "spec",
        "words": None,
        "item_sheets": None,
        "tracking": [],
        "prior_reviews": [],
    },
    "format": {
        "layout": "single",
        "width_px": None,
        "height_px": None,
        "tolerance_pct": 2,
    },
    "scene_id_pattern": r"(\d+)(?!.*\d)",
    "scan": {
        "tiles": [3, 3],
        "tile_overlap": 0.15,
        "crop_padding": 0.20,
        "crop_min_short_side": 768,
        "crop_max_long_side": 2048,
        "crop_max_scale": 8,
        "context_padding": 1.0,
        "view_max_side": 1568,
        "gap_grid": 6,
        "dedupe_iou": 0.5,
    },
    "fix_threshold": "medium",
    "features": {
        "find_tags": True,
        "item_strip": True,
        "words": True,
        "spreads": False,
    },
}


class ConfigError(Exception):
    """book.yaml is missing or invalid."""


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def find_book_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    raise ConfigError(
        f"No {CONFIG_NAME} found in {here} or its parents. Run `scene-audit init` in the book folder, or pass --book."
    )


@dataclass
class Book:
    root: Path
    cfg: dict[str, Any]

    @classmethod
    def load(cls, book: str | Path | None = None) -> "Book":
        if book:
            path = Path(book).resolve()
            root = path.parent if path.is_file() else path
            if not (root / CONFIG_NAME).is_file():
                raise ConfigError(f"No {CONFIG_NAME} in {root}")
        else:
            root = find_book_root()
        raw = yaml.safe_load((root / CONFIG_NAME).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ConfigError(f"{CONFIG_NAME} must be a mapping")
        cfg = _merge(DEFAULTS, raw)
        if cfg["fix_threshold"] not in SEVERITY_RANK:
            raise ConfigError(f"fix_threshold must be one of {SEVERITIES}")
        if cfg["format"]["layout"] not in ("single", "spread"):
            raise ConfigError("format.layout must be single or spread")
        return cls(root=root, cfg=cfg)

    # Folders -----------------------------------------------------------
    def path(self, value: str | None) -> Path | None:
        if not value:
            return None
        p = Path(value)
        return p if p.is_absolute() else (self.root / p)

    @property
    def scenes_dir(self) -> Path:
        return self.path(self.cfg["paths"]["scenes"])  # type: ignore[return-value]

    @property
    def spec_dir(self) -> Path:
        return self.path(self.cfg["paths"]["spec"])  # type: ignore[return-value]

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def out(self) -> Path:
        return self.root / "out"

    @property
    def scan(self) -> dict[str, Any]:
        return self.cfg["scan"]

    def scene_work(self, scene_id: str) -> Path:
        return self.work / f"scene-{scene_id}"

    def scene_json(self, scene_id: str) -> Path:
        return self.work / f"scene-{scene_id}.json"

    # Scenes ------------------------------------------------------------
    def scene_files(self) -> list[Path]:
        folder = self.scenes_dir
        if not folder.is_dir():
            return []
        return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)

    def scene_id_for(self, path: Path) -> str:
        match = re.search(self.cfg["scene_id_pattern"], path.stem)
        if match:
            value = match.group(1)
            return value.zfill(2) if value.isdigit() else value
        return re.sub(r"[^A-Za-z0-9_-]+", "-", path.stem).strip("-") or "scene"

    def scene_map(self) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for path in self.scene_files():
            sid = self.scene_id_for(path)
            if sid in result:
                raise ConfigError(
                    f"Two files map to scene {sid}: {result[sid].name} and {path.name}. Adjust scene_id_pattern in {CONFIG_NAME}."
                )
            result[sid] = path
        return result

    def resolve_scenes(self, scene: str | None, all_scenes: bool) -> list[str]:
        mapping = self.scene_map()
        if all_scenes or not scene:
            return sorted(mapping)
        wanted = []
        for part in scene.split(","):
            sid = part.strip()
            if sid.isdigit():
                sid = sid.zfill(2)
            if sid not in mapping:
                raise ConfigError(f"Unknown scene {part!r}. Known: {', '.join(sorted(mapping)) or 'none'}")
            wanted.append(sid)
        return wanted

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
