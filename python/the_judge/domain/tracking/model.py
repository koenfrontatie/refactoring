from __future__ import annotations  
from dataclasses import dataclass
from datetime import datetime, timedelta
from the_judge.common import datetime_utils
from typing import Optional
import numpy as np
from enum import Enum

@dataclass
class Frame:
    id: str
    camera_name: str
    captured_at: datetime
    collection_id: str

@dataclass
class Face:
    id: str
    frame_id: str
    bbox: tuple[int, int, int, int]
    embedding_id: str
    embedding_norm: float
    det_score: float
    quality_score: Optional[float]
    pose: Optional[str]
    age: Optional[int]
    sex: Optional[str]
    captured_at: datetime

@dataclass
class FaceEmbedding:
    id: str
    embedding: np.ndarray
    normed_embedding: np.ndarray

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
    face_id: str
    embedding_id: str
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
class Composite:
    face: Face
    embedding: FaceEmbedding
    body: Optional[Body] = None
    visitor: Optional[Visitor] = None

@dataclass
class VisitorState(Enum):
    TEMPORARY = "temporary"
    ACTIVE = "active"
    MISSING = "missing"
    RETURNING = "returning"

@dataclass
class Visitor:
    id: str
    name: str
    state: VisitorState
    face_id: str
    body_id: str
    seen_count: int = 0
    captured_at: datetime
    created_at: datetime
    

    @property
    def time_since_creation(self) -> timedelta:
        return datetime_utils.now() - self.created_at
    
    @property
    def time_since_last_seen(self) -> timedelta:
        return datetime_utils.now() - self.captured_at

    @property
    def is_missing(self) -> bool:
        return self.time_since_last_seen > timedelta(minutes=1) 
    
    @property
    def should_be_promoted(self) -> bool:
        return (self.state == VisitorState.TEMPORARY and self.seen_count >= 3)  
    
    @property
    def should_be_removed(self) -> bool:
        return (self.state == VisitorState.TEMPORARY and 
                self.time_since_last_seen > timedelta(minutes=1))
    
    def record(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'face_id': self.face_id,
            'body_id': self.body_id,
            'seen_count': self.seen_count,
            'captured_at': self.captured_at,
            'created_at': self.created_at
        }


