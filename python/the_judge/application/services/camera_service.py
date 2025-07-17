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
        
        try:
            if dto.b64.startswith('data:image/'):
                dto.b64 = dto.b64.split(',')[1]
                
            frame_bytes = base64.b64decode(dto.b64)
        except Exception as e:
            logger.error(f"Failed to decode frame data from {dto.camera}: {e}")
            return
            
        camera_dir = self.cfg.get_stream_path(dto.camera)
        filepath = f"{camera_dir}/{dto.collection_id}.jpg"
        
        with open(filepath, 'wb') as f:
            f.write(frame_bytes)
            
        logger.debug(f"Saved frame from {dto.camera}")


    async def register_camera(self, dto: CameraRegistrationDTO):
        if dto.action != "register":
            self._cameras.remove(dto.camera)
            logger.info(f"Unregistered camera {dto.camera}")
            return
        
        self._cameras.add(dto.camera)
        logger.info(f"Registered camera {dto.camera}")


