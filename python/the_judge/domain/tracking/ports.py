# src/domain/ports.py
from abc import ABC, abstractmethod
from typing import List, Protocol
from tracking.model import Frame

class FrameCollectorPort(ABC):
    @abstractmethod
    def collect_frames(self, camera_id: str) -> set[Frame]:
        pass