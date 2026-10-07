"""Offline providers: deterministic keyframes (Pillow) and Ken-Burns 'I2V' (FFmpeg zoompan).

They let the whole pipeline run and be tested with no API keys or GPU.
"""
from __future__ import annotations

import hashlib
import random
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from ..ffmpeg import run_ffmpeg, require_ffmpeg
from .base import ImageProvider, VideoProvider


class MockImageProvider(ImageProvider):
    def generate(self, prompt, negative, out_path, *, width, height, seed=None, reference=None):
        h = int(hashlib.sha256(f"{prompt}|{seed}".encode()).hexdigest(), 16)
        rng = random.Random(h)
        c1 = tuple(rng.randint(20, 235) for _ in range(3))
        c2 = tuple(rng.randint(20, 235) for _ in range(3))
        img = Image.new("RGB", (width, height))
        px = ImageDraw.Draw(img)
        for y in range(height):  # vertical gradient
            t = y / max(height - 1, 1)
            px.line([(0, y), (width, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
        px.multiline_text((40, 40), "\n".join(textwrap.wrap(prompt, 48)[:8]), fill=(255, 255, 255))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path


class MockVideoProvider(VideoProvider):
    def animate(self, image_path, prompt, negative, out_path, *, duration, fps, width, height, seed=None):
        frames = max(1, round(duration * fps))
        zoom = "zoom='min(zoom+0.0015,1.3)'" if "pull" not in prompt else "zoom='max(1.3-0.0015*on,1.0)'"
        vf = (f"scale={width * 2}:{height * 2},zoompan={zoom}:d={frames}:s={width}x{height}:fps={fps}"
              ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',format=yuv420p")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg([require_ffmpeg(), "-y", "-loglevel", "error", "-i", str(image_path), "-vf", vf,
              "-frames:v", str(frames), "-c:v", "libx264", str(out_path)])
        return out_path
