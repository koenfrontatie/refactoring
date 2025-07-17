# src/domain/model.py
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class Frame:
    id: str
    captured_at: datetime
    camera: str
    detection: str = None  

@dataclass
class Camera:
    id: str           
    state: str
    first_seen: datetime
    last_seen: datetime        

# Linking multiple cameras
@dataclass
class Detection:
    id: str           
    captured_at: datetime
