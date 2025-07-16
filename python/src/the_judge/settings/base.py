"""
Application Settings
Configuration management using Pydantic settings.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # App basics
    app_name: str = "The Judge"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Network
    socket_url: str = Field(default="ws://localhost:8081", env="SOCKET_URL")
    
    # Camera settings
    camera_device_id: int = Field(default=0, env="CAMERA_DEVICE_ID")
    camera_width: int = Field(default=1280, env="CAMERA_WIDTH")
    camera_height: int = Field(default=720, env="CAMERA_HEIGHT")
    capture_interval: float = Field(default=10.0, env="CAPTURE_INTERVAL")
    
    # Storage paths
    storage_dir: Path = Field(default=Path("storage"), env="STORAGE_DIR")
    stream_dir: Path = Field(default=Path("storage/stream"), env="STREAM_DIR")
    
    # Database
    database_url: str = Field(default="sqlite:///storage/tracking.db", env="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def get_stream_path(self, filename: str) -> Path:
        """Get full path for a stream file."""
        return self.stream_dir / filename


# Cached settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        
        # Ensure directories exist
        _settings.storage_dir.mkdir(parents=True, exist_ok=True)
        _settings.stream_dir.mkdir(parents=True, exist_ok=True)
        
    return _settings
