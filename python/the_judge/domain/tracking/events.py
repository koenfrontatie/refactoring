from __future__ import annotations  # Add this line

from dataclasses import dataclass
from abc import ABC

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from the_judge.domain.tracking.model import Visitor, Frame, VisitorSession

class Event(ABC):
    pass

@dataclass
class FrameSaved(Event):
    frame: Frame

@dataclass
class FrameProcessed(Event):
    frame: Frame
    detection_count: int

@dataclass
class VisitorPromoted(Event):
    visitor: Visitor

@dataclass
class VisitorReturned(Event):
    visitor: Visitor

@dataclass
class SessionStarted(Event):
    visitor: Visitor
    session: VisitorSession

@dataclass
class SessionEnded(Event):
    visitor: Visitor
    session: VisitorSession

@dataclass
class VisitorWentMissing(Event):
    visitor: Visitor

@dataclass
class VisitorExpired(Event):
    visitor: Visitor
