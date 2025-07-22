# the_judge/infrastructure/tracking/face_recognizer.py
from __future__ import annotations

from typing import Callable, Dict, List, Optional

import numpy as np

from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.model import Face
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork

logger = setup_logger("FaceRecognizer")


class FaceRecognizer(FaceRecognizerPort):
    """
    Two‑pass recogniser.
      • first checks the most‑recent RECENT_LIMIT faces
      • then (for still‑unmatched) the next slice of SECOND_LIMIT faces
    """

    RECENT_LIMIT = 100
    SECOND_LIMIT = 300

    def __init__(
        self,
        *,
        uow_factory: Callable[[], AbstractUnitOfWork],
        provider,  # InsightFaceProvider instance
        threshold: float,
    ) -> None:
        self.uow_factory = uow_factory
        self.provider = provider
        self.threshold = threshold

    # ---------------------------------------------------------------------#
    # public API
    # ---------------------------------------------------------------------#
    def recognize_faces(self, faces: List[Face]) -> Dict[str, Optional[dict]]:
        if not faces:
            return {}

        results: Dict[str, Optional[dict]] = {f.id: None for f in faces}
        exclude_ids = {f.id for f in faces}

        with self.uow_factory() as uow:
            # -------- pass 1: newest slice --------------------------------
            gallery = [
                g
                for g in uow.repository.get_recent(Face, limit=self.RECENT_LIMIT + len(exclude_ids))
                if g.id not in exclude_ids
            ]
            self._match_batch(faces, gallery, results)

            # -------- pass 2: older slice ---------------------------------
            unmatched = [f for f in faces if results[f.id] is None]
            if unmatched:
                older_gallery = [
                    g
                    for g in uow.repository.get_all_sorted(Face, offset=self.RECENT_LIMIT)
                    if g.id not in exclude_ids
                ][: self.SECOND_LIMIT]
                self._match_batch(unmatched, older_gallery, results)

        return results

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _match_batch(
        self,
        queries: List[Face],
        gallery: List[Face],
        output: Dict[str, Optional[dict]],
    ) -> None:
        for q in queries:
            if not self._valid(q):
                continue
            best = self._best_match(q, gallery)
            if best:
                output[q.id] = best

    def _valid(self, f: Face) -> bool:
        return f.normed_embedding is not None and (f.quality_score or 0) > 0.5

    def _sim(self, a: np.ndarray, b: np.ndarray) -> float:
        # Use InsightFace's optimised function if available
        model = getattr(self.provider.app, "model", None)
        if model and hasattr(model, "compute_sim"):
            return float(model.compute_sim(a, b))
        return float(np.dot(a, b))

    def _best_match(self, query: Face, gallery: List[Face]) -> Optional[dict]:
        best_face, best_sim = None, 0.0
        qe = query.normed_embedding
        for g in gallery:
            if g.normed_embedding is None or g.id == query.id:
                continue
            sim = self._sim(qe, g.normed_embedding)
            if sim >= self.threshold and sim > best_sim:
                best_face, best_sim = g, sim
        if best_face:
            return {
                "matched_face_id": best_face.id,
                "similarity_score": best_sim,
                "recognition_type": "face_embedding_match",
            }
        return None
