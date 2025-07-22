from typing import List, Dict, Optional
import numpy as np

from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.domain.tracking.model import Face
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger('FaceRecognizer')

class FaceRecognizer(FaceRecognizerPort):
    
    def __init__(self):
        self.cfg = get_settings()
    
    def recognize_faces(self, faces: List[Face]) -> Dict[str, Optional[dict]]:
        recognition_results = {}
        
        if not faces:
            return recognition_results
        
        try:
            uow = SqlAlchemyUnitOfWork()
            gallery_faces = self._get_gallery_faces(uow)
            
            for face in faces:
                if not self._is_valid_face(face):
                    recognition_results[face.id] = None
                    continue
                
                match_result = self._find_best_visitor_match(face, gallery_faces)
                recognition_results[face.id] = match_result
                
                if match_result:
                    logger.info(f"Face {face.id} matched with confidence {match_result.get('similarity_score', 0):.3f}")
                else:
                    logger.info(f"Face {face.id} represents a new visitor")
        
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            for face in faces:
                if face.id is not None:
                    recognition_results[face.id] = None
        
        return recognition_results
    
    def _get_gallery_faces(self, uow: AbstractUnitOfWork) -> List[Face]:
        from sqlalchemy import desc
        
        with uow:
            return uow.session.query(Face).order_by(desc(Face.captured_at)).limit(100).all()
    
    def _is_valid_face(self, face: Face) -> bool:
        return (
            face.id is not None and 
            face.normed_embedding is not None and
            face.quality_score and face.quality_score > 0.5
        )
    
    def _find_best_visitor_match(self, query_face: Face, gallery_faces: List[Face]) -> Optional[dict]:
        best_match = None
        best_similarity = 0.0
        
        for gallery_face in gallery_faces:
            if not self._can_compare_faces(query_face, gallery_face):
                continue
            
            similarity = self._calculate_face_similarity(
                query_face.normed_embedding, 
                gallery_face.normed_embedding
            )
            
            if (similarity >= self.cfg.face_recognition_threshold and 
                similarity > best_similarity):
                best_similarity = similarity
                best_match = gallery_face
        
        if best_match:
            return {
                'matched_face_id': best_match.id,
                'similarity_score': best_similarity,
                'recognition_type': 'face_embedding_match'
            }
        else:
            return None
    
    def _can_compare_faces(self, face1: Face, face2: Face) -> bool:
        return (
            face1.id != face2.id and
            face2.normed_embedding is not None and
            hasattr(face2, 'quality_score') and face2.quality_score > 0.3
        )
    
    def _calculate_face_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        return float(np.dot(embedding1, embedding2))
