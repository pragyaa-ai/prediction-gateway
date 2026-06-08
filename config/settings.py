from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    # Gateway
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    
    # Local on-disk models (see config/models.yaml local_artifact_path)
    # Override when models live outside the repo, e.g. /opt/ml-models
    local_models_dir: Optional[str] = None

    # Python binary with AutoGluon installed (requirements-autogluon.txt).
    # Used for no_show_fakeeh_ksa_local when autogluon is not in the main venv.
    autogluon_python: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AUTOGLUON_PYTHON", "AUTOGUON_PYTHON"),
    )

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False
    # OpenSearch: one index per model → {prefix}-{model-slug}
    opensearch_index_prefix: str = "ml-predictions"
    opensearch_index_pattern: Optional[str] = None  # legacy .env alias for prefix
    
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
    
settings = Settings()
