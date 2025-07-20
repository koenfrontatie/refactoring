from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import numpy as np

@dataclass
class Frame:
    id: Optional[int] = field(default=None)
    camera_name: str = field()
    captured_at: datetime = field()
    collection_id: Optional[int] = field(default=None)
    uuid: str = field()

@dataclass
class Face:
    id: Optional[int] = field(default=None)
    frame: Frame = field()
    bbox: tuple = field()
    embedding: np.ndarray = field()
    normed_embedding: np.ndarray = field()
    embedding_norm: float = field()
    det_score: float = field()
    quality_score: Optional[float] = field(default=None)
    pose: Optional[str] = field(default=None)
    age: Optional[int] = field(default=None)
    sex: Optional[str] = field(default=None)
    captured_at: datetime = field()
    uuid: str = field()

@dataclass
class Body:
    id: Optional[int] = field(default=None)
    frame: Frame = field()
    bbox: tuple = field()
    captured_at: datetime = field()
    uuid: str = field()

@dataclass
class Detection:
    id: Optional[int] = field(default=None)
    frame: Frame = field()
    visitor_record: dict = field()
    captured_at: datetime = field()
    uuid: str = field()

@dataclass
class Collection:
    id: Optional[int] = field(default=None)
    created_at: datetime = field()
    uuid: str = field()

@dataclass
class Camera:
    id: Optional[int] = field(default=None)
    name: str = field()
    state: str = field()
    captured_at: datetime = field()
    created_at: datetime = field()
    uuid: str = field()

@dataclass
class Visitor:
    id: Optional[int] = field(default=None)
    name: str = field()
    state: str = field()
    face: Face = field()
    body: Body = field()
    captured_at: datetime = field()
    created_at: datetime = field()
    uuid: str = field()

    def record(self) -> dict:
        return dict(
            id=self.id,
            name=self.name,
            state=self.state,
            face_id=self.face.id if self.face else None,
            body_id=self.body.id if self.body else None,
            captured_at=self.captured_at,
            created_at=self.created_at,
            uuid=self.uuid
        )
