from dataclasses import dataclass
from abc import ABC
from datetime import datetime
from tracking import Frame, Face, Body, Detection

class Event(ABC):
    pass

@dataclass
class FrameSaved(Event):
    frame: Frame

@dataclass
class FrameProcessed(Event):
    frame: Frame
