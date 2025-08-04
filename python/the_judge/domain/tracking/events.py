from dataclasses import dataclass
from abc import ABC
from typing import Optional
from the_judge.domain.tracking.model import Frame

class Event(ABC):
    pass

@dataclass
class FrameSaved(Event):
    frame: Frame

@dataclass
class FrameProcessed(Event):
    frame_id: str
    detection_count: int

@dataclass
class VisitorPromoted(Event):
    visitor_id: str

@dataclass
class VisitorWentMissing(Event):
    visitor_id: str

@dataclass
class VisitorReturned(Event):
    visitor_id: str

@dataclass
class SessionStarted(Event):
    visitor_id: str
    session_id: str
    frame_id: str

@dataclass
class SessionEnded(Event):
    visitor_id: str
    session_id: str
    reason: str

@dataclass
class VisitorExpired(Event):
    visitor_id: str
