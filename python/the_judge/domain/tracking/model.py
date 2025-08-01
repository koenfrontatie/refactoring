from __future__ import annotations  
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Set, Dict
import numpy as np
from enum import Enum
import uuid

from the_judge.domain.tracking.events import VisitorExpired, VisitorPromoted, VisitorWentMissing, VisitorReturned
from the_judge.common import datetime_utils

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
    visitor_id: str
    visitor_record: dict
    captured_at: datetime
    body_id: Optional[str] = None

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
class VisitorCollection:
    id: str
    created_at: datetime
    composites: List[Composite] = field(default_factory=list)

class VisitorState(Enum):
    TEMPORARY = "temporary"
    ACTIVE = "active"
    MISSING = "missing"
    RETURNING = "returning"

@dataclass
class Visitor:
    MISSING_AFTER = timedelta(minutes=1)
    RETURNING_WINDOW = timedelta(seconds=30)
    REMOVE_AFTER = timedelta(minutes=1)

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    state: VisitorState = VisitorState.TEMPORARY
    seen_count: int = 0
    frame_count: int = 0
    last_seen: datetime = field(default_factory=datetime_utils.now)
    created_at: datetime = field(default_factory=datetime_utils.now)
    current_session: Optional[VisitorSession] = None
    events: List = field(default_factory=list, init=False, compare=False)

    @classmethod
    def create_new(cls, name: str, current_time: datetime) -> "Visitor":
        return cls(name=name, last_seen=current_time, created_at=current_time)

    def mark_sighting(self, current_time: datetime, increment_seen: bool) -> None:
        if increment_seen:
            self.seen_count += 1
        self.frame_count += 1
        self.last_seen = current_time
        if self.current_session:
            self.current_session.increment_frame(current_time)

    def update_state(self, current_time: datetime) -> None:
        old_state = self.state

        if self._should_be_removed(current_time):
            self.events.append(VisitorExpired(visitor_id=self.id))

        elif self._should_be_promoted(current_time):
            self.state = VisitorState.ACTIVE
            if self.state != old_state:
                self.events.append(VisitorPromoted(visitor_id=self.id))

        elif self._should_go_missing(current_time):
            self.state = VisitorState.MISSING
            if self.state != old_state:
                self.events.append(VisitorWentMissing(visitor_id=self.id))

        elif self._should_be_returning(current_time):
            self.state = VisitorState.RETURNING
            if self.state != old_state:
                self.events.append(VisitorReturned(visitor_id=self.id))

        elif self._should_be_active(current_time):
            self.state = VisitorState.ACTIVE

    def create_detection(self, frame: Frame, composite: Composite) -> Detection:
        return Detection(
            id=str(uuid.uuid4()),
            frame_id=frame.id,
            face_id=composite.face.id,
            embedding_id=composite.embedding.id,
            visitor_id=self.id,
            state=self.state, #should be visitor state
            captured_at=self.last_seen,
            body_id=composite.body.id if composite.body else None   
        )
    
    def _should_be_removed(self, current_time) -> bool:
        return (self.state == VisitorState.TEMPORARY
                and (current_time - self.last_seen) > self.REMOVE_AFTER)

    def _should_go_missing(self, current_time) -> bool:
        return (self.state != VisitorState.MISSING
                and (current_time - self.last_seen) > self.MISSING_AFTER)
    
    def _should_be_returning(self, current_time) -> bool:
        return (self.state in {VisitorState.MISSING, VisitorState.RETURNING}
                and self.current_session is not None
                and (current_time - self.current_session.started_at) <= self.RETURNING_WINDOW)
    
    def _should_be_promoted(self) -> bool:
        return (self.state == VisitorState.TEMPORARY
                and self.seen_count >= 3)

    def _should_be_active(self, current_time) -> bool:
        return (self.state in {VisitorState.ACTIVE, VisitorState.RETURNING}
                and self.current_session is not None
                and (current_time - self.current_session.started_at) > self.RETURNING_WINDOW)

@dataclass
class VisitorSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    visitor_id: str = ""
    start_frame_id: str = ""
    started_at: Optional[datetime] = None
    captured_at: Optional[datetime] = None
    frame_count: int = 1
    ended_at: Optional[datetime] = None

    @classmethod
    def create_new(cls, visitor_id: str, frame: Frame) -> "VisitorSession":
        return cls(
            visitor_id=visitor_id,
            start_frame_id=frame.id,
            started_at=frame.captured_at,
            captured_at=frame.captured_at,
        )

    def increment_frame(self, captured_at: datetime) -> None:
        self.captured_at = captured_at
        self.frame_count += 1

    def end(self, ended_at: datetime) -> None:
        self.ended_at = ended_at

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def duration(self) -> Optional[timedelta]:
        if self.ended_at:
            return self.captured_at - self.started_at
        return None

