from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import ProviderError


def run_ffmpeg(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ProviderError(f"ffmpeg failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def require_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise ProviderError("ffmpeg not found on PATH")
    return exe


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def normalize_clip(src: Path, dst: Path, *, duration: float, fps: int, width: int, height: int) -> Path:
    """Scale/crop to target size, fix fps, pixel format and length (loops last frame if the clip is short)."""
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
          f"fps={fps},tpad=stop_mode=clone:stop_duration={duration},setsar=1,format=yuv420p")
    run_ffmpeg([require_ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, "-t", f"{duration:.3f}",
          "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(dst)])
    return dst


def assemble(clips: list[Path], durations: list[float], dst: Path, *, transition: float,
             audio: Path | None, fps: int) -> Path:
    """Join normalized clips with xfade crossfades (or hard cuts), optionally mux a soundtrack."""
    if len(clips) != len(durations) or not clips:
        raise ValueError("clips/durations mismatch")
    exe = require_ffmpeg()
    cmd = [exe, "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]
    if audio:
        cmd += ["-i", str(audio)]

    if len(clips) == 1:
        vmap, filt = "0:v", None
    elif transition > 0:
        parts, label, elapsed = [], "[0:v]", durations[0]
        for i in range(1, len(clips)):
            out = f"[v{i}]"
            parts.append(f"{label}[{i}:v]xfade=transition=fade:duration={transition}:"
                         f"offset={elapsed - transition:.3f}{out}")
            label, elapsed = out, elapsed + durations[i] - transition
        vmap, filt = label, ";".join(parts)
    else:
        ins = "".join(f"[{i}:v]" for i in range(len(clips)))
        vmap, filt = "[vc]", f"{ins}concat=n={len(clips)}:v=1:a=0[vc]"

    if filt:
        cmd += ["-filter_complex", filt]
    cmd += ["-map", vmap]
    if audio:
        cmd += ["-map", f"{len(clips)}:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    run_ffmpeg(cmd)
    return dst
