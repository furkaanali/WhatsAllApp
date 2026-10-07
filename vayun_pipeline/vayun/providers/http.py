"""Generic submit -> poll -> download HTTP providers.

Real vendors differ in request/response shape, so the JSON field names are configurable.
Expected contract:
  POST  {endpoint}            -> JSON containing a job id at `id_field`
  GET   {endpoint}/{job_id}   -> JSON with `status_field` in {done_values, failed_values}
                                 and, once done, a result URL at `result_field`
Dotted paths ("data.url") are supported. The API key is read from an env var, never stored.
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

import requests

from .base import ImageProvider, ProviderError, VideoProvider


def _dig(obj: Any, path: str) -> Any:
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


class _HttpJobClient:
    def __init__(self, endpoint: str, api_key_env: str, *, id_field="id", status_field="status",
                 result_field="output.url", done_values=("succeeded", "completed", "done"),
                 failed_values=("failed", "error", "canceled"), poll_interval=5.0, timeout=900.0,
                 extra: dict | None = None):
        key = os.environ.get(api_key_env)
        if not key:
            raise ProviderError(f"Environment variable {api_key_env} is not set")
        self.endpoint = endpoint.rstrip("/")
        self.headers = {"Authorization": f"Bearer {key}"}
        self.id_field, self.status_field, self.result_field = id_field, status_field, result_field
        self.done, self.failed = set(done_values), set(failed_values)
        self.poll_interval, self.timeout, self.extra = poll_interval, timeout, extra or {}

    def run(self, payload: dict, out_path: Path) -> Path:
        r = requests.post(self.endpoint, json={**self.extra, **payload}, headers=self.headers, timeout=60)
        r.raise_for_status()
        job_id = _dig(r.json(), self.id_field)
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            s = requests.get(f"{self.endpoint}/{job_id}", headers=self.headers, timeout=60)
            s.raise_for_status()
            body = s.json()
            status = str(_dig(body, self.status_field)).lower()
            if status in self.done:
                dl = requests.get(_dig(body, self.result_field), timeout=300)
                dl.raise_for_status()
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(dl.content)
                return out_path
            if status in self.failed:
                raise ProviderError(f"Job {job_id} failed: {body}")
            time.sleep(self.poll_interval)
        raise ProviderError(f"Job {job_id} timed out after {self.timeout}s")


class HttpImageProvider(ImageProvider):
    def __init__(self, **kw):
        self.client = _HttpJobClient(**kw)

    def generate(self, prompt, negative, out_path, *, width, height, seed=None, reference=None):
        payload = {"prompt": prompt, "negative_prompt": negative, "width": width, "height": height, "seed": seed}
        if reference:
            payload["reference_image"] = base64.b64encode(reference.read_bytes()).decode()
        return self.client.run(payload, out_path)


class HttpVideoProvider(VideoProvider):
    def __init__(self, **kw):
        self.client = _HttpJobClient(**kw)

    def animate(self, image_path, prompt, negative, out_path, *, duration, fps, width, height, seed=None):
        payload = {"image": base64.b64encode(image_path.read_bytes()).decode(), "prompt": prompt,
                   "negative_prompt": negative, "duration": duration, "fps": fps, "seed": seed}
        return self.client.run(payload, out_path)
