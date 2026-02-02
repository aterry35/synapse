from abc import ABC, abstractmethod
from typing import Dict, Any

class PluginBase(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._stop_requested = False

    @abstractmethod
    def on_load(self):
        """Called when plugin is loaded. Initialize resources here."""
        pass

    @abstractmethod
    def shutdown(self):
        """Called on system shutdown or plugin disable. Cleanup resources."""
        pass

    @abstractmethod
    def execute(self, command: str, context: Dict[str, Any]) -> str:
        """Execute a command. Must be blocking but cooperative with request_stop."""
        pass

    @abstractmethod
    def is_busy(self) -> bool:
        """Return True if currently executing a task."""
        pass
    
    @abstractmethod
    def heartbeat(self) -> Dict[str, Any]:
        """Return status dict: {'status': '...', 'progress': '...', 'message': '...'}"""
        pass

    def request_stop(self):
        """Signal the plugin to stop execution."""
        self._stop_requested = True
    
    def clear_stop(self):
        self._stop_requested = False
    
    def check_stop(self):
        """Helper to raise exception if stop requested."""
        if self._stop_requested:
            raise InterruptedError("Plugin execution aborted by user.")
