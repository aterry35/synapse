import threading
import datetime
from sqlalchemy.orm import Session
from app.core.plugin_manager import PluginManager
from app.core.config_manager import ConfigManager
from app.core.task_store import TaskLog, SessionLocal
from app.core.watchdog import Watchdog

class Orchestrator:
    _instance = None
    
    def __init__(self):
        self.lock = threading.Lock()
        self.active_plugin_id = None
        self.plugin_manager = PluginManager.get_instance()
        self.watchdog = Watchdog(self)
        self.watchdog.start()

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def create_task(self, text: str) -> str:
        """
        Creates a task entry in the DB and returns the ID.
        This runs synchronously and quickly.
        """
        # 1. Parse Trigger (Basic)
        parts = text.strip().split(" ", 1)
        trigger = parts[0]
        
        db = SessionLocal()
        task = TaskLog(command_text=text, trigger_used=trigger, status="QUEUED")
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = str(task.id)
        db.close()
        return task_id

    def handle_command(self, task_id: str):
        """
        Executes a task by ID.
        Runs in background thread.
        """
        db = SessionLocal()
        task = db.query(TaskLog).filter(TaskLog.id == int(task_id)).first()
        if not task:
            db.close()
            return
            
        task.status = "RUNNING"
        task.started_at = datetime.datetime.now()
        db.commit()
        
        text = task.command_text
        # 1. Parse Trigger
        parts = text.strip().split(" ", 1)
        trigger = parts[0]
        payload = parts[1] if len(parts) > 1 else ""
        
        # 2. Routing
        plugin = self.plugin_manager.get_plugin_by_trigger(trigger)
        if not plugin:
            if not text.startswith("/"):
                plugin = self.plugin_manager.get_plugin_by_id("system")
                payload = text 
                trigger = "(default)"
            else:
                task.status = "FAILED"
                task.error_message = "Unknown slash command/plugin."
                db.commit()
                db.close()
                return

        if not plugin:
             task.status = "FAILED"
             task.error_message = "System plugin not found/loaded."
             db.commit()
             db.close()
             return

        # 3. Execution Lock
        if not self.lock.acquire(blocking=False):
             task.status = "FAILED"
             task.error_message = f"System busy running {self.active_plugin_id}. Use /stop."
             db.commit()
             db.close()
             return

        self.active_plugin_id = plugin.config.get("id", "unknown")
        task.plugin_id = self.active_plugin_id
        db.commit()
        
        try:
            # Execute
            result = plugin.execute(payload, {"trigger": trigger})
            task.status = "DONE"
            task.result_message = str(result)
        except InterruptedError:
            task.status = "FAILED"
            task.error_message = "User Aborted"
        except Exception as e:
            task.status = "FAILED"
            task.error_message = str(e)
        finally:
            self.active_plugin_id = None
            self.lock.release()
            task.updated_at = datetime.datetime.now()
            db.commit()
            db.close()

    def abort_active_task(self):
        """
        Global Stop / Kill Switch
        """
        if not self.active_plugin_id:
            return "No active task to stop."
        
        plugin = self.plugin_manager.get_plugin_by_id(self.active_plugin_id)
        if plugin:
            plugin.request_stop()
            # We could also force kill if it doesn't stop in X seconds context
            # But cooperative first.
            return f"Stop signal sent to {self.active_plugin_id}..."
        return "Active plugin not found in manager."

    def _log_failure(self, cmd, trig, msg):
        db = SessionLocal()
        task = TaskLog(command_text=cmd, trigger_used=trig, status="FAILED", error_message=msg)
        db.add(task)
        db.commit()
        db.close()
        return msg
