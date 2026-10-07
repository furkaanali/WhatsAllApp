from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..errors import ProviderError  # noqa: F401  (re-export)


class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, negative: str, out_path: Path, *, width: int, height: int,
                 seed: int | None = None, reference: Path | None = None) -> Path:
        """Write a keyframe image to out_path. `reference` is the previous scene's keyframe (may be ignored)."""


class VideoProvider(ABC):
    @abstractmethod
    def animate(self, image_path: Path, prompt: str, negative: str, out_path: Path, *,
                duration: float, fps: int, width: int, height: int, seed: int | None = None) -> Path:
        """Write an mp4 animating image_path to out_path."""

