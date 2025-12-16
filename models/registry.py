import yaml
from pathlib import Path
from typing import Dict, Optional
from models.schemas import ModelConfig


class ModelRegistry:
    """Loads and manages model configurations from YAML"""
    
    def __init__(self, config_path: str = "config/models.yaml"):
        self.config_path = Path(config_path)
        self._models: Dict[str, ModelConfig] = {}
        self.load_models()
    
    def load_models(self) -> None:
        """Load model configurations from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        self._models = {}
        for model_id, config in data.items():
            self._models[model_id] = ModelConfig(**config)
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID"""
        return self._models.get(model_id)
    
    def list_models(self) -> Dict[str, ModelConfig]:
        """List all registered models"""
        return self._models.copy()
    
    def is_model_enabled(self, model_id: str) -> bool:
        """Check if model is enabled"""
        model = self.get_model(model_id)
        return model.enabled if model else False
    
    def toggle_model(self, model_id: str) -> Optional[bool]:
        """
        Toggle model enabled/disabled state
        
        Returns:
            New enabled state (True/False), or None if model not found
        """
        model = self.get_model(model_id)
        if not model:
            return None
        
        # Toggle the state
        model.enabled = not model.enabled
        
        return model.enabled
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.load_models()


# Global registry instance
registry = ModelRegistry()
