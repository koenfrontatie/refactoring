import uuid
from datetime import datetime
from typing import List, Callable, Tuple

import cv2
import numpy as np

from the_judge.domain.tracking.ports import FaceDetectorPort
from the_judge.domain.tracking.model import Face, FaceEmbedding, Composite
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now
from the_judge.settings import get_settings
logger = setup_logger("FaceDetector")


class FaceDetector(FaceDetectorPort):
    def __init__(
        self,
        face_model,
        *,
        det_thresh: float = 0.5,
        min_area: int = 2500,
        min_norm: float = 15,
    ):
        self.app = face_model
        self.det_thresh = det_thresh
        self.min_area = min_area
        self.min_norm = min_norm

    def detect_faces(self, image: np.ndarray, frame_id: str) -> List[Composite]:
        composites: List[Composite] = []
        current_time = now()

        for raw in self.app.get(image):  
            if not self._quality(raw):
                continue

            x1, y1, x2, y2 = raw.bbox.astype(int).tolist()
            
            # Create FaceEmbedding first
            face_embedding = FaceEmbedding(
                id=str(uuid.uuid4()),
                embedding=raw.embedding,
                normed_embedding=raw.normed_embedding
            )
            
            # Create Face with reference to embedding
            face = Face(
                id=str(uuid.uuid4()),
                frame_id=frame_id,
                bbox=(x1, y1, x2, y2),
                embedding_id=face_embedding.id,
                embedding_norm=float(raw.embedding_norm),
                det_score=float(raw.det_score),
                quality_score=self._quality_score(raw),
                pose=f"{raw.pose[0]:.1f},{raw.pose[1]:.1f},{raw.pose[2]:.1f}",
                age=int(getattr(raw, "age", 0)) or None,
                sex="M" if getattr(raw, "gender", -1) == 1 else "F",
                captured_at=current_time,
            )

            composite = Composite(face=face, embedding=face_embedding)

            composites.append(composite)

        return composites

    def _quality(self, f) -> bool:
        if getattr(f, "det_score", 0.0) < self.det_thresh:
            return False

        w, h = (f.bbox[2] - f.bbox[0], f.bbox[3] - f.bbox[1])
        if w * h < self.min_area:
            return False

        if getattr(f, "embedding_norm", 0.0) < self.min_norm:
            return False

        return True

    def _quality_score(self, f) -> float:
        det_score = getattr(f, "det_score", 0.0)
        norm_score = min(1.0, getattr(f, "embedding_norm", 0.0) / 20.0)
        yaw, pitch, _ = getattr(f, "pose", (0.0, 0.0, 0.0))
        pose_penalty = max(0.0, 1.0 - (abs(yaw) + abs(pitch)) / 90.0)

        final_quality = (det_score * 0.6 + norm_score * 0.3 + pose_penalty * 0.1)
        final_quality = max(0.0, min(1.0, final_quality))
        
        return final_quality
