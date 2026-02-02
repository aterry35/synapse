import os
import json
import importlib.util
from typing import Dict, Type
from app.core.plugin_base import PluginBase
from app.core.config_manager import ConfigManager

class PluginManager:
    _instance = None
    
    def __init__(self):
        self.plugins: Dict[str, PluginBase] = {} # id -> instance
        self.trigger_map: Dict[str, PluginBase] = {} # trigger -> instance
        self.manifests: Dict[str, dict] = {} # id -> manifest

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def load_plugins(self, plugin_dir: str = "app/plugins"):
        print(f"Scanning for plugins in {plugin_dir}...")
        if not os.path.exists(plugin_dir):
            print(f"Plugin directory {plugin_dir} does not exist.")
            return

        for entry in os.scandir(plugin_dir):
            if entry.is_dir():
                manifest_path = os.path.join(entry.path, "plugin.json")
                if os.path.exists(manifest_path):
                    self._load_single_plugin(entry.path, manifest_path)

    def _load_single_plugin(self, folder_path: str, manifest_path: str):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Validate Manifest
            required_keys = ["name", "id", "version", "entry_point", "triggers"]
            for key in required_keys:
                if key not in manifest:
                    print(f"Skipping {folder_path}: Missing mandatory key '{key}' in manifest.")
                    return

            plugin_id = manifest["id"]
            
            # Check Config if enabled
            plugin_config = ConfigManager.get_plugin_config(plugin_id)
            if plugin_config.get("enabled") is False:
                print(f"Plugin {plugin_id} is disabled in config.json. Skipping.")
                return

            # Import Entry Point
            entry_point_str = manifest["entry_point"]
            module_name, class_name = entry_point_str.rsplit(".", 1)
            
            # Construct absolute module path for importlib
            file_path = os.path.join(folder_path, f"{module_name.split('.')[0]}.py")
            if not os.path.exists(file_path):
                 # Try assuming the module_name matches filename exactly in that folder
                 # But usually entry_point is "filename.ClassName"
                 file_path = os.path.join(folder_path, f"{module_name}.py")
            
            spec = importlib.util.spec_from_file_location(f"plugins.{plugin_id}", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            plugin_class: Type[PluginBase] = getattr(module, class_name)
            
            # Instantiate
            plugin_instance = plugin_class(plugin_config)
            plugin_instance.on_load()
            
            # Register
            self.plugins[plugin_id] = plugin_instance
            self.manifests[plugin_id] = manifest
            
            for trigger in manifest["triggers"]:
                if trigger in self.trigger_map:
                    print(f"Conflict: Trigger '{trigger}' already registered. Skipping for {plugin_id}.")
                else:
                    self.trigger_map[trigger] = plugin_instance
            
            print(f"Loaded Plugin: {manifest['name']} ({plugin_id})")

        except Exception as e:
            print(f"Failed to load plugin from {folder_path}: {e}")

    def get_plugin_by_trigger(self, trigger: str) -> PluginBase:
        return self.trigger_map.get(trigger)

    def get_plugin_by_id(self, plugin_id: str) -> PluginBase:
        return self.plugins.get(plugin_id)

    def shutdown_all(self):
        for p in self.plugins.values():
            try:
                p.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin: {e}")
