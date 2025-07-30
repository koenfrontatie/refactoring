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
    seen_count: int
    frame_count: int
    current_session_id: Optional[str]
    last_seen: datetime
    created_at: datetime
    session_started_at: Optional[datetime] = None
    

    @property
    def time_since_creation(self) -> timedelta:
        return datetime_utils.now() - self.created_at
    
    @property
    def time_since_last_seen(self) -> timedelta:
        return datetime_utils.now() - self.last_seen

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
    
    def _is_within_returning_window(self, current_time: datetime) -> bool:
        return (self.session_started_at and 
                current_time - self.session_started_at <= timedelta(seconds=30))
    
    def update_state(self, current_time: datetime) -> None:
        """Update visitor state based on current time and business rules."""
        # Promotion
        if self.state == VisitorState.TEMPORARY and self.seen_count >= 3:
            self.state = VisitorState.ACTIVE
            
        # Missing check
        elif current_time - self.last_seen > timedelta(minutes=1):
            self.state = VisitorState.MISSING
            
        # Returning logic - combine conditions with OR
        elif (self.state in [VisitorState.MISSING, VisitorState.RETURNING] and
              self._is_within_returning_window(current_time) and
              current_time - self.last_seen <= timedelta(minutes=1)):
            self.state = VisitorState.RETURNING
                
        # Returning timeout
        elif self.state == VisitorState.RETURNING:
            self.state = VisitorState.ACTIVE
    
    def record(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state.value, 
            'seen_count': self.seen_count,
            'frame_count': self.frame_count,
            'current_session_id': self.current_session_id,
            'last_seen': datetime_utils.to_formatted_string(self.last_seen),
            'created_at': datetime_utils.to_formatted_string(self.created_at),
            'session_started_at': datetime_utils.to_formatted_string(self.session_started_at) if self.session_started_at else None
        }


@dataclass
class VisitorSession:
    id: str
    visitor_id: str
    start_frame_id: str
    end_frame_id: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    captured_at: datetime
    frame_count: int
    
    def end_session(self, end_frame_id: str, ended_at: datetime):
        self.end_frame_id = end_frame_id
        self.ended_at = ended_at
    
    def increment_frame_count(self):
        self.frame_count += 1
    
    @property
    def is_active(self) -> bool:
        return self.ended_at is None
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.ended_at:
            return self.ended_at - self.started_at
        return None


