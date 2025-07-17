# src/domain/ports.py
from abc import ABC, abstractmethod
from typing import List, Protocol
from .model import CameraDescriptor, Frame

class CameraPort(ABC):
    @abstractmethod
    def open(self) -> None: ...
    @abstractmethod
    def read(self) -> Frame: ...
    @abstractmethod
    def close(self) -> None: ...
