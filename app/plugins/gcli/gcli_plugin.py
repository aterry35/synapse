import time
from app.core.plugin_base import PluginBase
from app.plugins.gcli.sdlc_workflow import SDLCManager

class GCLIPlugin(PluginBase):
    def on_load(self):
        self.manager = SDLCManager(self.config)
        self.status = "idle"

    def shutdown(self):
        self.manager.terminate()

    def is_busy(self) -> bool:
        return self.status == "running"

    def heartbeat(self):
        return {
            "status": self.status,
            "progress": self.manager.current_phase,
            "message": self.manager.last_msg
        }

    def execute(self, command: str, context: dict) -> str:
        self.status = "running"
        self.clear_stop()
        try:
            if command.strip().lower() == "approve":
                # Resume Flow
                result = self.manager.resume_approval(stop_callback=self.check_stop)
                return result
            elif command.strip().lower().startswith("refine"):
                # Refine Flow
                # /gcli refine add dark mode
                feedback = command.strip()[6:].strip()
                result = self.manager.refine_requirements(feedback, stop_callback=self.check_stop)
                return result
            else:
                # Start New Flow
                result = self.manager.start_new_project(command, stop_callback=self.check_stop)
                return result
        except InterruptedError:
            self.manager.terminate()
            raise
        except Exception as e:
            raise e
        finally:
            self.status = "idle"
