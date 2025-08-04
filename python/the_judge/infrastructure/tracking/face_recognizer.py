# the_judge/infrastructure/tracking/face_recognizer.py
from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np

from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.model import FaceEmbedding, Composite, Detection, Visitor
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork

logger = setup_logger("FaceRecognizer")


class FaceRecognizer(FaceRecognizerPort):
    
    def __init__(
        self,
        face_model,
        uow_factory: Callable[[], AbstractUnitOfWork],
        threshold: float = 0.5,
    ) -> None:
        self.face_model = face_model
        self.uow_factory = uow_factory
        self.threshold = threshold

    def recognize_faces(self, faces: List[Composite]) -> List[Composite]:
        """Recognize faces against known embeddings in database. Returns composite objects with matched visitors attached."""
        if not faces:
            return []

        results = []

        with self.uow_factory() as uow:
            # Get all embeddings from repository
            all_embeddings = uow.repository.list(FaceEmbedding)

            for face_composite in faces:
                visitor = self._find_visitor(face_composite, all_embeddings, uow)
                updated_composite = Composite(
                    face=face_composite.face,
                    embedding=face_composite.embedding,
                    body=face_composite.body,
                    visitor=visitor
                )
                results.append(updated_composite)

        return results

    def match_against_collection(self, composite: Composite, collection: List[Composite]) -> Optional[Visitor]:
        for existing in collection:
            if self._sim(composite.embedding.normed_embedding, existing.embedding.normed_embedding) > self.threshold:
                return existing.visitor
        return None
    
    def _find_visitor(
        self, 
        query_composite: Composite, 
        gallery_embeddings: List[FaceEmbedding],
        uow: AbstractUnitOfWork
    ) -> Optional[Visitor]:
        """
        1. Search for matching embedding in repository
        2. If found, search detection table with that embedding_id 
        3. Get visitor_id from detection and return full Visitor object
        """
        if not self._valid_composite(query_composite):
            return None

        # Step 1: Find best matching embedding
        best_embedding = self._find_best_matching_embedding(query_composite, gallery_embeddings)
        
        if not best_embedding:
            return None

        # Step 2: Get detection by embedding_id
        detection = uow.repository.get_by(Detection, embedding_id=best_embedding.id)
        
        if detection:
            visitor_id = detection.visitor.id
            if visitor_id:
                # Step 3: Get full Visitor object
                visitor = uow.repository.get(Visitor, visitor_id)
                return visitor

        # No detection found with this embedding or no visitor found
        return None
    
    def _find_best_matching_embedding(
        self, 
        query_composite: Composite, 
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


    def _valid_composite(self, fc: Composite) -> bool:
        return (fc.embedding.normed_embedding is not None and 
                (fc.face.quality_score or 0) > 0.5)

    def _sim(self, a: np.ndarray, b: np.ndarray) -> float:
        # Use InsightFace's optimised function if available
        model = getattr(self.face_model, "model", None)
        if model and hasattr(model, "compute_sim"):
            return float(model.compute_sim(a, b))
        return float(np.dot(a, b))