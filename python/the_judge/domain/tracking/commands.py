from pydantic import BaseModel

class StartCollectionCommand(BaseModel):
    collection_id: str

class SaveFrameCommand(BaseModel):
    camera_name: str
    collection_id: str
    frame_data: bytes

class RegisterCameraCommand(BaseModel):
    camera_name: str

class UnregisterCameraCommand(BaseModel):
    camera_name: str

class ProcessFrameCommand(BaseModel):
    frame_id: int