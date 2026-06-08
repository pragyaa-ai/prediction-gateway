"""
Compatibility shim to load Azure AutoML pickled pipelines without the
azureml-train-automl-client runtime installed.

Strategy
--------
1. Patch sklearn.utils.tosequence (removed in sklearn 1.x) so that
   sklearn_pandas 2.2.0 can be imported properly.
2. Install auto-stubbing modules for every azureml.* namespace so that
   pickle.load can reconstruct the objects.
3. Add working transform/predict methods to each stub class that delegate
   to the underlying sklearn/scipy objects embedded in the pickle.
4. Patch xgboost.core.Booster.__setstate__ to survive old binary formats
   (Azure AutoML sometimes stores pre-1.0 boosters).

After calling install_azureml_compat() the Azure AutoML delay/LOS artifacts under
models/local-models/ can be loaded with pickle.load and their .predict(pd.DataFrame) called.
"""
from __future__ import annotations

import sys
import types
import warnings
from typing import Any

import numpy as np
import pandas as pd

_COMPAT_INSTALLED = False


# ---------------------------------------------------------------------------
# sklearn.utils.tosequence shim (removed in sklearn >= 1.0)
# ---------------------------------------------------------------------------

def _patch_sklearn_tosequence() -> None:
    import sklearn.utils  # noqa: F401

    if not hasattr(sklearn.utils, "tosequence"):
        sklearn.utils.tosequence = lambda x: list(x) if hasattr(x, "__iter__") else [x]


# ---------------------------------------------------------------------------
# XGBoost Booster old-format shim
# ---------------------------------------------------------------------------

def _try_load_xgb_from_json_state(state: dict) -> "Any | None":
    """
    XGBoost 1.5.x stores the booster as {Config:.., Model:..} JSON in the pickle
    state's 'handle' key.  XGBoost 2.x UnserializeFromBuffer rejects this format.
    Extract the 'Model' sub-dict and load it via Booster.load_model() which does
    accept the older JSON model format.
    """
    import json
    import os
    import tempfile

    try:
        import xgboost as _xgb

        handle_bytes = bytes(state.get("handle", b""))
        if not handle_bytes:
            return None
        j = json.loads(handle_bytes)
        model_json = json.dumps(j["Model"]).encode()
    except Exception:
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as fh:
        fh.write(model_json)
        fname = fh.name
    try:
        b = _xgb.Booster()
        b.load_model(fname)
        b.best_iteration = state.get("best_iteration", 0)
        b.best_ntree_limit = state.get("best_ntree_limit", 0)
        return b
    except Exception:
        return None
    finally:
        os.unlink(fname)


def _patch_xgboost_booster() -> None:
    """Patch Booster.__setstate__ to handle pre-1.6 JSON format on xgboost 2.x."""
    try:
        import xgboost.core as _xc

        _orig = _xc.Booster.__setstate__

        def _safe_setstate(self: Any, state: Any) -> None:
            try:
                _orig(self, state)
                self._load_failed = False  # type: ignore[attr-defined]
            except Exception:
                self._load_failed = True  # type: ignore[attr-defined]
                self._handle = None  # type: ignore[attr-defined]

        _xc.Booster.__setstate__ = _safe_setstate  # type: ignore[method-assign]
    except ImportError:
        pass


