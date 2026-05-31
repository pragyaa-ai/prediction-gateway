from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Gateway
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    
    # Local on-disk models (see config/models.yaml local_artifact_path)
    # Override when models live outside the repo, e.g. /opt/ml-models
    local_models_dir: Optional[str] = None

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False
    opensearch_index_pattern: str = "ml-predictions-v1"
    
    # Azure
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    
    # Admin
    admin_username: str = "admin"
    admin_password: str = "changeme"
    
    # Email SMTP (optional - for alerts)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@pragyaa.ai"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
