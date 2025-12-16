from abc import ABC, abstractmethod
from typing import Dict, Any
import httpx
import time
from models.schemas import InferenceRequest, InferenceResponse, ModelConfig
from adapters.mappers import get_input_mapper, get_output_mapper


class BaseModelAdapter(ABC):
    """Base adapter for all ML model providers"""
    
    @abstractmethod
    async def predict(self, request: InferenceRequest, config: ModelConfig) -> InferenceResponse:
        """
        Execute prediction request
        
        Args:
            request: Canonical inference request
            config: Model configuration
            
        Returns:
            Standardized inference response
        """
        pass


class AzureMLAdapter(BaseModelAdapter):
    """Adapter for Azure ML hosted models"""
    
    async def predict(self, request: InferenceRequest, config: ModelConfig) -> InferenceResponse:
        """
        Call Azure ML endpoint and return standardized response
        """
        start_time = time.time()
        
        # Get mapper functions
        input_mapper = get_input_mapper(config.input_mapper)
        output_mapper = get_output_mapper(config.output_mapper)
        
        # Transform inputs to Azure format
        azure_inputs = input_mapper(request.inputs)
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if config.auth_type == "key" and config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        
        # Call Azure endpoint
        timeout_seconds = config.timeout_ms / 1000.0
        
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            try:
                response = await client.post(
                    config.endpoint_url,
                    json=azure_inputs,
                    headers=headers
                )
                response.raise_for_status()
                azure_response = response.json()
                
            except httpx.TimeoutException:
                latency_ms = int((time.time() - start_time) * 1000)
                raise TimeoutError(f"Azure ML request timeout after {latency_ms}ms")
            
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Azure ML error: {e.response.status_code} - {e.response.text}")
            
            except Exception as e:
                raise RuntimeError(f"Azure ML request failed: {str(e)}")
        
        # Transform output to standard format
        standardized = output_mapper(azure_response)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        return InferenceResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            prediction=standardized["prediction"],
            score=standardized.get("score"),
            latency_ms=latency_ms
        )


# Adapter factory
def get_adapter(provider: str) -> BaseModelAdapter:
    """Get adapter instance for provider"""
    adapters = {
        "azure_ml": AzureMLAdapter(),
    }
    
    adapter = adapters.get(provider)
    if not adapter:
        raise ValueError(f"Unknown provider: {provider}")
    
    return adapter
