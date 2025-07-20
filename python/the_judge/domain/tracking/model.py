# domain/tracking/model.py
from datetime import datetime
import numpy as np
from pydantic import BaseModel
from typing import Optional

class Frame(BaseModel):
    """Frame value object."""
    camera_name: str
    captured_at: datetime
    uuid: str
    collection_id: Optional[int] = None
    id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

class Face(BaseModel):
    """Face value object."""
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

    class Config:
        arbitrary_types_allowed = True

class Body(BaseModel):
    """Body value object."""
    frame: Frame
    bbox: tuple
    captured_at: datetime
    uuid: str
    id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

class Detection(BaseModel):
    """Detection value object."""
    frame: Frame
    visitor_record: dict
    captured_at: datetime
    uuid: str
    id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

class Collection(BaseModel):
    """Collection value object."""
    created_at: datetime
    uuid: str
    id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

# ====== Entities ======

class Camera(BaseModel):
    """Camera entity."""
    name: str
    state: str
    captured_at: datetime
    created_at: datetime
    uuid: str
    id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

class Visitor(BaseModel):
    """Visitor entity."""
    name: str
    state: str
    face: Face
    body: Body
    captured_at: datetime
    created_at: datetime
    uuid: str
    id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

    def record(self) -> dict:
        """Return visitor data as dictionary for detection snapshots."""
        visitor_record = VisitorRecord(
            id=self.id,
            name=self.name,
            state=self.state,
            face_id=self.face.id if self.face else None,
            body_id=self.body.id if self.body else None,
            captured_at=self.captured_at,
            created_at=self.created_at,
            uuid=self.uuid
        )
        return visitor_record.dict()

class VisitorRecord(BaseModel):
    """Pydantic model for visitor serialization."""
    id: Optional[int] = None
    name: str
    state: str
    face_id: Optional[int] = None
    body_id: Optional[int] = None
    captured_at: datetime
    created_at: datetime
    uuid: str

    class Config:
        arbitrary_types_allowed = True
