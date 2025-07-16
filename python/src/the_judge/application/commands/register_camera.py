# application/commands/register_camera.py
from the_judge.application.services.camera_service import CameraService

class RegisterCameraCommand:
    def __init__(self, service: CameraService):
        self.service = service

    async def execute(self, camera_id: str):
        await self.service.register(camera_id)
