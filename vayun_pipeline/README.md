# VAYUN AI Video Pipeline

`scene → prompt → image/keyframe → image-to-video → FFmpeg → final video`

```
story.yaml ─▶ prompts.py ─▶ ImageProvider ─▶ VideoProvider ─▶ ffmpeg.normalize ─▶ ffmpeg.assemble ─▶ final.mp4
 (scenes +     (style bible,   (keyframe.png)  (raw.mp4)        (size/fps/length)   (xfade + audio)
  style)        @character)
```

## Quick start (offline, no API keys)
```bash
pip install -r requirements.txt        # needs ffmpeg + ffprobe on PATH
python -m vayun examples/story.yaml     # -> build/vayun_demo/final.mp4
python -m unittest discover -s tests -t .
```
The default **mock providers** (Pillow keyframes + FFmpeg Ken-Burns zoom) exercise every stage so the
workflow can be tested anywhere.

## Real backends
`python -m vayun story.yaml --providers examples/providers.http.example.yaml`

`HttpImageProvider` / `HttpVideoProvider` implement a generic *submit → poll → download* contract with
configurable JSON field names; API keys are read from env vars (`api_key_env`). **These are not yet
tested against a live vendor** - expect to adjust the payload/field names for your chosen service,
or add a small `ImageProvider`/`VideoProvider` subclass (two methods) and register it in
`providers/__init__.py`.

## Design notes
- **Resumable & incremental**: each stage is cached by a hash of its inputs in `manifest.json`.
  Editing one scene regenerates only that scene plus the final assemble (covered by tests).
- **Consistency**: `style` (look, palette, negative prompt) is applied to every scene; `@name` tokens expand to
  a fixed character description. `--chain-reference` passes the previous keyframe as a reference image.
- **Output**: all clips are normalised to one size/fps/pixel format before `xfade` crossfades, so mixed-vendor
  clips join cleanly. Optional soundtrack via `output.audio`.
- Intermediate artifacts (`prompts.json`, per-scene `keyframe.png`, `raw.mp4`, `clip.mp4`) are kept in the workdir for review.

## Roadmap
LLM-based script → scenes step, per-scene retries/backoff, cost/time logging, subtitle burn-in, voice-over (TTS), QC gate (human approve keyframes before spending I2V credits).