def _reconvert_xgboost_boosters(obj: Any, _visited: "set[int] | None" = None) -> None:
    """
    Post-load fix for xgboost 2.x loading old pre-1.6 pickle format.

    xgboost 2.x can load the old JSON model format (with a deprecation warning)
    but may predict incorrectly due to internal format differences.  Re-saving each
    booster to UBJ and reloading in-place normalises the format and restores correct
    prediction behaviour.  Safe to call on xgboost 1.x too (no-op if save succeeds).
    """
    import os
    import tempfile

    if _visited is None:
        _visited = set()
    oid = id(obj)
    if oid in _visited:
        return
    _visited.add(oid)

    cls_name = type(obj).__name__

    # XGBRegressor / XGBClassifier: fix the booster in-place
    if cls_name in ("XGBRegressor", "XGBClassifier", "XGBModel") or (
        hasattr(obj, "_Booster") and obj._Booster is not None
    ):
        try:
            booster = getattr(obj, "_Booster", None)
            if booster is None:
                booster = obj.get_booster()
            if booster is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ubj") as fh:
                    fname = fh.name
                try:
                    booster.save_model(fname)
                    booster.load_model(fname)
                finally:
                    try:
                        os.unlink(fname)
                    except OSError:
                        pass
        except Exception:
            pass
        return  # don't recurse into XGB internals

    # Recurse into child objects
    for attr in ("pipeline", "model"):
        child = getattr(obj, attr, None)
        if child is not None and not isinstance(
            child, (str, bytes, int, float, bool, type(None), np.ndarray)
        ):
            _reconvert_xgboost_boosters(child, _visited)

    if hasattr(obj, "steps"):
        for _, step in obj.steps:
            _reconvert_xgboost_boosters(step, _visited)

    if hasattr(obj, "_wrappedEnsemble"):
        ens = obj._wrappedEnsemble
        if hasattr(ens, "estimators_"):
            for est in ens.estimators_:
                _reconvert_xgboost_boosters(est, _visited)


# ---------------------------------------------------------------------------
# Auto-stubbing azureml.* modules
# ---------------------------------------------------------------------------

_AZUREML_MODULES = [
    "azureml",
    "azureml.automl",
    "azureml.automl.core",
    "azureml.automl.core.featurization",
    "azureml.automl.core.featurization.featurizationconfig",
    "azureml.automl.runtime",
    "azureml.automl.runtime.featurization",
    "azureml.automl.runtime.featurization.data_transformer",
    "azureml.automl.runtime.featurization.transformer_and_mapper",
    "azureml.automl.runtime.shared",
    "azureml.automl.runtime.shared.model_wrappers",
    "azureml.automl.runtime.shared.problem_info",
    "azureml.training",
    "azureml.training.tabular",
    "azureml.training.tabular.featurization",
    "azureml.training.tabular.featurization._engineered_feature_names",
    "azureml.training.tabular.featurization.categorical",
    "azureml.training.tabular.featurization.categorical.cat_imputer",
    "azureml.training.tabular.featurization.categorical.hashonehotvectorizer_transformer",
    "azureml.training.tabular.featurization.categorical.labelencoder_transformer",
    "azureml.training.tabular.featurization.text",
    "azureml.training.tabular.featurization.text.stringcast_transformer",
    "azureml.training.tabular.featurization.datetime",
    "azureml.training.tabular.featurization.datetime.datetime_transformer",
    "azureml.training.tabular.featurization.generic",
    "azureml.training.tabular.featurization.generic.imputation_marker",
    "azureml.training.tabular.models",
    "azureml.training.tabular.models.forecasting_pipeline_wrapper",
    "azureml.training.tabular.models.voting_ensemble",
]


def _make_auto_stub_module(mod_name: str) -> types.ModuleType:
    """Return a module whose __getattr__ creates sklearn-compatible stub classes on demand."""
    from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin

    def _stub_bases(name: str) -> tuple[type, ...]:
        if name in (
            "PreFittedSoftVotingRegressor",
            "XGBoostRegressor",
            "LightGBMRegressor",
            "RegressionPipeline",
        ) or "Regressor" in name:
            return (BaseEstimator, RegressorMixin)
        return (BaseEstimator, TransformerMixin)

    def _stub_methods(name: str) -> dict[str, Any]:
        methods: dict[str, Any] = {
            "__module__": mod_name,
            "__setstate__": lambda self, d: self.__dict__.update(d),
            "_wrap_in_lst": staticmethod(
                lambda x: [x] if not isinstance(x, list) else x
            ),
            "fit": lambda self, *a, **kw: self,
            "__sklearn_is_fitted__": lambda self: True,
        }
        if name in (
            "PreFittedSoftVotingRegressor",
            "XGBoostRegressor",
            "LightGBMRegressor",
            "RegressionPipeline",
        ) or "Regressor" in name:
            methods["predict"] = lambda self, X: np.asarray(X)
        else:
            methods["transform"] = lambda self, X: X
        return methods

    def _getattr(name: str) -> type:
        stub = type(name, _stub_bases(name), _stub_methods(name))
        setattr(sys.modules[mod_name], name, stub)
        return stub

    mod = types.ModuleType(mod_name)
    mod.__getattr__ = _getattr  # type: ignore[method-assign]
    mod.__path__ = []  # treat as package so importlib can load submodules
    return mod


