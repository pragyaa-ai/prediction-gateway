"""
API Key management service
"""
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
import json
from pathlib import Path


class APIKeyManager:
    """Manage API keys for client access"""
    
    def __init__(self, keys_file: str = "config/api_keys.json"):
        self.keys_file = Path(keys_file)
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        self._keys = self._load_keys()
    
    def _load_keys(self) -> Dict:
        """Load API keys from file"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_keys(self):
        """Save API keys to file"""
        with open(self.keys_file, 'w') as f:
            json.dump(self._keys, f, indent=2)
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def generate_key(
        self,
        client_name: str,
        client_email: str,
        created_by: str,
        permissions: List[str] = None
    ) -> Dict:
        """Generate a new API key"""
        # Generate secure random key
        raw_key = f"pragyaa_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        
        key_data = {
            "key_hash": key_hash,
            "client_name": client_name,
            "client_email": client_email,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "permissions": permissions or ["predict"],
            "active": True,
            "usage_count": 0,
            "last_used": None
        }
        
        self._keys[key_hash] = key_data
        self._save_keys()
        
        return {
            "api_key": raw_key,  # Only shown once!
            "key_hash": key_hash,
            **key_data
        }
    
    def validate_key(self, api_key: str) -> Optional[Dict]:
        """Validate an API key"""
        key_hash = self._hash_key(api_key)
        key_data = self._keys.get(key_hash)
        
        if not key_data or not key_data.get("active"):
            return None
        
        # Update usage
        key_data["usage_count"] += 1
        key_data["last_used"] = datetime.utcnow().isoformat()
        self._save_keys()
        
        return key_data
    
    def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key"""
        if key_hash in self._keys:
            self._keys[key_hash]["active"] = False
            self._save_keys()
            return True
        return False
    
    def list_keys(self) -> List[Dict]:
        """List all API keys (without raw keys)"""
        return [
            {
                "key_hash": key_hash[:16] + "...",
                **{k: v for k, v in data.items() if k != "key_hash"}
            }
            for key_hash, data in self._keys.items()
        ]
    
    def get_key_stats(self, key_hash: str) -> Optional[Dict]:
        """Get statistics for an API key"""
        return self._keys.get(key_hash)


# Global API key manager
api_key_manager = APIKeyManager()
