#!/usr/bin/env python3
"""
Standalone AutoGluon no-show inference (used when AUTOGLUON_PYTHON points here).

Reads JSON from stdin:
  {"model_dir": "...", "model_name": "WeightedEnsemble_L3_FULL", "inputs": {...}}

Writes JSON to stdout with predict_autogluon_noshow() result.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.autogluon_noshow import (  # noqa: E402
    DEFAULT_ENSEMBLE_MODEL,
    load_autogluon_predictor,
    predict_autogluon_noshow,
)

_CACHE: dict[str, object] = {}


def main() -> int:
    payload = json.load(sys.stdin)
    model_dir = payload["model_dir"]
    model_name = payload.get("model_name") or DEFAULT_ENSEMBLE_MODEL
    inputs = payload.get("inputs") or {}

    key = str(Path(model_dir).resolve())
    predictor = _CACHE.get(key)
    if predictor is None:
        predictor = load_autogluon_predictor(model_dir)
        _CACHE[key] = predictor

    result = predict_autogluon_noshow(predictor, inputs, model_name=model_name)
    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        import traceback

        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)
