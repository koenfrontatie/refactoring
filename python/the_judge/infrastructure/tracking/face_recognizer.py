# the_judge/infrastructure/tracking/face_recognizer.py
from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np

from the_judge.common.logger import setup_logger
from the_judge.domain.tracking import FaceEmbedding, FaceComposite, Detection
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork

logger = setup_logger("FaceRecognizer")


class FaceRecognizer(FaceRecognizerPort):
    
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

    def recognize_faces(self, faces: List[FaceComposite]) -> List[Optional[str]]:
        """Recognize faces against known embeddings in database. Returns list of visitor id or none."""
        if not faces:
            return []

        results = []

        with self.uow_factory() as uow:
            # Get all embeddings from repository
            all_embeddings = uow.repository.list(FaceEmbedding)

            for face_composite in faces:
                visitor_name = self._find_visitor_id(face_composite, all_embeddings, uow)
                results.append(visitor_name)

        return results

    def _find_visitor_id(
        self, 
        query_composite: FaceComposite, 
        gallery_embeddings: List[FaceEmbedding],
        uow: AbstractUnitOfWork
    ) -> Optional[str]:
        """
        1. Search for matching embedding in repository
        2. If found, search detection table with that embedding_id 
        3. Return visitor_name from detection, or None
        """
        if not self._valid_composite(query_composite):
            return None

        # Step 1: Find best matching embedding
        best_embedding = self._find_best_matching_embedding(query_composite, gallery_embeddings)
        
        if not best_embedding:
            return None

        # Step 2: Get detection by embedding_id (much more efficient!)
        detection = uow.repository.get_by(Detection, embedding_id=best_embedding.id)
        
        if detection:
            return detection.visitor_record.get('id')

        # No detection found with this embedding
        return None
    
    def _find_best_matching_embedding(
        self, 
        query_composite: FaceComposite, 
        gallery_embeddings: List[FaceEmbedding]
    ) -> Optional[FaceEmbedding]:
        """Find the best matching embedding in the gallery."""
        best_embedding, best_sim = None, 0.0
        query_normed = query_composite.embedding.normed_embedding

        for gallery_embedding in gallery_embeddings:
            if gallery_embedding.normed_embedding is None:
                continue
                
            sim = self._sim(query_normed, gallery_embedding.normed_embedding)
            if sim >= self.threshold and sim > best_sim:
                best_embedding, best_sim = gallery_embedding, sim

        return best_embedding

    def _valid_composite(self, fc: FaceComposite) -> bool:
        return (fc.embedding.normed_embedding is not None and 
                (fc.face.quality_score or 0) > 0.5)

    def _sim(self, a: np.ndarray, b: np.ndarray) -> float:
        # Use InsightFace's optimised function if available
        model = getattr(self.provider.app, "model", None)
        if model and hasattr(model, "compute_sim"):
            return float(model.compute_sim(a, b))
        return float(np.dot(a, b))