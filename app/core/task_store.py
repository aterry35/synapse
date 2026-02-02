import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./synapse.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    command_text = Column(String)
    trigger_used = Column(String)
    plugin_id = Column(String)
    status = Column(String, default="QUEUED") # QUEUED|RUNNING|DONE|FAILED
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    error_message = Column(Text, nullable=True)
    result_message = Column(Text, nullable=True)

class PluginState(Base):
    __tablename__ = "plugin_state"
    
    plugin_id = Column(String, primary_key=True)
    last_heartbeat_at = Column(DateTime)
    last_status = Column(String)
    last_message = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
