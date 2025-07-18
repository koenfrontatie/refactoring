# src/domain/model.py
from __future__ import annotations  
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from attr import asdict

@dataclass(frozen=True)
class Frame:
    id: int
    camera: Camera
    captured_at: datetime
    uuid: str

@dataclass(frozen=True)
class Detection:
    id: int
    frame: Frame
    visitor_record: dict
    captured_at: datetime
    uuid: str

@dataclass(frozen=True)
class Collection:
    id: int
    created_at: datetime
    frames: set[Frame]  
    uuid: str

@dataclass(frozen=True)
class Face:
    id: int
    frame: Frame
    bbox: tuple[int, int, int, int] # (x1, y1, x2, y2)
    embedding: np.ndarray
    normed_embedding: np.ndarray
    embedding_norm: float
    det_score: float
    quality_score: float
    pose: str
    age: int
    sex: str
    captured_at: datetime   
    uuid: str

@dataclass(frozen=True)
class Body:
    id: int
    frame: Frame
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    captured_at: datetime
    uuid: str

# ---- Entities ----

@dataclass
class Camera:
    id: int           
    state: str
    captured_at: datetime
    created_at: datetime
    uuid: str

@dataclass
class Visitor:
    id: int
    name: str
    state: str
    face: Face
    body: Body
    captured_at: datetime
    created_at: datetime
    uuid: str

    def record(self) -> dict:
        return asdict(self)

