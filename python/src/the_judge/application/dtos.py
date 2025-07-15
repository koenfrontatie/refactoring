# application/dtos.py
from dataclasses import dataclass
from typing import Optional

@dataclass(slots=True, frozen=True)
class CaptureFrameDTO:
    camera_id: str | None = None      # None = broadcast to all
    filename: Optional[str] = None