def _install_azureml_stubs() -> None:
    for mod_name in _AZUREML_MODULES:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = _make_auto_stub_module(mod_name)


# ---------------------------------------------------------------------------
# Functional transform/predict methods for the stub classes
# Each is injected after the pickle is loaded and the stub class is known.
# ---------------------------------------------------------------------------

def _to_series(X: Any, col: str) -> pd.Series:
    """Extract a single column from a DataFrame or array."""
    if isinstance(X, pd.DataFrame):
        if col in X.columns:
            return X[col]
        return pd.Series([""] * len(X))
    return pd.Series(X)


def _col_to_str(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str)


# -- StringCastTransformer --------------------------------------------------

def _stringcast_transform(self: Any, X: Any) -> Any:
    """Cast values to string; pass-through for CountVectorizer downstream."""
    if isinstance(X, pd.Series):
        return _col_to_str(X)
    if isinstance(X, pd.DataFrame):
        return X.apply(lambda c: _col_to_str(c))
    return pd.Series(X).astype(str)


# -- CatImputer -------------------------------------------------------------

def _catimputer_transform(self: Any, X: Any) -> Any:
    fill = getattr(self, "_fill", "")
    if isinstance(X, pd.Series):
        return X.fillna(fill).astype(str)
    if isinstance(X, pd.DataFrame):
        return X.fillna(fill).astype(str)
    return pd.Series(X).fillna(fill).astype(str)


# -- LabelEncoderTransformer ------------------------------------------------

def _labelencoder_transform(self: Any, X: Any) -> np.ndarray:
    le = self._label_encoder
    known = set(le.classes_)
    if isinstance(X, pd.Series):
        vals = X.astype(str).tolist()
    else:
        vals = list(X)
    # Unknown categories → 0 (first class)
    mapped = [v if v in known else le.classes_[0] for v in vals]
    return le.transform(mapped).reshape(-1, 1).astype(float)


# -- HashOneHotVectorizerTransformer ----------------------------------------

def _hashohe_transform(self: Any, X: Any) -> np.ndarray:
    """Reproduce Azure AutoML hash-based OHE using sklearn FeatureHasher."""
    from sklearn.feature_extraction import FeatureHasher

    n = int(self._num_cols)
    if isinstance(X, pd.Series):
        strings = _col_to_str(X).tolist()
    else:
        strings = [str(v) for v in X]
    fh = FeatureHasher(n_features=n, input_type="string", alternate_sign=False)
    return fh.transform([[s] for s in strings]).toarray()


# -- ImputationMarker -------------------------------------------------------

def _imputation_marker_transform(self: Any, X: Any) -> np.ndarray:
    """Return a binary flag: 1 where original value was missing, 0 otherwise."""
    if isinstance(X, pd.Series):
        return X.isna().astype(float).values.reshape(-1, 1)
    return np.zeros((len(X), 1), dtype=float)


# -- DateTimeFeaturesTransformer --------------------------------------------

def _datetime_transform(self: Any, X: Any) -> np.ndarray:
    """
    Extract the 10 datetime features that Azure AutoML DateTimeFeaturesTransformer
    produces by default: year, month, day, hour, minute, second, weekday,
    day_of_year, quarter, is_weekend.
    """
    if isinstance(X, pd.Series):
        dt = pd.to_datetime(X, errors="coerce")
    else:
        dt = pd.to_datetime(pd.Series(X), errors="coerce")
    out = pd.DataFrame(
        {
            "year": dt.dt.year.fillna(0).astype(float),
            "month": dt.dt.month.fillna(0).astype(float),
            "day": dt.dt.day.fillna(0).astype(float),
            "hour": dt.dt.hour.fillna(0).astype(float),
            "minute": dt.dt.minute.fillna(0).astype(float),
            "second": dt.dt.second.fillna(0).astype(float),
            "weekday": dt.dt.weekday.fillna(0).astype(float),
            "day_of_year": dt.dt.day_of_year.fillna(0).astype(float),
            "quarter": dt.dt.quarter.fillna(0).astype(float),
            "is_weekend": (dt.dt.weekday >= 5).astype(float),
        }
    )
    return out.values


