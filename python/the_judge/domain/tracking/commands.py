from pydantic import BaseModel
from common import datetime_utils
from typing import Optional
from dataclasses import dataclass

class StartCollectionCommand(BaseModel):
    collection_id: str

class IngestFrameCommand(BaseModel):
    camera_name: str
    collection_id: str
    frame_data: bytes

class RegisterCameraCommand(BaseModel):
    camera_name: str

class UnregisterCameraCommand(BaseModel):
    camera_name: str