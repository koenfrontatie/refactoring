# application/dtos.py
from dataclasses import dataclass
from typing import Optional

@dataclass(slots=True, frozen=True)
class CaptureRequestDTO:
    filename: str | None

@dataclass(slots=True, frozen=True)
class CaptureResultDTO:
    camera_id: str
    filename: str | None
    frame_data: str          
    width: int
    height: int
