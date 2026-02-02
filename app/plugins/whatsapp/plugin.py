import os
import subprocess
import threading
import time
from typing import Dict, Any
from app.core.plugin_base import PluginBase

class WhatsappPlugin(PluginBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.process = None
        self.thread = None
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))

    def on_load(self):
        """Starts the Node.js bridge."""
        print("[WhatsApp] Loading plugin...")
        
        # Check for node_modules
        node_modules = os.path.join(self.plugin_dir, "node_modules")
        if not os.path.exists(node_modules):
            print("[WhatsApp] Installing dependencies via npm...")
            try:
                # Use local cache to avoid permission issues
                subprocess.check_call(["npm", "install", "--cache", "./.npm-cache"], cwd=self.plugin_dir)
            except subprocess.CalledProcessError as e:
                print(f"[WhatsApp] Failed to install dependencies: {e}")
                return

        # Start Node.js process
        self._start_node_process()

    def _start_node_process(self):
        """Starts the 'node index.js' subprocess."""
        try:
            cmd = ["node", "index.js"]
            print(f"[WhatsApp] Starting bridge in {self.plugin_dir}...")
            
            # We want to pipe stdout so we can see the QR code in the main log
            self.process = subprocess.Popen(
                cmd,
                cwd=self.plugin_dir,
                stdout=None, # Inherit stdout to show QR code in terminal
                stderr=None, # Inherit stderr
                text=True
            )
            print(f"[WhatsApp] Bridge started (PID: {self.process.pid})")
            
        except Exception as e:
            print(f"[WhatsApp] Failed to start bridge: {e}")

    def shutdown(self):
        """Stops the Node.js subprocess."""
        print("[WhatsApp] Shutting down...")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("[WhatsApp] Bridge stopped.")

    def execute(self, command: str, context: Dict[str, Any]) -> str:
        # This plugin doesn't handle internal commands yet, it's just a bridge.
        return "WhatsApp bridge is running."

    def is_busy(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def heartbeat(self) -> Dict[str, Any]:
        alive = self.is_busy()
        return {
            "status": "running" if alive else "stopped",
            "pid": self.process.pid if self.process else None
        }
