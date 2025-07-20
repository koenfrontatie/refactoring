# src/domain/ports.py
from abc import ABC, abstractmethod
from typing import List, Protocol
from the_judge.domain.tracking.model import Frame, Face

class FrameCollectorPort(ABC):

    @abstractmethod
    def register_camera(self, command):
        pass

    @abstractmethod
    def unregister_camera(self, command):
        pass

    @abstractmethod
    def ingest_frame(self, command):
        pass

class FaceAnalysisPort(ABC):
    @abstractmethod
    def get_faces(self, frame_id: int) -> set[Face]:
        """Retrieve all faces detected in a specific frame."""
        pass