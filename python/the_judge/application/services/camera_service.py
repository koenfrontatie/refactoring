# application/services/camera_service.py
from typing import Set
from application.dtos import CaptureResponseDTO, CameraRegistrationDTO
from settings import get_settings
from common.logger import setup_logger

import base64

logger = setup_logger('CameraController')

class CameraService:
    def __init__(self):
        self._cameras: Set[str] = set()
        self.cfg = get_settings()

    async def ingest_frame(self, dto: CaptureResponseDTO):
        logger.info(f"Received frame from camera {dto.camera}...")
    
        if dto.camera not in self._cameras:
            logger.warning(f"Camera {dto.camera} is not registered.")
            return
            
        camera_dir = self.cfg.get_stream_path(dto.camera)
        camera_dir.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
        filepath = f"{camera_dir}/{dto.collection_id}.jpg"
        
        with open(filepath, 'wb') as f:
            f.write(dto.bytes)
            
        logger.debug(f"Saved frame from {dto.camera}")


    async def register_camera(self, dto: CameraRegistrationDTO):
        if dto.action != "register":
            self._cameras.remove(dto.camera)
            logger.info(f"Unregistered camera {dto.camera}")
            return
        
        self._cameras.add(dto.camera)
        logger.info(f"Registered camera {dto.camera}")


