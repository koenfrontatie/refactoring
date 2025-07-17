from settings import get_settings
from infrastructure.network.socket import SocketIOClient
from application.services.camera_service import CameraService

class Runtime:
    
    def __init__(self, ws_client, camera_service: CameraService):
        self.ws_client = ws_client
        self.camera_service = camera_service
    
    def shutdown(self):
        self.camera_service.shutdown_all()


def build_runtime() -> Runtime:
    settings = get_settings()
    
    camera_service = CameraService()
        
    ws_client = SocketIOClient(camera_service)
        
    return Runtime(ws_client, camera_service)
