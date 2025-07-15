"""
Dependency injection container.
Wires up all application components.
"""

from typing import Protocol

from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.entities import Camera
from the_judge.infrastructure.hardware.usb_camera import USBCameraAdapter
from the_judge.infrastructure.hardware.remote_camera import RemoteCameraAdapter
from the_judge.infrastructure.network.socket import SocketIOClient
from the_judge.infrastructure.network.handlers import CameraHandlers
from the_judge.application.commands.capture import CaptureFrameCommand
from the_judge.application.services.camera_service import CameraService

logger = setup_logger('Container')


class CameraGateway(Protocol):
    async def initialize(self) -> bool: ...
    async def capture_frame(self, filename: str) -> str | None: ...
    def shutdown(self): ...


class Runtime:
    
    def __init__(self, ws_client, camera_service: CameraService):
        self.ws_client = ws_client
        self.camera_service = camera_service
    
    def shutdown(self):
        self.camera_service.shutdown_all()
        logger.info("Runtime shutdown complete")


def build_runtime() -> Runtime:
    settings = get_settings()
    
    camera_service = CameraService()
    
    usb_camera = Camera(name="USB Camera")
    usb_adapter = USBCameraAdapter(
        camera=usb_camera,
        device_id=settings.camera_device_id,
        width=settings.camera_width,
        height=settings.camera_height,
        stream_dir=settings.stream_dir
    )
    camera_service.add_usb_camera(usb_adapter)
    
    remote_camera = Camera(name="Remote Camera Manager")
    remote_adapter = RemoteCameraAdapter(
        camera=remote_camera,
        stream_dir=settings.stream_dir
    )
    camera_service.add_remote_camera(remote_adapter)
    
    ws_client = SocketIOClient("http://localhost:8081")
    
    capture_command = CaptureFrameCommand(camera_service)
    camera_handlers = CameraHandlers(capture_command)
    
    ws_client.register_handler('camera_capture', camera_handlers.handle_camera_capture)
    
    return Runtime(ws_client, camera_service)
