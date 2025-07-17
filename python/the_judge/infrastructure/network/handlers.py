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
    async def handle_camera_register(payload):
        camera = payload.get('camera')
        if not camera:
            return

        registration_dto = CameraRegistrationDTO(camera=camera)
        await camera_service.register_camera(registration_dto)
    
    @sio.on(Event.TRIGGER_COLLECTION)
    async def handle_trigger_collection(payload):
        collection_dto = CollectionRequestDTO(collection_id=datetime_utils.now().strftime("%Y%m%d%H%M%S"))
        await sio.emit(Event.COLLECT_FRAME, collection_dto.model_dump())
        pass

    @sio.on(Event.FRAME)
    async def handle_camera_frame(payload):
        collection_id = payload.get('collection_id')
        camera = payload.get('camera')
        b64 = payload.get('b64')
        
        if not all([collection_id, camera, b64]):
            return
            
        dto = CaptureResponseDTO(
            collection_id=collection_id,
            camera=camera,
            b64=b64
        )
        await camera_service.ingest_frame(dto)
