from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from .models import Project
from .pipeline import Pipeline
from .providers import ProviderError, build_provider


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vayun", description="Scene -> prompt -> keyframe -> I2V -> FFmpeg -> video")
    ap.add_argument("project", help="project YAML (see examples/story.yaml)")
    ap.add_argument("--workdir", default=None, help="output/cache dir (default: build/<project name>)")
    ap.add_argument("--providers", default=None, help="providers YAML; default is offline mock providers")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--chain-reference", action="store_true",
                    help="feed each keyframe to the next scene as reference (sequential)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(message)s")

    try:
        project = Project.load(a.project)
        cfg = yaml.safe_load(Path(a.providers).read_text()) if a.providers else {}
        image = build_provider("image", cfg.get("image", {"type": "mock"}))
        video = build_provider("video", cfg.get("video", {"type": "mock"}))
        work = Path(a.workdir or Path("build") / project.name)
        final = Pipeline(project, image, video, work, workers=a.workers,
                         chain_reference=a.chain_reference).run()
    except (ProviderError, ValueError, FileNotFoundError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
