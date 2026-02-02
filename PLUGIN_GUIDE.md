# 🔌 Synapse Plugin Development Guide

Synapse is built on a **hot-swappable plugin architecture**. This guide will teach you how to create your own agentic capabilities.

## 📂 Architecture

Synapse automatically scans the `app/plugins/` directory on startup. To add a new feature, you simply create a folder there.

### File Structure
Your plugin folder must look like this:

```
app/plugins/
└── my_cool_plugin/          <-- Your Plugin ID
    ├── plugin.json          <-- Manifest (Required)
    └── my_plugin_file.py    <-- Logic (Required)
```

## 📝 1. The Manifest (`plugin.json`)

This file tells the system about your plugin.

```json
{
    "id": "my_cool_plugin",
    "name": "My Cool Feature",
    "version": "1.0.0",
    "entry_point": "my_plugin_file.MyPluginClass", 
    "triggers": ["/cool", "/wow"],
    "description": "A brief description of what this does.",
    "capabilities": ["network", "filesystem"] 
}
```

*   **id**: Must match the folder name.
*   **entry_point**: Format is `filename.ClassName`.
*   **triggers**: List of commands that will wake up your plugin.

## 🧠 2. The Logic (`my_plugin_file.py`)

Create a class that inherits from `PluginBase`.

```python
from app.core.plugin_base import PluginBase

class MyPluginClass(PluginBase):
    def on_load(self):
        print("My Plugin Loaded!")
        self.running = False

    def shutdown(self):
        print("Cleaning up...")

    def execute(self, command: str, context: dict) -> str:
        # command = The text after the trigger (e.g. "/cool hello world")
        self.running = True
        try:
            return f"You said: {command}"
        finally:
            self.running = False

    def is_busy(self) -> bool:
        return self.running
    
    def heartbeat(self):
        # Used by the Dashboard
        return {"status": "idle", "message": "Waiting for command"}
```

## 🚀 Testing

1.  Restart Synapse: `./start_synapse.sh`
2.  Check the logs: You should see `Loaded Plugin: My Cool Feature`.
3.  Go to Telegram or Dashboard and type `/cool test`.

## 🤝 Submission

1.  Create a branch: `git checkout -b plugin/my_cool_plugin`
2.  Commit your folder: `git add app/plugins/my_cool_plugin`
3.  Push and PR!