# -- TransformerPipeline (sklearn_pandas.pipeline) --------------------------

def _transformer_pipeline_transform(self: Any, X: Any) -> Any:
    """Apply each step's transform in sequence, adapting between Series/array."""
    out = X
    for step_name, step in self.steps:
        if hasattr(step, "transform"):
            out = step.transform(out)
        elif hasattr(step, "fit_transform"):
            out = step.fit_transform(out)
    return out


# -- StandardScalerWrapper, SparseNormalizer, MaxAbsScalerWrapper -----------

def _scaler_wrapper_transform(self: Any, X: Any) -> np.ndarray:
    return self.model.transform(X)


def _scaler_wrapper_predict(self: Any, X: Any) -> np.ndarray:
    return self.model.predict(X)


# -- XGBoostRegressor (Azure AutoML wrapper) --------------------------------

def _xgboost_wrapper_predict(self: Any, X: Any) -> np.ndarray:
    inner = getattr(self, "model", None)
    if inner is None:
        raise RuntimeError("XGBoostRegressor: no inner model")
    booster = getattr(inner, "_Booster", None) or getattr(inner, "get_booster", lambda: None)()
    if booster is not None and getattr(booster, "_load_failed", False):
        raise RuntimeError("XGBoostRegressor: old-format booster could not be loaded")
    return inner.predict(X)


def _lightgbm_wrapper_predict(self: Any, X: Any) -> np.ndarray:
    inner = getattr(self, "model", None)
    if inner is None:
        raise RuntimeError("LightGBMRegressor: no inner model")
    return np.asarray(inner.predict(X), dtype=float).reshape(-1)


# -- PreFittedSoftVotingRegressor -------------------------------------------

def _voting_predict(self: Any, X: Any) -> np.ndarray:
    ens = self._wrappedEnsemble
    weights = list(ens.weights or ([1] * len(ens.estimators_)))
    preds, valid_w = [], []
    n_samples = len(X) if hasattr(X, "__len__") else 1
    for est, w in zip(ens.estimators_, weights):
        try:
            p = np.asarray(est.predict(X), dtype=float).reshape(-1)
            if p.size != n_samples:
                continue
            preds.append(p)
            valid_w.append(float(w))
        except Exception:
            pass
    if not preds:
        raise RuntimeError("PreFittedSoftVotingRegressor: all sub-estimators failed")
    valid_w_arr = np.array(valid_w)
    valid_w_arr = valid_w_arr / valid_w_arr.sum()
    return np.average(np.column_stack(preds), axis=1, weights=valid_w_arr)


# -- DataTransformer --------------------------------------------------------

def _datatransformer_transform(self: Any, X: Any) -> np.ndarray:
    if isinstance(X, dict):
        X = pd.DataFrame([X])
    elif not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)

    parts: list[np.ndarray] = []
    for tm in self.transformer_and_mapper_list:
        try:
            out = tm.mapper.transform(X)
            if hasattr(out, "toarray"):
                out = out.toarray()
            out = np.asarray(out, dtype=float)
            if out.ndim == 1:
                out = out.reshape(-1, 1)
            parts.append(out)
        except Exception:
            pass

    if not parts:
        raise RuntimeError("DataTransformer: no transformer produced output")
    return np.hstack(parts)


# -- RegressionPipeline -----------------------------------------------------

def _regression_pipeline_predict(self: Any, X: Any) -> np.ndarray:
    if isinstance(X, dict):
        X = pd.DataFrame([X])
    elif not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)
    return self.pipeline.predict(X)


# ---------------------------------------------------------------------------
# Inject methods into loaded stub classes
# ---------------------------------------------------------------------------

