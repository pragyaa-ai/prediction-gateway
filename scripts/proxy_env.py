"""Shared env helpers for Fakeeh Flask proxies (model-specific vars with generic fallback)."""
from __future__ import annotations

import os


def env_get(*keys: str, default: str = "") -> str:
    """Return the first set env var from keys, else default."""
    for key in keys:
        val = os.getenv(key)
        if val is not None and val != "":
            return val
    return default


def env_bool(*keys: str, default: str = "true") -> bool:
    return env_get(*keys, default=default).lower() in ("1", "true", "yes")
