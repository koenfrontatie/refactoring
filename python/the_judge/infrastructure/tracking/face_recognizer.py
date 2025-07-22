from __future__ import annotations
from typing import List, Dict, Optional, Callable
import numpy as np

from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.domain.tracking.model import Face
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.common.logger import setup_logger

logger = setup_logger("FaceRecognizer")


class FaceRecognizer(FaceRecognizerPort):
    def __init__(
        self,
        *,
        uow_factory: Callable[[], AbstractUnitOfWork],
        model,                       
        threshold: float,
    ):
        self.uow_factory = uow_factory
        self.model = model
        self.threshold = threshold

    def recognize_faces(self, faces: List[Face]) -> Dict[str, Optional[dict]]:
        if not faces:
            return {}

        result: Dict[str, Optional[dict]] = {f.id: None for f in faces}
        exclude_ids = {f.id for f in faces}

        with self.uow_factory() as uow:
            # ---------- first pass: most‑recent slice ----------
            recent = [
                g
                for g in uow.repository.get_recent(Face, limit=100)
                if g.id not in exclude_ids
            ]
            for q in faces:
                if self._valid(q) and result[q.id] is None:
                    result[q.id] = self._match(q, recent)

            # ---------- second pass: older slice for still‑unmatched ----------
            unmatched = [f for f in faces if result[f.id] is None]
            if unmatched:
                older = [
                    g
                    for g in uow.repository.get_all_sorted(Face, offset=100)
                    if g.id not in exclude_ids
                ]
                for q in unmatched:
                    result[q.id] = self._match(q, older)

        return result

    def _valid(self, f: Face) -> bool:
        return f.normed_embedding is not None and (f.quality_score or 0) > 0.5

    def _sim(self, a: np.ndarray, b: np.ndarray) -> float:
        if hasattr(self.model, "compute_sim"):
            return float(self.model.compute_sim(a, b))
        return float(np.dot(a, b))

    def _match(self, query: Face, gallery: List[Face]) -> Optional[dict]:
        best, best_sim = None, 0.0
        qe = query.normed_embedding
        for g in gallery:
            if g.normed_embedding is None:
                continue
            s = self._sim(qe, g.normed_embedding)
            if s >= self.threshold and s > best_sim:
                best, best_sim = g, s
        if best:
            return {
                "matched_face_id": best.id,
                "similarity_score": best_sim,
                "recognition_type": "face_embedding_match",
            }
        return None
