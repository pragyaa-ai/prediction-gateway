"""
AutoGluon TabularPredictor loader + inference for no_show_fakeeh_ksa_local.

Production SageMaker model: WeightedEnsemble-L3-FULL-t1
On-disk artifact name:      WeightedEnsemble_L3_FULL

The export was built with AutoGluon 0.4.3. We load with 0.5.x and apply small
compat patches for cross-version pickles (see apply_autogluon_compat_patches).
"""
from __future__ import annotations

import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from adapters.noshow_features import NOSHOW_CLASS_LABELS, NOSHOW_RAW_FIELDS_21

DEFAULT_ENSEMBLE_MODEL = "WeightedEnsemble_L3_FULL"

_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
)

_NUMERIC_RAW_COLUMNS = frozenset(
    {"ALLOCATION_DATE_TIME", "GIVEN_ON", "MRNO", "APPT_ALLOCATION_ID"}
)

_patches_applied = False


def resolve_autogluon_model_name(name: Optional[str]) -> str:
    """Map SageMaker MODEL_NAME env (hyphens, -t1 suffix) to on-disk model key."""
    if not name:
        return DEFAULT_ENSEMBLE_MODEL
    resolved = name.strip().replace("-", "_")
    if resolved.endswith("_t1"):
        resolved = resolved[: -len("_t1")]
    return resolved


def apply_autogluon_compat_patches() -> None:
    """One-time patches so 0.4.3 artifacts run under newer AutoGluon."""
    global _patches_applied
    if _patches_applied:
        return
    _patches_applied = True

    warnings.filterwarnings("ignore", category=UserWarning, module="autogluon")

    try:
        import autogluon.common.utils.path_converter as path_converter

        path_converter.PathConverter._validate_path = lambda path: None  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        import autogluon.tabular.predictor.predictor as predictor_mod

        _orig_load = predictor_mod.TabularPredictor.load

        @classmethod
        def _load_patched(cls, path: str, *args: Any, **kwargs: Any) -> Any:
            pred = _orig_load(path, *args, **kwargs)
            if not hasattr(pred, "_decision_threshold"):
                pred._decision_threshold = None
            return pred

        predictor_mod.TabularPredictor.load = _load_patched  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from autogluon.tabular.models.fastainn.tabular_nn_fastai import NNFastAiTabularModel

        _orig_fastai_predict = NNFastAiTabularModel._predict_proba

        def _predict_proba_patched(self: Any, X: Any, **kwargs: Any) -> Any:
            if not hasattr(self, "_num_cpus_infer"):
                self._num_cpus_infer = os.cpu_count() or 4
            return _orig_fastai_predict(self, X, **kwargs)

        NNFastAiTabularModel._predict_proba = _predict_proba_patched  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from autogluon.tabular.models.tabular_nn.torch.tabular_nn_torch import TabularNeuralNetTorchModel

        _orig_torch_predict = TabularNeuralNetTorchModel._predict_proba

        def _torch_predict_proba_patched(self: Any, X: Any, **kwargs: Any) -> Any:
            if not hasattr(self, "_num_cpus_infer"):
                self._num_cpus_infer = os.cpu_count() or 4
            return _orig_torch_predict(self, X, **kwargs)

        TabularNeuralNetTorchModel._predict_proba = _torch_predict_proba_patched  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from autogluon.tabular.models.xgboost.xgboost_model import XGBoostModel

        _orig_xgb_load = XGBoostModel.load

        @classmethod
        def _xgb_load_patched(cls, path: str, reset_paths: bool = True, verbose: bool = True) -> Any:
            model = super(XGBoostModel, cls).load(path=path, reset_paths=reset_paths, verbose=verbose)
            if model._xgb_model_type is None:
                return model
            model.model = model._xgb_model_type()
            load_errors: list[str] = []
            for suffix in ("xgb.ubj", "xgb.model", "xgb.json", "model.ubj", "model.json"):
                candidate = f"{path}{suffix}"
                if not os.path.isfile(candidate):
                    continue
                try:
                    model.model.load_model(candidate)
                    model._xgb_model_type = None
                    return model
                except Exception as exc:
                    if suffix == "xgb.ubj":
                        import shutil
                        import tempfile

                        fd, tmp_path = tempfile.mkstemp(suffix=".model")
                        os.close(fd)
                        try:
                            shutil.copy2(candidate, tmp_path)
                            model.model.load_model(tmp_path)
                            model._xgb_model_type = None
                            return model
                        except Exception as inner_exc:
                            load_errors.append(f"{suffix} (binary fallback): {inner_exc}")
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass
                    load_errors.append(f"{suffix}: {exc}")
            tried = ", ".join(load_errors) or "no candidate files found"
            raise RuntimeError(f"Failed to load XGBoost model from {path} ({tried})")

        XGBoostModel.load = _xgb_load_patched  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        import torch

        _orig_torch_load = torch.load

        def _torch_load_patched(*args: Any, **kwargs: Any) -> Any:
            if "weights_only" not in kwargs:
                kwargs["weights_only"] = False
            return _orig_torch_load(*args, **kwargs)

        torch.load = _torch_load_patched  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass


