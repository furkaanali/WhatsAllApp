from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import ffmpeg
from .models import Project, Scene
from .prompts import ScenePrompts, build_prompts
from .providers import ImageProvider, VideoProvider

log = logging.getLogger("vayun")


def _digest(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


class Pipeline:
    """Stages per scene: prompt -> keyframe -> I2V -> normalize; then one assemble step.

    Every stage is cached by a hash of its inputs in <workdir>/manifest.json, so re-runs only redo
    what changed (edit one scene prompt -> only that scene and the final assemble are regenerated).
    """

    def __init__(self, project: Project, image: ImageProvider, video: VideoProvider, workdir: Path,
                 *, workers: int = 2, chain_reference: bool = False):
        self.p, self.image, self.video = project, image, video
        self.work = Path(workdir)
        self.workers = workers
        self.chain_reference = chain_reference  # pass previous keyframe as reference (forces sequential)
        self.work.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.work / "manifest.json"
        self.manifest: dict[str, str] = (
            json.loads(self._manifest_path.read_text()) if self._manifest_path.exists() else {})

    # -- cache helpers --------------------------------------------------------
    def _fresh(self, key: str, digest: str, path: Path) -> bool:
        return path.exists() and self.manifest.get(key) == digest

    def _record(self, key: str, digest: str) -> None:
        self.manifest[key] = digest
        self._manifest_path.write_text(json.dumps(self.manifest, indent=2))

    # -- per-scene work -------------------------------------------------------
    def _scene(self, scene: Scene, prompts: ScenePrompts, reference: Path | None) -> Path:
        o, d = self.p.output, self.work / "scenes" / scene.id
        key_img, raw, clip = d / "keyframe.png", d / "raw.mp4", d / "clip.mp4"

        k1 = _digest("img", prompts.image, prompts.negative, scene.seed, o.width, o.height)
        if not self._fresh(f"{scene.id}:img", k1, key_img):
            log.info("[%s] keyframe", scene.id)
            self.image.generate(prompts.image, prompts.negative, key_img, width=o.width, height=o.height,
                                seed=scene.seed, reference=reference)
            self._record(f"{scene.id}:img", k1)

        k2 = _digest("i2v", k1, prompts.motion, scene.duration, o.fps)
        if not self._fresh(f"{scene.id}:i2v", k2, raw):
            log.info("[%s] image-to-video", scene.id)
            self.video.animate(key_img, prompts.motion, prompts.negative, raw, duration=scene.duration,
                               fps=o.fps, width=o.width, height=o.height, seed=scene.seed)
            self._record(f"{scene.id}:i2v", k2)

        k3 = _digest("norm", k2, o.width, o.height, o.fps, scene.duration)
        if not self._fresh(f"{scene.id}:norm", k3, clip):
            ffmpeg.normalize_clip(raw, clip, duration=scene.duration, fps=o.fps, width=o.width, height=o.height)
            self._record(f"{scene.id}:norm", k3)
        return clip

    def run(self) -> Path:
        scenes = self.p.scenes
        prompts = {s.id: build_prompts(s, self.p.style) for s in scenes}
        (self.work / "prompts.json").write_text(
            json.dumps({k: vars(v) for k, v in prompts.items()}, indent=2))

        if self.chain_reference:
            clips, ref = [], None
            for s in scenes:
                clips.append(self._scene(s, prompts[s.id], ref))
                ref = self.work / "scenes" / s.id / "keyframe.png"
        else:
            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                clips = list(ex.map(lambda s: self._scene(s, prompts[s.id], None), scenes))

        o = self.p.output
        final = self.work / o.filename
        audio = Path(o.audio) if o.audio else None
        k = _digest("final", [self.manifest.get(f"{s.id}:norm") for s in scenes], o.transition,
                    str(audio), audio.stat().st_mtime if audio and audio.exists() else None)
        if not self._fresh("final", k, final):
            log.info("assembling %d clips", len(clips))
            ffmpeg.assemble(clips, [s.duration for s in scenes], final, transition=o.transition,
                            audio=audio, fps=o.fps)
            self._record("final", k)
        return final
