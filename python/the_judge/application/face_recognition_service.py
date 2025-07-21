from typing import List, Dict, Optional
from sqlalchemy import desc

from the_judge.domain.tracking.model import Face
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger('FaceRecognitionService')

class FaceRecognitionService:
    """Application service for face recognition business logic"""
    
    def __init__(self):
        self.cfg = get_settings()
    
    def recognize_faces(self, faces: List[Face], uow: AbstractUnitOfWork) -> Dict[int, Optional[dict]]:
        """Find matches for faces against known faces in database"""
        recognition_results = {}
        
        if not faces:
            return recognition_results
        
        try:
            with uow:
                gallery_faces = self._get_gallery_faces(uow)
                
                for face in faces:
                    if face.id is None or face.normed_embedding is None:
                        recognition_results[face.id] = None
                        continue
                    
                    match = self._find_best_match(face, gallery_faces)
                    
                    if match:
                        recognition_results[face.id] = self._create_match_record(face, match)
                        logger.info(f"Face {face.id} matched to face {match['face_id']} with similarity {match['similarity']:.3f}")
                    else:
                        recognition_results[face.id] = None
                        logger.info(f"Face {face.id} is a new person")
        
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            # Return None for all faces on error
            for face in faces:
                if face.id is not None:
                    recognition_results[face.id] = None
        
        return recognition_results
    
    def _get_gallery_faces(self, uow: AbstractUnitOfWork) -> List[Face]:
        """Get recent faces from database for comparison"""
        session = uow.session
        return session.query(Face).order_by(desc(Face.captured_at)).limit(100).all()
    
    def _find_best_match(self, query_face: Face, gallery_faces: List[Face]) -> Optional[dict]:
        """Find best matching face using business rules"""
        best_match = None
        best_similarity = 0.0
        
        for gallery_face in gallery_faces:
            # Skip self-comparison and faces without embeddings
            if (gallery_face.id == query_face.id or 
                gallery_face.normed_embedding is None):
                continue
            
            # Calculate similarity (infrastructure concern delegated to simple calculation)
            similarity = self._calculate_similarity(query_face.normed_embedding, gallery_face.normed_embedding)
            
            # Apply business rule: similarity threshold and best match
            if (similarity >= self.cfg.face_recognition_threshold and 
                similarity > best_similarity):
                best_similarity = similarity
                best_match = {
                    'face_id': gallery_face.id,
                    'similarity': similarity,
                    'gallery_face': gallery_face
                }
        
        return best_match
    
    def _calculate_similarity(self, embedding1, embedding2) -> float:
        """Simple cosine similarity for normalized embeddings"""
        import numpy as np
        return float(np.dot(embedding1, embedding2))
    
    def _create_match_record(self, query_face: Face, match: dict) -> dict:
        """Create visitor record based on match - business logic"""
        return {
            'matched_face_id': match['face_id'],
            'similarity_score': match['similarity'],
            'matched_at': query_face.captured_at.isoformat(),
            'recognition_type': 'face_embedding_match'
        }