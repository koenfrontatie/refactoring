from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional, Type, Tuple
import numpy as np
from .model import Frame, Face, FaceEmbedding, Body, Composite, Visitor


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
    def detect_faces(self, image: np.ndarray, frame_id: str) -> List[Composite]:
        """Detect faces in image and return Composite objects."""
        pass

class BodyDetectorPort(ABC):
    @abstractmethod
    def detect_bodies(self, image: np.ndarray, frame_id: str) -> List[Body]:
        """Detect body bounding boxes in image data."""
        pass

class FaceBodyMatcherPort(ABC):
    @abstractmethod
    def match_faces_to_bodies(self, faces: List[Composite], bodies: List[Body]) -> List[Composite]:
        """Match faces to bodies using geometric/spatial analysis. Returns face_id -> body_id mapping."""
        pass

class FaceRecognizerPort(ABC):
    @abstractmethod
    def recognize_faces(self, faces: List[Composite]) -> List[Composite]:
        pass

    @abstractmethod
    def match_against_collection(self, composite: Composite, collection: List[Composite]) -> Optional[Visitor]:
        pass
    
    @abstractmethod
    def match_against_visitor(self, composite: Composite, visitor: Visitor) -> bool:
        pass

class FaceMLProvider(ABC):
    @abstractmethod
    def get_face_model(self):
        pass

class BodyMLProvider(ABC):
    @abstractmethod
    def get_body_model(self):
        pass