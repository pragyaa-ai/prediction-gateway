from opensearchpy import OpenSearch, RequestsHttpConnection
from typing import Optional, Dict, Any
import logging
import hashlib
from datetime import datetime
from models.schemas import PredictionLog, InferenceRequest, InferenceResponse, ModelConfig
from config.settings import settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """Async OpenSearch client for prediction logging"""
    
    def __init__(self):
        self.client: Optional[OpenSearch] = None
        self._connected = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenSearch connection"""
        try:
            self.client = OpenSearch(
                hosts=[{
                    'host': settings.opensearch_host,
                    'port': settings.opensearch_port
                }],
                http_auth=(settings.opensearch_user, settings.opensearch_password),
                use_ssl=settings.opensearch_use_ssl,
                verify_certs=settings.opensearch_verify_certs,
                connection_class=RequestsHttpConnection,
                timeout=10
            )
            
            # Test connection
            info = self.client.info()
            logger.info(f"Connected to OpenSearch: {info['version']['number']}")
            self._connected = True
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            self._connected = False
    
    def is_healthy(self) -> bool:
        """Check OpenSearch connection health"""
        if not self.client:
            return False
        
        try:
            self.client.cluster.health()
            return True
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return False
    
    def _get_index_name(self) -> str:
        """Generate index name with date pattern"""
        date_suffix = datetime.utcnow().strftime("%Y.%m.%d")
        return f"{settings.opensearch_index_pattern}-{date_suffix}"
    
    def _hash_inputs(self, inputs: Dict[str, Any]) -> str:
        """Generate SHA256 hash of inputs"""
        input_str = str(sorted(inputs.items()))
        return hashlib.sha256(input_str.encode()).hexdigest()
    
    async def log_prediction(
        self,
        request: InferenceRequest,
        response: InferenceResponse,
        config: ModelConfig,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> None:
        """
        Log prediction to OpenSearch (non-blocking)
        
        This method catches all exceptions to prevent inference failures
        """
        if not self._connected:
            logger.warning("OpenSearch not connected, skipping log")
            return
        
        try:
            log_entry = PredictionLog(
                request_id=request.request_id,
                model_id=request.model_id,
                model_version=config.version,
                provider=config.provider,
                inputs_hash=self._hash_inputs(request.inputs),
                prediction=response.prediction,
                score=response.score,
                latency_ms=response.latency_ms,
                client_id=request.client_id,
                timestamp=request.timestamp.isoformat(),
                status=status,
                error_message=error_message
            )
            
            index_name = self._get_index_name()
            
            # Ensure index exists with proper mapping
            self._ensure_index(index_name)
            
            # Index document
            self.client.index(
                index=index_name,
                body=log_entry.model_dump(),
                id=request.request_id
            )
            
            logger.debug(f"Logged prediction {request.request_id} to {index_name}")
            
        except Exception as e:
            # NEVER fail the inference due to logging errors
            logger.error(f"Failed to log prediction to OpenSearch: {e}")
    
    def _ensure_index(self, index_name: str) -> None:
        """Create index with proper mapping if it doesn't exist"""
        if self.client.indices.exists(index=index_name):
            return
        
        mapping = {
            "mappings": {
                "properties": {
                    "request_id": {"type": "keyword"},
                    "model_id": {"type": "keyword"},
                    "model_version": {"type": "keyword"},
                    "provider": {"type": "keyword"},
                    "inputs_hash": {"type": "keyword"},
                    "prediction": {"type": "text"},
                    "score": {"type": "float"},
                    "latency_ms": {"type": "integer"},
                    "client_id": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "status": {"type": "keyword"},
                    "error_message": {"type": "text"}
                }
            }
        }
        
        try:
            self.client.indices.create(index=index_name, body=mapping)
            logger.info(f"Created OpenSearch index: {index_name}")
        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")
    
    def search_recent_predictions(self, limit: int = 50) -> list:
        """Search for recent predictions across all indices"""
        if not self._connected:
            return []
        
        try:
            index_pattern = f"{settings.opensearch_index_pattern}-*"
            
            query = {
                "size": limit,
                "sort": [{"timestamp": {"order": "desc"}}],
                "query": {"match_all": {}}
            }
            
            response = self.client.search(index=index_pattern, body=query)
            return [hit["_source"] for hit in response["hits"]["hits"]]
            
        except Exception as e:
            logger.error(f"Failed to search predictions: {e}")
            return []
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics per model"""
        if not self._connected:
            return {}
        
        try:
            index_pattern = f"{settings.opensearch_index_pattern}-*"
            
            query = {
                "size": 0,
                "aggs": {
                    "models": {
                        "terms": {"field": "model_id", "size": 100},
                        "aggs": {
                            "avg_latency": {"avg": {"field": "latency_ms"}},
                            "status_counts": {
                                "terms": {"field": "status"}
                            }
                        }
                    }
                }
            }
            
            response = self.client.search(index=index_pattern, body=query)
            return response["aggregations"]
            
        except Exception as e:
            logger.error(f"Failed to get model stats: {e}")
            return {}
    
    def get_prediction_volume_timeline(self, hours: int = 24) -> Dict[str, Any]:
        """Get prediction volume over time"""
        if not self._connected:
            return {"timeline": []}
        
        try:
            index_pattern = f"{settings.opensearch_index_pattern}-*"
            
            query = {
                "size": 0,
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": f"now-{hours}h"
                        }
                    }
                },
                "aggs": {
                    "predictions_over_time": {
                        "date_histogram": {
                            "field": "timestamp",
                            "fixed_interval": "1h"
                        },
                        "aggs": {
                            "by_model": {
                                "terms": {"field": "model_id"}
                            }
                        }
                    }
                }
            }
            
            response = self.client.search(index=index_pattern, body=query)
            return response["aggregations"]
            
        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            return {"predictions_over_time": {"buckets": []}}
    
    def get_error_rate_by_model(self) -> Dict[str, float]:
        """Calculate error rate percentage for each model"""
        if not self._connected:
            return {}
        
        try:
            index_pattern = f"{settings.opensearch_index_pattern}-*"
            
            query = {
                "size": 0,
                "aggs": {
                    "models": {
                        "terms": {"field": "model_id", "size": 100},
                        "aggs": {
                            "error_rate": {
                                "filters": {
                                    "filters": {
                                        "errors": {"term": {"status": "error"}},
                                        "total": {"match_all": {}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            response = self.client.search(index=index_pattern, body=query)
            
            error_rates = {}
            for bucket in response["aggregations"]["models"]["buckets"]:
                model_id = bucket["key"]
                total = bucket["error_rate"]["total"]["doc_count"]
                errors = bucket["error_rate"]["errors"]["doc_count"]
                error_rates[model_id] = (errors / total * 100) if total > 0 else 0
            
            return error_rates
            
        except Exception as e:
            logger.error(f"Failed to calculate error rates: {e}")
            return {}
    
    def search_predictions(
        self,
        model_id: Optional[str] = None,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Advanced search with filters"""
        if not self._connected:
            return []
        
        try:
            index_pattern = f"{settings.opensearch_index_pattern}-*"
            
            # Build query
            must_clauses = []
            
            if model_id:
                must_clauses.append({"term": {"model_id": model_id}})
            if client_id:
                must_clauses.append({"term": {"client_id": client_id}})
            if status:
                must_clauses.append({"term": {"status": status}})
            if from_date or to_date:
                range_query = {"range": {"timestamp": {}}}
                if from_date:
                    range_query["range"]["timestamp"]["gte"] = from_date
                if to_date:
                    range_query["range"]["timestamp"]["lte"] = to_date
                must_clauses.append(range_query)
            
            query = {
                "size": limit,
                "sort": [{"timestamp": {"order": "desc"}}],
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}]
                    }
                }
            }
            
            response = self.client.search(index=index_pattern, body=query)
            return [hit["_source"] for hit in response["hits"]["hits"]]
            
        except Exception as e:
            logger.error(f"Failed to search predictions: {e}")
            return []


# Global OpenSearch client instance
opensearch_client = OpenSearchClient()
