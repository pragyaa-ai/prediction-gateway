from pydantic import BaseModel, Field
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
    score: Optional[float] = Field(default=None, exclude=True)
    latency_ms: Optional[int] = Field(default=None, exclude=True)


class ModelConfig(BaseModel):
    """Model configuration from YAML"""
    provider: str
    endpoint_url: str
    auth_type: str = "none"
    api_key: Optional[str] = None
    timeout_ms: int = 3000
    version: str
    input_mapper: str
    output_mapper: str
    enabled: bool = True


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
    latency_ms: int
    client_id: str
    timestamp: str
    status: str  # success, error, timeout
    error_message: Optional[str] = None
