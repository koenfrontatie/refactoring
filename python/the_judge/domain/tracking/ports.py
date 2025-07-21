from abc import ABC, abstractmethod
from typing import List, Protocol, Dict, Optional
import numpy as np
from the_judge.domain.tracking.model import Frame, Face, Body

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


class FaceDetectionPort(ABC):
    @abstractmethod
    def detect_faces(self, image: np.ndarray, frame_id: int) -> List[Face]:
        """Detect faces in image and return Face objects with embeddings."""
        pass


class BodyDetectionPort(ABC):
    @abstractmethod
    def detect_bodies(self, image: np.ndarray, frame_id: int) -> List[Body]:
        """Detect body bounding boxes in image data."""
        pass


class FaceBodyMatchingPort(ABC):
    @abstractmethod
    def match_faces_to_bodies(self, faces: List[Face], bodies: List[Body]) -> Dict[int, int]:
        """Match faces to bodies using geometric/spatial analysis. Returns face_id -> body_id mapping."""
        pass