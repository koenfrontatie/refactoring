from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional, Type, Tuple
import numpy as np
from the_judge.domain.tracking.model import Frame, Face, FaceEmbedding, Body, FaceComposite


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
    def detect_faces(self, image: np.ndarray, frame_id: str) -> List[FaceComposite]:
        """Detect faces in image and return Composite objects."""
        pass

class BodyDetectorPort(ABC):
    @abstractmethod
    def detect_bodies(self, image: np.ndarray, frame_id: str) -> List[Body]:
        """Detect body bounding boxes in image data."""
        pass

class FaceBodyMatcherPort(ABC):
    @abstractmethod
    def match_faces_to_bodies(self, faces: List[FaceComposite], bodies: List[Body]) -> List[FaceComposite]:
        """Match faces to bodies using geometric/spatial analysis. Returns face_id -> body_id mapping."""
        pass

class FaceRecognizerPort(ABC):
    @abstractmethod
    def recognize_faces(self, faces: List[FaceComposite]) -> List[str]:
        """Recognize faces against known embeddings in database. Returns list of visitor id or none."""
        pass


class FaceMLProvider(ABC):
    def get_face_detector(self) -> FaceDetectorPort:
        pass
    def get_face_recognizer(self) -> FaceRecognizerPort:
        pass

class BodyMLProvider(ABC):
    def get_body_detector(self) -> BodyDetectorPort:
        pass