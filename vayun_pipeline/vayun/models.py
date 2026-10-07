from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Scene:
    id: str
    description: str
    duration: float = 4.0
    camera: str = "slow push-in"        # camera movement hint for the I2V model
    motion: str = ""                    # subject motion hint
    shot: str = "medium shot"
    negative: str = ""                  # extra negative prompt for this scene
    seed: int | None = None


@dataclass
class Style:
    """Project-wide 'style bible' appended to every prompt for visual consistency."""
    look: str = "cinematic, natural lighting, 35mm film"
    palette: str = ""
    characters: dict[str, str] = field(default_factory=dict)  # name -> fixed visual description
    negative: str = "blurry, low quality, watermark, text, deformed"


@dataclass
class Output:
    width: int = 1280
    height: int = 720
    fps: int = 24
    transition: float = 0.5             # crossfade seconds between scenes (0 = hard cut)
    audio: str | None = None            # optional soundtrack file
    filename: str = "final.mp4"


@dataclass
class Project:
    name: str
    scenes: list[Scene]
    style: Style = field(default_factory=Style)
    output: Output = field(default_factory=Output)

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        scenes = [Scene(**s) for s in data.get("scenes", [])]
        if not scenes:
            raise ValueError("Project has no scenes")
        ids = [s.id for s in scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("Scene ids must be unique")
        for s in scenes:
            if s.duration <= 0:
                raise ValueError(f"Scene {s.id}: duration must be > 0")
        out = Output(**data.get("output", {}))
        if out.width % 2 or out.height % 2:
            raise ValueError("Output width/height must be even (yuv420p)")
        if out.transition >= min(s.duration for s in scenes):
            raise ValueError("transition must be shorter than the shortest scene")
        return cls(
            name=data.get("name", "untitled"),
            scenes=scenes,
            style=Style(**data.get("style", {})),
            output=out,
        )
