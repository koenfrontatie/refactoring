from __future__ import annotations  
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np
from enum import Enum

@dataclass
class Frame:
    id: str
    camera_name: str
    captured_at: datetime
    collection_id: str

# we will eventually separate embedding from face, so we can have a max stored embeddings per visitor entity
@dataclass
class Face:
    id: str
    frame_id: str
    bbox: tuple[int, int, int, int]
    embedding: np.ndarray
    normed_embedding: np.ndarray
    embedding_norm: float
    det_score: float
    quality_score: Optional[float]
    pose: Optional[str]
    age: Optional[int]
    sex: Optional[str]
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


'''
@dataclass
class VisitorState(Enum):
    NEW = "new"
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    MISSING = "missing"

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
    def time_since_capture(self) -> timedelta:
        return datetime.now() - self.captured_at
    
    @property
    def time_since_last_seen(self) -> timedelta:
        return datetime.now() - self.last_seen
    
    @property
    def is_missing(self) -> bool:
        return self.time_since_last_seen > timedelta(minutes=5) 
    
    @property
    def should_be_promoted(self) -> bool:
        return (self.state == VisitorState.TEMPORARY and self.seen_count >= 3)  
    
    @property
    def should_be_removed(self) -> bool:
        return (self.state == VisitorState.TEMPORARY and 
                self.time_since_last_seen > timedelta(minutes=2))
    
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


'''