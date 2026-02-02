from fastapi import FastAPI, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.config_manager import ConfigManager
from app.core.plugin_manager import PluginManager
from app.core.orchestrator import Orchestrator
from app.core.task_store import init_db, SessionLocal, TaskLog
from pydantic import BaseModel
from typing import List

# Load Config
from dotenv import load_dotenv
load_dotenv()
ConfigManager.load()

# Init DB
init_db()

# Load Plugins
pm = PluginManager.get_instance()
pm.load_plugins()

app = FastAPI()

# Mount Static
app.mount("/web", StaticFiles(directory="web", html=True), name="web")

@app.get("/")
async def root():
    return RedirectResponse(url="/web/")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CommandReq(BaseModel):
    text: str

@app.post("/api/command")
def send_command(req: CommandReq, bg: BackgroundTasks):
    orc = Orchestrator.get_instance()
    # Synchronous Create
    task_id = orc.create_task(req.text)
    # Async Execute
    bg.add_task(orc.handle_command, task_id)
    return {"status": "Queued", "task_id": task_id}
    
@app.get("/api/task/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskLog).filter(TaskLog.id == task_id).first()
    if not task:
        return {"status": "NOT_FOUND"}
    return {
        "id": task.id,
        "status": task.status,
        "result": task.result_message,
        "error": task.error_message
    }

@app.post("/api/stop")
def stop_command():
    orc = Orchestrator.get_instance()
    msg = orc.abort_active_task()
    return {"status": msg}

@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    return db.query(TaskLog).order_by(TaskLog.id.desc()).limit(10).all()

@app.get("/api/plugins")
def list_plugins():
    pm = PluginManager.get_instance()
    res = []
    for pid, p in pm.plugins.items():
        # Get manifest info
        m = pm.manifests.get(pid, {})
        # Get realtime status
        hb = p.heartbeat()
        res.append({
            "id": pid,
            "name": m.get("name"),
            "status": hb.get("status"),
            "progress": hb.get("progress"),
            "message": hb.get("message")
        })
    return res

if __name__ == "__main__":
    import uvicorn
    cfg = ConfigManager.get_server_config()
    host = cfg.get("bind_host", "127.0.0.1")
    port = cfg.get("port", 8000)
    uvicorn.run(app, host=host, port=port)
