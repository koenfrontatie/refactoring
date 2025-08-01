from __future__ import annotations  
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from the_judge.common import datetime_utils
from typing import Optional, List, Set, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    pass
import numpy as np
from enum import Enum
import uuid

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
    id: str
    name: str
    state: VisitorState
    seen_count: int
    frame_count: int
    last_seen: datetime
    created_at: datetime
    current_session_id: Optional[str] = None  
    events: List = field(default_factory=list, init=False, compare=False)

    @classmethod
    def create_new(cls, name: str) -> Visitor:
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            state=VisitorState.TEMPORARY,
            seen_count=0,
            frame_count=0,
            last_seen=datetime_utils.now(),
            created_at=datetime_utils.now(),
            current_session_id=None
        )

    def process_detection(self, frame_id: str, is_new_in_collection: bool) -> Optional[VisitorSession]:
        self.last_seen = datetime_utils.now()
        self.frame_count += 1
        
        if is_new_in_collection:
            self.seen_count += 1
            self._check_promotion()
        
        if self.state == VisitorState.RETURNING:
            self._end_current_session("visitor_returned")
            return self._start_new_session(frame_id)
        elif not self.current_session_id:
            return self._start_new_session(frame_id)
        else:
            return None

    def update_state(self, current_time: datetime) -> bool:
        time_since_last_seen = current_time - self.last_seen
        old_state = self.state
        
        if time_since_last_seen > timedelta(minutes=1):
            if self.state != VisitorState.MISSING:
                self._become_missing(current_time)
        elif self.state == VisitorState.MISSING:
            self._become_returning(current_time)
        elif self.state == VisitorState.RETURNING:
            if (current_time - self.last_seen) > timedelta(seconds=30):
                self.state = VisitorState.ACTIVE
        
        return self.state != old_state

    def expire(self) -> None:
        from .events import VisitorExpired
        self.events.append(VisitorExpired(visitor_id=self.id))

    @property
    def should_be_removed(self) -> bool:
        return (self.state == VisitorState.TEMPORARY and 
                (datetime_utils.now() - self.last_seen) > timedelta(minutes=1))

    @property
    def has_active_session(self) -> bool:
        return self.current_session_id is not None

    def end_current_session(self, reason: str) -> Optional[str]:
        if self.current_session_id:
            session_id = self.current_session_id
            self._end_current_session(reason)
            return session_id
        return None

    def _start_new_session(self, frame_id: str) -> VisitorSession:
        from .events import SessionStarted
        
        session_id = str(uuid.uuid4())
        new_session = VisitorSession(
            id=session_id,
            visitor_id=self.id,
            start_frame_id=frame_id,
            started_at=datetime_utils.now(),
            captured_at=datetime_utils.now()
        )
        
        self.current_session_id = session_id
        self.events.append(SessionStarted(
            visitor_id=self.id,
            session_id=session_id,
            frame_id=frame_id
        ))
        
        return new_session

    def _end_current_session(self, reason: str) -> None:
        from .events import SessionEnded
        
        if self.current_session_id:
            self.events.append(SessionEnded(
                visitor_id=self.id,
                session_id=self.current_session_id,
                reason=reason
            ))
        
        self.current_session_id = None

    def _check_promotion(self) -> None:
        if self.state == VisitorState.TEMPORARY and self.seen_count >= 3:
            self.state = VisitorState.ACTIVE
            from .events import VisitorPromoted
            self.events.append(VisitorPromoted(visitor_id=self.id))

    def _become_missing(self, current_time: datetime) -> None:
        self.state = VisitorState.MISSING
        from .events import VisitorWentMissing
        self.events.append(VisitorWentMissing(visitor_id=self.id))

    def _become_returning(self, current_time: datetime) -> None:
        self.state = VisitorState.RETURNING
        from .events import VisitorReturned
        self.events.append(VisitorReturned(visitor_id=self.id))

    def record(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state.value, 
            'seen_count': self.seen_count,
            'frame_count': self.frame_count,
            'current_session_id': self.current_session_id,
            'last_seen': datetime_utils.to_formatted_string(self.last_seen),
            'created_at': datetime_utils.to_formatted_string(self.created_at)
        }


@dataclass
class VisitorSession:
    id: str
    visitor_id: str
    start_frame_id: str
    started_at: datetime
    captured_at: datetime
    frame_count: int = 1
    end_frame_id: Optional[str] = None
    ended_at: Optional[datetime] = None

    def add_frame(self) -> None:
        self.frame_count += 1
        self.captured_at = datetime_utils.now()

    def end(self, end_frame_id: str, ended_at: datetime) -> None:
        self.end_frame_id = end_frame_id
        self.ended_at = ended_at

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def duration(self) -> Optional[timedelta]:
        if self.ended_at:
            return self.ended_at - self.started_at
        return None

