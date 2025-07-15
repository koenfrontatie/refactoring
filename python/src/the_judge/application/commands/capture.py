from typing import Optional
from pathlib import Path

from the_judge.common.logger import setup_logger
from the_judge.common import datetime_utils

logger = setup_logger('CaptureCommand')


class CaptureFrameCommand:
    
    def __init__(self, camera_service):
        self.camera_service = camera_service
    
    async def execute(self, filename: Optional[str] = None) -> dict:
        if not filename:
            filename = datetime_utils.now().strftime("%Y.%m.%d-%H.%M.%S.jpg")
        
        logger.info(f"Requesting frames from all cameras: {filename}")
        return await self.camera_service.request_frames_from_all(filename)
