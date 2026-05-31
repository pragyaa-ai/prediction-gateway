from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, Any, Dict
import uuid


class InferenceRequest(BaseModel):
    """Canonical internal request object used throughout the gateway"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str
    inputs: Dict[str, Any]
    client_id: str = "on_prem_deployment"  # Default for on-prem
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PredictionRequest(BaseModel):
    """External API request format"""
    request_id: Optional[str] = None
    model_id: str
    inputs: Dict[str, Any]
    client_id: Optional[str] = None  # Make it optional
    
    def to_inference_request(self) -> InferenceRequest:
        """Convert external request to canonical internal format"""
        return InferenceRequest(
            request_id=self.request_id or str(uuid.uuid4()),
            model_id=self.model_id,
            inputs=self.inputs,
            client_id=self.client_id or "on_prem_deployment"  # Default value
        )


class InferenceResponse(BaseModel):
    """Standardized prediction response"""
    request_id: str
    model_id: str
    prediction: Any
    score: Optional[float] = None
    probability: Optional[float] = None
    latency_ms: Optional[int] = None


class ModelConfig(BaseModel):
    """Model configuration from YAML"""
    provider: str
    endpoint_url: str = ""
    auth_type: str = "none"
    api_key: Optional[str] = None
    timeout_ms: int = 3000
    version: str
    input_mapper: str
    output_mapper: str
    enabled: bool = True
    # On-disk artifacts (provider: local_artifact)
    local_artifact_path: Optional[str] = None
    local_artifact_format: Optional[str] = None  # pickle | joblib
    local_model_kind: Optional[str] = None  # sklearn | noshow_xgboost_bundle

    @model_validator(mode="after")
    def validate_provider_fields(self) -> "ModelConfig":
        if self.provider == "local_artifact":
            if not self.local_artifact_path:
                raise ValueError("local_artifact_path is required when provider is 'local_artifact'")
            if not self.local_artifact_format:
                raise ValueError("local_artifact_format is required when provider is 'local_artifact'")
            fmt = self.local_artifact_format.lower()
            if fmt not in ("pickle", "joblib", "azure_automl_pickle"):
                raise ValueError("local_artifact_format must be 'pickle', 'joblib', or 'azure_automl_pickle'")
        elif not self.endpoint_url:
            raise ValueError(f"endpoint_url is required for provider '{self.provider}'")
        return self


class PredictionLog(BaseModel):
    """OpenSearch logging schema"""
    request_id: str
    model_id: str
    model_version: str
    provider: str
    inputs: Dict[str, Any]  # Store actual input data
    inputs_hash: str  # Keep for backward compatibility and deduplication
    prediction: Any
    score: Optional[float]
    probability: Optional[float] = None
    latency_ms: int
    client_id: str
    timestamp: str
    status: str  # success, error, timeout
    error_message: Optional[str] = None
