"""
Camera hardware adapters base classes.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from the_judge.domain.tracking.entities import Camera


class CameraAdapter(ABC):
    """Abstract base for camera adapters."""
    
    def __init__(self, camera: Camera):
        self.camera = camera
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the camera."""
        pass
    
    @abstractmethod
    async def capture_frame(self, filename: str) -> Optional[Path]:
        """Capture a single frame and save to file."""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Clean shutdown."""
        pass
