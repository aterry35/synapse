import time
import threading
from app.core.config_manager import ConfigManager
from app.core.plugin_manager import PluginManager

class Watchdog:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.running = False
        self.thread = None

    def start(self):
        if ConfigManager.is_scheduler_enabled():
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print("Watchdog started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _monitor_loop(self):
        while self.running:
            # 1. Identify active plugin
            active_plugin_id = self.orchestrator.active_plugin_id
            
            if active_plugin_id:
                plugin = PluginManager.get_instance().get_plugin_by_id(active_plugin_id)
                if plugin:
                    heartbeat = plugin.heartbeat()
                    # Here we could implement advanced logic:
                    # - Save heartbeat to DB
                    # - Check if stall (e.g. heartbeat['progress'] hasn't changed in X sec)
                    # For now, we just print if it looks stuck or errors.
                    if heartbeat.get('status') == 'error':
                        print(f"WATCHDOG ALERT: Plugin {active_plugin_id} reported error: {heartbeat.get('message')}")
                    
                    # Logic to auto-recover/abort if stalled could go here
            
            time.sleep(2)
