from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CameraRegistrationDTO(BaseModel):
    camera: str
    action: str = "register"

class CollectionRequestDTO(BaseModel):
    collection_id: str

class CaptureResponseDTO(BaseModel):
    collection_id: str
    camera: str
    bytes: bytes