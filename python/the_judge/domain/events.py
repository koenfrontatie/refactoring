from dataclasses import dataclass
from abc import ABC
from datetime import datetime

class Event(ABC):
    pass

@dataclass
class FrameIngested(Event):
    frame_id: int
    camera_name: str
    collection_id: str
    ingested_at: datetime

@dataclass
class FrameAnalyzed(Event):
    frame_id: int
    faces_detected: int
    bodies_detected: int
    analyzed_at: datetime
