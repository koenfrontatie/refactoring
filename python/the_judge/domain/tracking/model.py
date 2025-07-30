from __future__ import annotations  
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from the_judge.common import datetime_utils
from typing import Optional, List, Set
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
    last_seen: datetime
    created_at: datetime
    current_session: Optional[VisitorSession] = None
    events: List = field(default_factory=list, init=False)

    @classmethod
    def create_new(cls, name: str) -> Visitor:
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            state=VisitorState.TEMPORARY,
            seen_count=0,
            frame_count=0,
            last_seen=datetime_utils.now(),
            created_at=datetime_utils.now()
        )

    def start_session(self, frame_id: str) -> None:
        if self.current_session and self.current_session.is_active:
            raise ValueError("Cannot start new session while another is active")
        
        session_id = str(uuid.uuid4())
        self.current_session = VisitorSession(
            id=session_id,
            visitor_id=self.id,
            start_frame_id=frame_id,
            started_at=datetime_utils.now()
        )
        
        from .events import SessionStarted
        self.events.append(SessionStarted(
            visitor_id=self.id,
            session_id=session_id,
            frame_id=frame_id
        ))

    def record_detection(self, collection_id: str, frame_id: str, is_new_collection: bool) -> dict:
        current_time = datetime_utils.now()
        
        self.last_seen = current_time
        self.frame_count += 1
        
        if is_new_collection:
            self.seen_count += 1
        
        if not self.current_session or not self.current_session.is_active:
            self.start_session(frame_id)
        else:
            self.current_session.add_frame()
        
        self._check_promotion()
        
        return self.record()

    def update_state(self, current_time: datetime) -> None:
        old_state = self.state
        time_since_last_seen = current_time - self.last_seen
        
        if self._should_be_missing(time_since_last_seen):
            self._transition_to_missing()
        elif self._should_be_returning(current_time, time_since_last_seen):
            self._transition_to_returning()
        elif self.state == VisitorState.RETURNING:
            self._transition_to_active()
        
        if old_state != VisitorState.MISSING and self.state == VisitorState.MISSING:
            self._end_current_session("timeout", current_time)

    def expire(self) -> None:
        if self.current_session and self.current_session.is_active:
            self._end_current_session("expired", datetime_utils.now())
        
        from .events import VisitorExpired
        self.events.append(VisitorExpired(visitor_id=self.id))

    @property
    def should_be_removed(self) -> bool:
        return (self.state == VisitorState.TEMPORARY and 
                (datetime_utils.now() - self.last_seen) > timedelta(minutes=1))

    @property
    def time_since_creation(self) -> timedelta:
        return datetime_utils.now() - self.created_at
    
    @property
    def time_since_last_seen(self) -> timedelta:
        return datetime_utils.now() - self.last_seen

    @property
    def current_session_id(self) -> Optional[str]:
        return self.current_session.id if self.current_session else None

    @property
    def session_started_at(self) -> Optional[datetime]:
        return self.current_session.started_at if self.current_session else None

    def _check_promotion(self) -> None:
        if self.state == VisitorState.TEMPORARY and self.seen_count >= 3:
            self.state = VisitorState.ACTIVE
            from .events import VisitorPromoted
            self.events.append(VisitorPromoted(visitor_id=self.id))

    def _should_be_missing(self, time_since_last_seen: timedelta) -> bool:
        return time_since_last_seen > timedelta(minutes=1)

    def _should_be_returning(self, current_time: datetime, time_since_last_seen: timedelta) -> bool:
        if not self.current_session:
            return False
        
        within_returning_window = (current_time - self.current_session.started_at) <= timedelta(seconds=30)
        not_too_long_missing = time_since_last_seen <= timedelta(minutes=1)
        
        return (self.state in [VisitorState.MISSING, VisitorState.RETURNING] and 
                within_returning_window and not_too_long_missing)

    def _transition_to_missing(self) -> None:
        if self.state != VisitorState.MISSING:
            self.state = VisitorState.MISSING
            from .events import VisitorWentMissing
            self.events.append(VisitorWentMissing(visitor_id=self.id))

    def _transition_to_returning(self) -> None:
        if self.state != VisitorState.RETURNING:
            self.state = VisitorState.RETURNING
            from .events import VisitorReturned
            self.events.append(VisitorReturned(visitor_id=self.id))

    def _transition_to_active(self) -> None:
        self.state = VisitorState.ACTIVE

    def _end_current_session(self, reason: str, ended_at: datetime) -> None:
        if self.current_session and self.current_session.is_active:
            self.current_session.end("unknown", ended_at)
            from .events import SessionEnded
            self.events.append(SessionEnded(
                visitor_id=self.id,
                session_id=self.current_session.id,
                reason=reason
            ))

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
    started_at: datetime
    frame_count: int = 1
    end_frame_id: Optional[str] = None
    ended_at: Optional[datetime] = None

    def add_frame(self) -> None:
        self.frame_count += 1

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


@dataclass
class DetectionFrame:
    """ DetectionFrame Aggregate Root - Groups all detections for a single frame """
    id: str
    collection_id: str
    camera_name: str
    captured_at: datetime
    detections: List[Detection] = field(default_factory=list)
    events: List = field(default_factory=list, init=False)

    def add_detection(self, face_id: str, embedding_id: str, visitor_id: str, 
                     visitor_record: dict, body_id: Optional[str] = None) -> Detection:
        detection = Detection(
            id=str(uuid.uuid4()),
            frame_id=self.id,
            face_id=face_id,
            embedding_id=embedding_id,
            visitor_id=visitor_id,
            visitor_record=visitor_record,
            captured_at=datetime_utils.now(),
            body_id=body_id
        )
        self.detections.append(detection)
        return detection

    def get_visitor_ids(self) -> Set[str]:
        return {detection.visitor_id for detection in self.detections}

    def has_visitor(self, visitor_id: str) -> bool:
        return visitor_id in self.get_visitor_ids()


