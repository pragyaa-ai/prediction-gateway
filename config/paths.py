"""Canonical filesystem paths for the gateway (independent of shell cwd)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_MODELS_DIR = PROJECT_ROOT / "models" / "local-models"
DEFAULT_MODELS_CONFIG = PROJECT_ROOT / "config" / "models.yaml"
