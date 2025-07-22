import uuid
import numpy as np
from datetime import datetime
from typing import List

from the_judge.domain.tracking.ports import BodyDetectorPort
from the_judge.domain.tracking.model import Body
from the_judge.infrastructure.tracking.providers import YOLOProvider
from the_judge.common.logger import setup_logger

logger = setup_logger('BodyDetector')

class BodyDetector(BodyDetectorPort):
    
    def __init__(self):
        self.model = YOLOProvider.get_instance()
    
    def detect_bodies(self, image: np.ndarray, frame_id: str) -> List[Body]:
        if self.model is None:
            logger.warning("YOLO model not available, returning empty body list")
            return []
        
        try:
            # Use original detection logic
            results = self.model(image, verbose=False)[0]
            bodies = []
            
            for r in results.boxes.data:
                x1, y1, x2, y2, conf, cls = r.tolist()
                if int(cls) == 0:  # Person class
                    # Convert to (x, y, w, h) format like original
                    rect = (int(x1), int(y1), int(x2), int(y2))
                    
                    body = Body(
                        id=str(uuid.uuid4()),
                        frame_id=frame_id,
                        bbox=rect,
                        captured_at=datetime.now()
                    )
                    bodies.append(body)
            
            logger.info(f"Detected {len(bodies)} bodies in frame_id {frame_id}")
            return bodies
            
        except Exception as e:
            logger.error(f"Error detecting bodies: {e}")
            return []