def _patch_loaded_model(obj: Any) -> None:
    """
    After loading a RegressionPipeline from pickle, walk the object tree and
    inject working transform/predict methods into stub instances.
    """
    cls_name = type(obj).__name__

    if cls_name == "RegressionPipeline":
        type(obj).predict = _regression_pipeline_predict  # type: ignore[attr-defined]
        if hasattr(obj, "pipeline") and hasattr(obj.pipeline, "steps"):
            for _, step in obj.pipeline.steps:
                _patch_loaded_model(step)

    elif cls_name == "DataTransformer":
        type(obj).transform = _datatransformer_transform  # type: ignore[attr-defined]
        for tm in getattr(obj, "transformer_and_mapper_list", []):
            _patch_loaded_model(tm)

    elif cls_name == "TransformerAndMapper":
        if hasattr(obj, "mapper"):
            _patch_loaded_model(obj.mapper)

    elif cls_name == "DataFrameMapper":
        # Real DataFrameMapper – patch its feature transformers
        for feat in getattr(obj, "features", []):
            _patch_loaded_model(feat[1])

    elif cls_name == "TransformerPipeline":
        type(obj).transform = _transformer_pipeline_transform  # type: ignore[attr-defined]
        for _, step in getattr(obj, "steps", []):
            _patch_loaded_model(step)

    elif cls_name == "StringCastTransformer":
        type(obj).transform = _stringcast_transform  # type: ignore[attr-defined]

    elif cls_name == "CatImputer":
        type(obj).transform = _catimputer_transform  # type: ignore[attr-defined]

    elif cls_name == "LabelEncoderTransformer":
        type(obj).transform = _labelencoder_transform  # type: ignore[attr-defined]

    elif cls_name == "HashOneHotVectorizerTransformer":
        type(obj).transform = _hashohe_transform  # type: ignore[attr-defined]

    elif cls_name == "ImputationMarker":
        type(obj).transform = _imputation_marker_transform  # type: ignore[attr-defined]

    elif cls_name == "DateTimeFeaturesTransformer":
        type(obj).transform = _datetime_transform  # type: ignore[attr-defined]

    elif cls_name in ("StandardScalerWrapper", "SparseNormalizer", "MaxAbsScalerWrapper"):
        type(obj).transform = _scaler_wrapper_transform  # type: ignore[attr-defined]
        type(obj).predict = _scaler_wrapper_predict  # type: ignore[attr-defined]

    elif cls_name == "XGBoostRegressor":
        type(obj).predict = _xgboost_wrapper_predict  # type: ignore[attr-defined]

    elif cls_name == "LightGBMRegressor":
        type(obj).predict = _lightgbm_wrapper_predict  # type: ignore[attr-defined]

    elif cls_name == "PreFittedSoftVotingRegressor":
        from sklearn.base import BaseEstimator, RegressorMixin

        if not isinstance(obj, BaseEstimator):
            obj.__class__ = type(
                cls_name,
                (BaseEstimator, RegressorMixin, type(obj)),
                {},
            )
        type(obj).predict = _voting_predict  # type: ignore[attr-defined]
        ens = getattr(obj, "_wrappedEnsemble", None)
        if ens and hasattr(ens, "estimators_"):
            for est in ens.estimators_:
                _patch_loaded_model(est)

    # sklearn Pipeline (the inner pipeline inside RegressionPipeline)
    elif cls_name == "Pipeline" and hasattr(obj, "steps"):
        for _, step in obj.steps:
            _patch_loaded_model(step)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def install_azureml_compat() -> None:
    """
    Call once at startup (or before the first pickle.load of an Azure AutoML model).
    Idempotent – safe to call multiple times.
    """
    global _COMPAT_INSTALLED
    if _COMPAT_INSTALLED:
        return

    warnings.filterwarnings(
        "ignore", category=UserWarning, module="sklearn"
    )

    _patch_sklearn_tosequence()
    import sklearn_pandas  # noqa: F401 – ensure real DataFrameMapper is importable
    _patch_xgboost_booster()
    _install_azureml_stubs()

    _COMPAT_INSTALLED = True


def load_azure_automl_pickle(path: str) -> Any:
    """
    Load an Azure AutoML pickle and return a predict-able object.

    Parameters
    ----------
    path : str
        Absolute or project-root-relative path to model.pkl.

    Returns
    -------
    object with .predict(pd.DataFrame) -> np.ndarray
    """
    import pickle

    install_azureml_compat()

    with open(path, "rb") as f:
        model = pickle.load(f)

    _patch_loaded_model(model)
    _reconvert_xgboost_boosters(model)  # fix old pre-1.6 JSON boosters for xgboost 2.x
    return model
