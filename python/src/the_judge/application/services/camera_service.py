# application/services/camera_service.py
from typing import List

from the_judge.infrastructure.hardware.base import CameraAdapter
from the_judge.application.dtos import CaptureRequestDTO, CameraRegistrationDTO
from the_judge.application.commands import CaptureFramesCommand

class CameraService:
    def __init__(self, usb_cameras, socket_client, registry):
        self.cameras = []
        self._capture_cmd = CaptureFramesCommand(
            usb_cameras, socket_client, registry
        )

    async def capture_frames(self, dto):
        return await self._capture_cmd.execute(dto)

    async def register_camera(self, dto: CameraRegistrationDTO):
        # Register the camera using the provided DTO
        pass

    def shutdown(self):
        for c in self.usb_cameras:
            c.shutdown()
