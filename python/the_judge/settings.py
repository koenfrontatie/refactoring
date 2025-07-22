from pathlib import Path
from typing import Optional
from pydantic import Field, BaseModel

class Settings(BaseModel):    
    # App basics
    app_name: str = "The Judge"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Network
    socket_url: str = Field(default="ws://localhost:8081", env="SOCKET_URL")
    
    # Camera settings
    capture_interval: float = Field(default=10.0, env="CAPTURE_INTERVAL")
    
    # Detection settings
    face_detection_threshold: float = Field(default=0.6, env="FACE_DETECTION_THRESHOLD")
    face_recognition_threshold: float = Field(default=0.4, env="FACE_RECOGNITION_THRESHOLD")
    model_path: Path = Field(default_factory=lambda: Path(__file__).parent / "infrastructure" / "models", env="MODEL_PATH")
    
    # Storage paths
    storage_dir: Path = Field(default=Path("storage"), env="STORAGE_DIR")
    stream_dir: Path = Field(default=Path("storage/stream"), env="STREAM_DIR")
    database_url: str = Field(default="sqlite:///storage/db/tracking.db", env="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def get_stream_path(self, filename: str) -> Path:
        return self.stream_dir / filename
        
    def get_tracking_db(self, filename: str) -> Path:
        return self.database_url

# Cached settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
