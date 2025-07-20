from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import numpy as np

@dataclass
class Frame:
    camera_name: str
    captured_at: datetime
    uuid: str
    collection_id: Optional[int] = None
    id: Optional[int] = None

@dataclass
class Face:
    frame: Frame
    bbox: tuple
    embedding: np.ndarray
    normed_embedding: np.ndarray
    embedding_norm: float
    det_score: float
    captured_at: datetime
    uuid: str
    quality_score: Optional[float] = None
    pose: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    id: Optional[int] = None

@dataclass
class Body:
    frame: Frame
    bbox: tuple
    captured_at: datetime
    uuid: str
    id: Optional[int] = None

@dataclass
class Detection:
    frame: Frame
    visitor_record: dict
    captured_at: datetime
    uuid: str
    id: Optional[int] = None

@dataclass
class Collection:
    created_at: datetime
    uuid: str
    id: Optional[int] = None

@dataclass
class Camera:
    name: str
    state: str
    captured_at: datetime
    created_at: datetime
    uuid: str
    id: Optional[int] = None

@dataclass
class Visitor:
    name: str
    state: str
    face: Face
    body: Body
    captured_at: datetime
    created_at: datetime
    uuid: str
    id: Optional[int] = None

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
