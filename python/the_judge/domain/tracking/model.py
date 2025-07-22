from __future__ import annotations  
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np

@dataclass
class Frame:
    id: str
    camera_name: str
    captured_at: datetime
    collection_id: Optional[str]

@dataclass
class Face:
    id: str
    frame_id: str
    bbox: tuple[int, int, int, int]
    embedding: np.ndarray
    normed_embedding: np.ndarray
    embedding_norm: float
    det_score: float
    quality_score: float
    pose: str
    age: int
    sex: str
    captured_at: datetime

@dataclass
class Body:
    id: str
    frame_id: str
    bbox: tuple[int, int, int, int]
    captured_at: datetime

@dataclass
class Detection:
    id: str
    frame_id: str
    face_id: Optional[str]
    body_id: Optional[str]
    visitor_record: dict
    captured_at: datetime

@dataclass
class Collection:
    id: str
    created_at: datetime

@dataclass
class Camera:
    id: str
    name: str          
    state: str
    captured_at: datetime
    created_at: datetime

@dataclass
class Visitor:
    id: str
    name: str
    state: str
    face_id: str
    body_id: str
    captured_at: datetime
    created_at: datetime

    def record(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'face_id': self.face_id,
            'body_id': self.body_id,
            'captured_at': self.captured_at,
            'created_at': self.created_at
        }

