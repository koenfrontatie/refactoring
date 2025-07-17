from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any


class CameraCmd(str, Enum):
    """Commands for controlling camera operation."""
    CAPTURE = "capture"  # Take a single frame
    TOGGLE = "toggle"    # Toggle continuous capture on/off
    STATUS = "status"    # Request camera status information


@dataclass(frozen=True)
class CaptureCmd:
    """Command to capture a single frame from camera."""
    camera_id: str
    
    
@dataclass(frozen=True)
class ToggleCaptureCmd:
    """Command to toggle continuous capture mode."""
    camera_id: str
    enabled: Optional[bool] = None  # If None, will toggle current state
    

@dataclass(frozen=True)
class GetCameraStatusCmd:
    """Command to retrieve the status of a camera."""
    camera_id: str
