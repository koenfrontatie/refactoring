"""
USB Camera hardware adapter.
"""

import cv2
import asyncio
from pathlib import Path
from typing import Optional

from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.entities import Camera
from the_judge.infrastructure.hardware.base import CameraAdapter

logger = setup_logger('USBCameraAdapter')


class USBCameraAdapter(CameraAdapter):
    """USB camera adapter using OpenCV."""
    
    def __init__(self, camera: Camera, device_id: int = 0, 
                 width: int = 1280, height: int = 720, stream_dir: Path = Path("stream")):
        super().__init__(camera)
        self.device_id = device_id
        self.width = width
        self.height = height
        self.stream_dir = stream_dir
        self.cv_camera: Optional[cv2.VideoCapture] = None
        
    async def initialize(self) -> bool:
        """Initialize the USB camera."""
        try:
            logger.info(f"Initializing USB camera {self.device_id}...")
            
            self.cv_camera = cv2.VideoCapture(self.device_id, cv2.CAP_DSHOW)
            if not self.cv_camera.isOpened():
                self.cv_camera = cv2.VideoCapture(self.device_id)
                
            if not self.cv_camera.isOpened():
                logger.error(f"Failed to open camera {self.device_id}")
                self.camera.mark_error()
                return False
                
            self.cv_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cv_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            ret, frame = self.cv_camera.read()
            if not ret or frame is None:
                logger.error(f"Camera {self.device_id} test capture failed")
                self.camera.mark_error()
                return False
                
            actual_width = int(self.cv_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cv_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"Camera {self.device_id} initialized: {actual_width}x{actual_height}")
            self.camera.activate()
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera {self.device_id}: {e}")
            self.camera.mark_error()
            return False
    
    async def capture_frame(self, filename: str) -> Optional[Path]:
        """Capture a frame and save to file."""
        if not self.cv_camera or not self.cv_camera.isOpened():
            logger.error("Camera not initialized")
            return None
            
        try:
            ret, frame = self.cv_camera.read()
            if not ret or frame is None:
                logger.error("Failed to capture frame")
                self.camera.mark_error()
                return None
            
            self.stream_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = self.stream_dir / filename
            success = cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            if success and filepath.exists():
                logger.info(f"Captured frame: {filename}")
                self.camera.update_activity()
                return filepath
            else:
                logger.error(f"Failed to save frame: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            self.camera.mark_error()
            return None
    
    def shutdown(self):
        """Clean shutdown."""
        if self.cv_camera:
            self.cv_camera.release()
            self.cv_camera = None
            logger.info(f"Camera {self.device_id} released")
        self.camera.deactivate()
