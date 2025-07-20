from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

from the_judge.common.datetime_utils import now

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