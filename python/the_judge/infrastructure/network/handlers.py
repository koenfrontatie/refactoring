from application import CameraService
from application.dtos import CaptureResponseDTO, CollectionRequestDTO, CameraRegistrationDTO
from enum import Enum
from common import datetime_utils

class Event(str, Enum):
    TRIGGER_COLLECTION = "camera.trigger_collection"
    COLLECT_FRAME = "camera.collect_frame"
    REGISTER = "camera.register"
    UNREGISTER = "camera.unregister"
    FRAME = "camera.frame"

def register(sio, camera_service: CameraService):
    @sio.on(Event.REGISTER)
    async def handle_camera_register(data):
        camera = data.get('camera')
        if not camera:
            return

        registration_dto = CameraRegistrationDTO(camera=camera)
        await camera_service.register_camera(registration_dto)
    
    @sio.on(Event.TRIGGER_COLLECTION)
    async def handle_trigger_collection():
        collection_dto = CollectionRequestDTO(collection_id=datetime_utils.now().strftime("%Y%m%d%H%M%S"))
        sio.emit(collection_dto.collection_id)
        pass

    @sio.on(Event.FRAME)
    async def handle_camera_frame(data):
        id = data.get('id')
        camera = data.get('camera')
        b64 = data.get('b64')
        
        if not all([id, camera, b64]):
            return
            
        dto = CaptureResponseDTO(
            id=id,
            camera=camera,
            b64=b64
        )
        await camera_service.ingest_frame(dto)
