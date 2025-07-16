# application/dtos.py
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class CaptureRequestDTO:
    filename: str

@dataclass(slots=True, frozen=True)
class CameraFrameDTO:
    camera_id: str
    filename: str
    frame_data: str  # base64 encoded image data

@dataclass(slots=True, frozen=True)
class CameraRegistrationDTO:
    name: str
