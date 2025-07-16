from the_judge.application.commands import register_camera
from the_judge.application.dtos import CameraFrameDTO, CaptureRequestDTO, CameraRegistrationDTO
from typing import Enum

class CameraEvent(str, Enum):
    CAPTURE_FRAMES = "camera.capture_frames"
    REGISTER = "camera.register"
    UNREGISTER = "camera.unregister"
    FRAME = "camera.frame"

def register(sio, camera_service):
    @sio.on(CameraEvent.REGISTER)
    async def handle_camera_register(data):
        name = data.get('name')
        if not name:
            return
            
        registration_dto = CameraRegistrationDTO(name=name)
        await register_camera(registration_dto)
    
    @sio.on(CameraEvent.CAPTURE_FRAMES)
    async def handle_capture_frames(data):
        filename = data.get('filename', '')
        await camera_service.capture_frames_from_all(filename)

    @sio.on(CameraEvent.FRAME)
    async def handle_camera_frame(data):
        camera_id = data.get('camera_id')
        filename = data.get('filename')
        frame_data = data.get('frame_data')
        
        if not all([camera_id, filename, frame_data]):
            return
            
        dto = CameraFrameDTO(
            camera_id=camera_id,
            filename=filename,
            frame_data=frame_data
        )
        await camera_service.ingest_frame(dto)
