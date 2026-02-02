import time
import os
import pyautogui
import pyperclip
from app.core.plugin_base import PluginBase

# Try import for pygetwindow
try:
    import pygetwindow
except ImportError:
    pygetwindow = None

class AntigravityPlugin(PluginBase):
    def on_load(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        self.exec_path = self.config.get("executable_path", "Antigravity.exe")
        self.status = "idle"
        self.current_action = "Ready"

    def shutdown(self):
        pass

    def is_busy(self) -> bool:
        return self.status == "running"

    def heartbeat(self):
        return {
            "status": self.status,
            "progress": self.current_action,
            "message": "Antigravity Active"
        }

    def execute(self, command: str, context: dict) -> str:
        """
        Command format: "Build <prompt>" or just "<prompt>"
        We assume the user wants to creating a new task if they typed `/ag <something>`.
        """
        self.status = "running"
        try:
            self.clear_stop()
            self.current_action = "parsing"
            
            project_root = self.config.get("project_root", "C:\\SynapseProjects")
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            project_path = os.path.join(project_root, f"Project_{ts}")
            
            self.current_action = "focusing_window"
            self.check_stop()
            self._focus_window()
            
            self.current_action = "creating_project"
            self.check_stop()
            self._create_new_task(command, project_path)
            
            self.current_action = "monitoring"
            self._monitor_progress(project_path)
            
            self.current_action = "done"
            return f"Task completed. Project at {project_path}"
        except Exception as e:
            self.status = "error"
            raise e
        finally:
            self.status = "idle"

    def _focus_window(self):
        if not pygetwindow:
            # On Mac/Linux dev env, we might skip or fail.
            # print("Warning: pygetwindow not available. Skipping GUI focus.")
            return 

        candidates = [w for w in pygetwindow.getAllWindows() if "antigravity" in w.title.lower() or "code" in w.title.lower()]
        if not candidates:
            # Launch
            try:
                os.startfile(self.exec_path)
                time.sleep(10)
                candidates = [w for w in pygetwindow.getAllWindows() if "antigravity" in w.title.lower()]
            except:
                pass
        
        if candidates:
            try:
                candidates[0].activate()
            except:
                pass

    def _create_new_task(self, prompt: str, path: str):
        # Ctrl+K, Ctrl+O -> Open Folder
        self._type_hotkey(['ctrl', 'k'])
        self._type_hotkey(['ctrl', 'o'])
        
        pyperclip.copy(path)
        self._type_hotkey(['ctrl', 'v'])
        pyautogui.press('enter')
        
        time.sleep(5) # Wait reload
        self.check_stop()
        
        # Ctrl+L -> Chat
        self._type_hotkey(['ctrl', 'l'])
        time.sleep(1)
        
        pyperclip.copy(prompt)
        self._type_hotkey(['ctrl', 'v'])
        pyautogui.press('enter')

    def _type_hotkey(self, keys):
        self.check_stop()
        pyautogui.hotkey(*keys)

    def _monitor_progress(self, path: str):
        # Poll for DONE.txt
        start = time.time()
        done_file = os.path.join(path, "DONE.txt")
        while (time.time() - start) < 1800: # 30 mins
            self.check_stop()
            if os.path.exists(done_file):
                return
            time.sleep(2)
        raise TimeoutError("Task timed out.")
