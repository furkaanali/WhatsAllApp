"""Scene -> prompts. Pure functions, so they are trivial to test and tweak."""
from __future__ import annotations

from dataclasses import dataclass

from .models import Scene, Style


@dataclass(frozen=True)
class ScenePrompts:
    image: str      # keyframe (text-to-image) prompt
    motion: str     # image-to-video prompt
    negative: str


def _expand_characters(text: str, style: Style) -> str:
    # Replace @name tokens with the fixed character description for consistency.
    for name, desc in style.characters.items():
        text = text.replace(f"@{name}", f"{name} ({desc})")
    return text


def build_prompts(scene: Scene, style: Style) -> ScenePrompts:
    desc = _expand_characters(scene.description.strip(), style)
    image = ", ".join(p for p in (scene.shot, desc, style.look, style.palette) if p)
    motion = ", ".join(p for p in (scene.motion, f"camera: {scene.camera}", "smooth natural motion") if p)
    negative = ", ".join(p for p in (style.negative, scene.negative) if p)
    return ScenePrompts(image=image, motion=motion, negative=negative)
