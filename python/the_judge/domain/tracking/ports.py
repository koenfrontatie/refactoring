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

class FaceDetectorPort(ABC):
    @abstractmethod
    def detect_faces(self, image: np.ndarray, frame_id: int) -> List[Face]:
        """Detect faces in image and return Face objects with embeddings."""
        pass


class BodyDetectorPort(ABC):
    @abstractmethod
    def detect_bodies(self, image: np.ndarray, frame_id: int) -> List[Body]:
        """Detect body bounding boxes in image data."""
        pass


class FaceBodyMatcherPort(ABC):
    @abstractmethod
    def match_faces_to_bodies(self, faces: List[Face], bodies: List[Body]) -> Dict[int, int]:
        """Match faces to bodies using geometric/spatial analysis. Returns face_id -> body_id mapping."""
        pass


class FaceRecognizerPort(ABC):
    @abstractmethod
    def recognize_faces(self, faces: List[Face]) -> Dict[int, Optional[dict]]:
        """Recognize faces against known faces database. Returns face_id -> visitor_record mapping."""
        pass