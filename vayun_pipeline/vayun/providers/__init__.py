from __future__ import annotations

from .base import ImageProvider, ProviderError, VideoProvider
from .http import HttpImageProvider, HttpVideoProvider
from .mock import MockImageProvider, MockVideoProvider


def build_provider(kind: str, spec: dict):
    """spec example: {"type": "mock"} or {"type": "http", "endpoint": ..., "api_key_env": ...}"""
    spec = dict(spec)
    typ = spec.pop("type", "mock")
    table = {"image": {"mock": MockImageProvider, "http": HttpImageProvider},
             "video": {"mock": MockVideoProvider, "http": HttpVideoProvider}}[kind]
    if typ not in table:
        raise ProviderError(f"Unknown {kind} provider type: {typ}")
    return table[typ](**spec)


__all__ = ["ImageProvider", "VideoProvider", "ProviderError", "build_provider"]
