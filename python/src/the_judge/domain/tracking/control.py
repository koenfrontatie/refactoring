from enum import Enum

class Camera(str, Enum):
    """Allowed commands for a camera device."""

    CAPTURE_FRAMES = "capture_frames"
    REGISTER_CAMERA = "register_camera"
    UNREGISTER_CAMERA = "unregister_camera"
