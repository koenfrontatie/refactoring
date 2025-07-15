from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple
from enum import Enum
import uuid

_now = lambda: datetime.now(tz=timezone.utc)


class CameraState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    CAPTURING = "capturing"
    ERROR = "error"


class VisitorState(str, Enum):
    TEMPORARY = "temporary"
    ACTIVE = "active"  
    MISSING = "missing"
    GONE = "gone"


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    
    @property
    def x2(self) -> float:
        return self.x + self.width
    
    @property
    def y2(self) -> float:
        return self.y + self.height
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.x2, self.y2)


@dataclass(frozen=True)
class FaceMetrics:
    det_score: float
    quality_score: Optional[float] = None
    embedding_norm: Optional[float] = None
    pose: Optional[Tuple[float, float, float]] = None
    age: Optional[float] = None
    sex: Optional[int] = None


@dataclass
class Camera:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: CameraState = CameraState.INACTIVE
    first_seen: datetime = field(default_factory=_now)
    last_seen: datetime = field(default_factory=_now)
        
    def activate(self) -> None:
        if self.state != CameraState.INACTIVE:
            raise RuntimeError(f"Cannot activate camera - current state: {self.state}")
        self.state = CameraState.ACTIVE
        self.last_seen = _now()
        
    def start_capturing(self) -> None:
        if self.state != CameraState.ACTIVE:
            raise RuntimeError(f"Cannot start capturing - current state: {self.state}")
        self.state = CameraState.CAPTURING
        self.last_seen = _now()
    
    def stop_capturing(self) -> None:
        if self.state != CameraState.CAPTURING:
            raise RuntimeError(f"Cannot stop capturing - current state: {self.state}")
        self.state = CameraState.ACTIVE
        self.last_seen = _now()
    
    def deactivate(self) -> None:
        if self.state in (CameraState.INACTIVE, CameraState.ERROR):
            return
        self.state = CameraState.INACTIVE
        self.last_seen = _now()
    
    def mark_error(self) -> None:
        self.state = CameraState.ERROR
        self.last_seen = _now()
    
    def update_activity(self) -> None:
        self.last_seen = _now()


@dataclass
class Frame:
    camera_id: str
    filename: str
    captured_at: datetime = field(default_factory=_now)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class Face:
    frame_id: str
    rect: BoundingBox
    metrics: FaceMetrics
    embedding: Optional[bytes] = None
    normed_embedding: Optional[bytes] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
        
    def set_embeddings(self, embedding: bytes, normed_embedding: bytes) -> None:
        self.embedding = embedding
        self.normed_embedding = normed_embedding


@dataclass
class Body:
    frame_id: str
    rect: BoundingBox
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class Detection:
    frame_id: str
    captured_at: datetime = field(default_factory=_now)
    visitor_id: Optional[str] = None
    visitor_state: Optional[VisitorState] = None
    face_id: Optional[str] = None
    body_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
        
    def assign_visitor(self, visitor_id: str, state: VisitorState) -> None:
        self.visitor_id = visitor_id
        self.visitor_state = state


@dataclass
class Visitor:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: VisitorState = VisitorState.TEMPORARY
    seen_count: int = 0
    first_seen: datetime = field(default_factory=_now)
    last_seen: datetime = field(default_factory=_now)
        
    def increment_seen(self) -> None:
        self.seen_count += 1
        self.last_seen = _now()
        
    def promote_to_active(self) -> None:
        if self.state != VisitorState.TEMPORARY:
            raise RuntimeError(f"Cannot promote visitor - current state: {self.state}")
        self.state = VisitorState.ACTIVE
            
    def mark_missing(self) -> None:
        if self.state == VisitorState.GONE:
            return
        self.state = VisitorState.MISSING
        
    def mark_gone(self) -> None:
        self.state = VisitorState.GONE
        
    def return_from_missing(self) -> None:
        if self.state != VisitorState.MISSING:
            raise RuntimeError(f"Cannot return visitor - current state: {self.state}")
        self.state = VisitorState.ACTIVE
        self.increment_seen()
