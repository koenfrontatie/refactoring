from dataclasses import dataclass
from abc import ABC
from datetime import datetime

class Event(ABC):
    pass

@dataclass
class FrameSaved(Event):
    frame_id: str
    camera_name: str
    collection_id: str
    ingested_at: datetime

@dataclass
class FrameProcessed(Event):
    frame_id: str
    collection_id: str
    faces_detected: int
    bodies_detected: int
    analyzed_at: datetime
