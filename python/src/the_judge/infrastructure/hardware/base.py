from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from the_judge.application.dtos import CameraFrameDTO

class CameraAdapter(ABC):
    """Abstract base for camera adapters."""

    @abstractmethod
    async def capture_frame(self, filename: str) -> list[CameraFrameDTO]:
        """Capture all cameras on a device and return a list of CameraFrameDTO."""
        pass
