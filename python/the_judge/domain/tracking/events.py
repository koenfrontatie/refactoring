from dataclasses import dataclass
from abc import ABC
from typing import Optional
from .model import Frame, Face, Body

class Event(ABC):
    pass

@dataclass
class FrameSaved(Event):
    frame: Frame

@dataclass
class FrameProcessed(Event):
    frame: Frame
    faces: Optional[list[Face]]
    bodies: Optional[list[Body]]
