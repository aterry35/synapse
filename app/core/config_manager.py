import json
import os
from typing import Dict, Any

class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    @classmethod
    def load(cls, config_path: str = "config.json"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file {config_path} not found.")
        
        with open(config_path, 'r') as f:
            cls._config = json.load(f)
        
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get_server_config(cls):
        return cls._config.get("server", {})
    
    @classmethod
    def get_features(cls):
        return cls._config.get("features", {})
    
    @classmethod
    def get_plugin_config(cls, plugin_id: str):
        return cls._config.get("plugins", {}).get(plugin_id, {})

    @classmethod
    def is_docker_allowed(cls):
        return cls.get_features().get("docker_enabled", False)

    @classmethod
    def is_scheduler_enabled(cls):
        return cls.get_features().get("scheduler_enabled", False)

    @classmethod
    def is_remote_enabled(cls):
        return cls.get_server_config().get("remote_enabled", False)

    @classmethod
    def get_google_api_key(cls):
        # Ensure dotenv is loaded? 
        # Ideally Orchestrator/Main loads it, but safe to fetch here.
        return os.getenv("GOOGLE_API_KEY")
