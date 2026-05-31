from abc import ABC, abstractmethod
from typing import Dict, Any
import httpx
import time
import boto3
import json
from models.schemas import InferenceRequest, InferenceResponse, ModelConfig
from adapters.mappers import get_input_mapper, get_output_mapper
from adapters.response_utils import build_inference_response


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
        
        return build_inference_response(request, standardized, latency_ms)


class AWSSageMakerAdapter(BaseModelAdapter):
    """Adapter for AWS SageMaker hosted models"""
    
    async def predict(self, request: InferenceRequest, config: ModelConfig) -> InferenceResponse:
        """
        Call AWS SageMaker endpoint and return standardized response
        """
        start_time = time.time()
        
        # Get mapper functions
        input_mapper = get_input_mapper(config.input_mapper)
        output_mapper = get_output_mapper(config.output_mapper)
        
        # Transform inputs to SageMaker format
        sagemaker_inputs = input_mapper(request.inputs)
        
        try:
            # Initialize SageMaker runtime client
            runtime = boto3.client(
                'sagemaker-runtime',
                region_name=getattr(config, 'region', 'us-east-1')
            )
            
            # Call SageMaker endpoint
            response = runtime.invoke_endpoint(
                EndpointName=getattr(config, 'endpoint_name', config.endpoint_url.split('/')[-2]),
                ContentType='application/json',
                Body=json.dumps(sagemaker_inputs)
            )
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            
        except Exception as e:
            raise RuntimeError(f"AWS SageMaker request failed: {str(e)}")
        
        # Transform output to standard format
        standardized = output_mapper(result)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        return build_inference_response(request, standardized, latency_ms)


# Adapter factory
def get_adapter(provider: str) -> BaseModelAdapter:
    """Get adapter instance for provider"""
    if provider == "local_artifact":
        from adapters.local_inference import LocalArtifactAdapter

        return LocalArtifactAdapter()

    adapters = {
        "azure_ml": AzureMLAdapter(),
        "aws_sagemaker": AWSSageMakerAdapter(),
    }

    adapter = adapters.get(provider)
    if not adapter:
        raise ValueError(f"Unknown provider: {provider}")

    return adapter
