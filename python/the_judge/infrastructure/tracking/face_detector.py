import uuid
from datetime import datetime
from typing import List, Callable, Tuple

import cv2
import numpy as np

from the_judge.domain.tracking.ports import FaceDetectorPort
from the_judge.domain.tracking.model import Face
from the_judge.common.logger import setup_logger

logger = setup_logger("FaceDetector")


class FaceDetector(FaceDetectorPort):
    def __init__(
        self,
        insight_provider,
        *,
        det_thresh: float,
        min_area: int,
        min_norm: float,
        max_yaw: float,
        max_pitch: float,
    ):
        self.app = insight_provider
        self.det_thresh = det_thresh
        self.min_area = min_area
        self.min_norm = min_norm
        self.max_yaw = max_yaw
        self.max_pitch = max_pitch

    def detect_faces(self, image: np.ndarray, frame_id: str) -> List[Face]:
        if self.app is None:
            return []

        faces_out: List[Face] = []
        now = datetime.now()

        for raw in self.app.get(image):
            if not self._quality(raw):
                continue

            x1, y1, x2, y2 = raw.bbox.astype(int).tolist()
            faces_out.append(
                Face(
                    id=str(uuid.uuid4()),
                    frame_id=frame_id,
                    bbox=(x1, y1, x2, y2),
                    embedding=raw.embedding,
                    normed_embedding=raw.normed_embedding,
                    embedding_norm=float(raw.embedding_norm),
                    det_score=float(raw.det_score),
                    quality_score=self._quality_score(raw),
                    pose=f"{raw.pose[0]:.1f},{raw.pose[1]:.1f},{raw.pose[2]:.1f}",
                    age=int(getattr(raw, "age", 0)) or None,
                    sex="M" if getattr(raw, "gender", -1) == 1 else "F",
                    captured_at=now,
                )
            )

        return faces_out

    def _quality(self, f) -> bool:
        if getattr(f, "det_score", 0.0) < self.det_thresh:
            return False

        w, h = (f.bbox[2] - f.bbox[0], f.bbox[3] - f.bbox[1])
        if w * h < self.min_area:
            return False

        if getattr(f, "embedding_norm", 0.0) < self.min_norm:
            return False

        yaw, pitch, _ = getattr(f, "pose", (0.0, 0.0, 0.0))
        if abs(yaw) > self.max_yaw or abs(pitch) > self.max_pitch:
            return False

        return True

    def _quality_score(self, f) -> float:
        det = getattr(f, "det_score", 0.0)
        norm = min(1.0, getattr(f, "embedding_norm", 0.0) / 20.0)
        yaw, pitch, _ = getattr(f, "pose", (0.0, 0.0, 0.0))
        pose_penalty = max(0.0, 1.0 - (abs(yaw) + abs(pitch)) / 90.0)
        return max(0.0, min(1.0, det * 0.6 + norm * 0.3 + pose_penalty * 0.1))