def _parse_datetime(val: Any) -> Optional[datetime]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(float(val))
        except (OSError, ValueError, OverflowError):
            return None
    text = str(val).strip()
    if not text:
        return None
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _datetime_to_float(val: Any) -> float:
    if val is None or val == "":
        return float("nan")
    if isinstance(val, (int, float)):
        # Fakeeh Flask cloud path sends epoch milliseconds
        return float(val)
    dt = _parse_datetime(val)
    if dt is not None:
        return dt.timestamp()
    try:
        return float(val)
    except (TypeError, ValueError):
        return float("nan")


def _id_to_float(val: Any) -> float:
    if val is None or val == "":
        return float("nan")
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    if not text:
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def build_autogluon_dataframe(raw: Dict[str, Any]) -> pd.DataFrame:
    """
    Build a one-row DataFrame aligned with tabular_serve.py HEADER / training schema.

    Datetime and id columns must be numeric (float) before AutoGluon feature typing.
    Other columns are passed through as strings, matching SageMaker CSV ingestion.
    """
    row: Dict[str, Any] = {}
    for col in NOSHOW_RAW_FIELDS_21:
        val = raw.get(col, "")
        if col in _NUMERIC_RAW_COLUMNS:
            row[col] = _datetime_to_float(val) if "DATE" in col or col == "GIVEN_ON" else _id_to_float(val)
        else:
            row[col] = "" if val is None else val
    return pd.DataFrame([row], columns=list(NOSHOW_RAW_FIELDS_21))


def load_autogluon_predictor(model_dir: str) -> Any:
    apply_autogluon_compat_patches()
    from autogluon.tabular import TabularPredictor

    root = Path(model_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"AutoGluon model directory not found: {root}")
    return TabularPredictor.load(str(root), require_version_match=False)


def predict_autogluon_noshow(
    predictor: Any,
    inputs: Dict[str, Any],
    model_name: str = DEFAULT_ENSEMBLE_MODEL,
) -> Dict[str, Any]:
    apply_autogluon_compat_patches()
    df = build_autogluon_dataframe(inputs)
    resolved_name = resolve_autogluon_model_name(model_name)

    label = predictor.predict(df, model=resolved_name)[0]
    proba_series = predictor.predict_proba(df, model=resolved_name).iloc[0]
    class_labels: List[str] = list(getattr(predictor, "class_labels", NOSHOW_CLASS_LABELS))
    probabilities = [float(proba_series[c]) for c in class_labels]
    no_show_prob = float(proba_series["No Show"]) if "No Show" in proba_series.index else probabilities[-1]
    score = float(proba_series.loc[label])

    return {
        "prediction": label,
        "predicted_label": str(label),
        "score": score,
        "probability": no_show_prob,
        "no_show_probability": no_show_prob,
        "probabilities": probabilities,
        "class_labels": class_labels,
    }


def autogluon_available() -> bool:
    try:
        import autogluon.tabular  # noqa: F401

        return True
    except ImportError:
        return False
