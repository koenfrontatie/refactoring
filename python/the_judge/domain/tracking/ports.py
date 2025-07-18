# src/domain/ports.py
from abc import ABC, abstractmethod
from typing import List, Protocol
#from model import Frame

class FrameCollectorPort(ABC):

    @abstractmethod
    def register_camera(self, command):
        pass

    @abstractmethod
    def unregister_camera(self, command):
        pass

    @abstractmethod
    def ingest_frame(self, command):
        pass