import uuid
import numpy as np
from datetime import datetime
from typing import List
import cv2

from the_judge.domain.tracking.ports import FaceDetectorPort
from the_judge.domain.tracking.model import Face
from the_judge.infrastructure.tracking.providers import InsightFaceProvider
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger('FaceDetector')

class FaceDetector(FaceDetectorPort):
    
    def __init__(self):
        self.cfg = get_settings()
        self.face_app = InsightFaceProvider.get_instance()
    
    def detect_faces(self, image: np.ndarray, frame_id: str) -> List[Face]:
        """Detect faces in image and return Face objects with embeddings"""
        if self.face_app is None:
            logger.warning("InsightFace not available, returning empty face list")
            return []
        
        try:
            insight_faces = self.face_app.get(image)
            logger.info(f"InsightFace found {len(insight_faces)} raw faces")
            
            faces = []
            for idx, i_face in enumerate(insight_faces):
                if not self._is_quality_face(i_face):
                    logger.debug(f"Face {idx} rejected by quality filter. Det: {getattr(i_face, 'det_score', 0):.2f}")
                    continue
                
                # Extract face data using original logic
                bbox = i_face.bbox.astype(int)
                rect = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
                
                quality_score = self._calculate_quality(i_face)
                
                face = Face(
                    id=str(uuid.uuid4()),
                    frame_id=frame_id,
                    bbox=rect,
                    embedding=i_face.embedding,
                    normed_embedding=i_face.normed_embedding,
                    embedding_norm=float(i_face.embedding_norm),
                    det_score=float(i_face.det_score),
                    quality_score=quality_score,
                    pose=self._get_pose_string(i_face),
                    age=int(getattr(i_face, 'age', 0)) if hasattr(i_face, 'age') else None,
                    sex=self._get_sex_string(i_face),
                    captured_at=datetime.now()
                )
                faces.append(face)
            
            logger.info(f"Returning {len(faces)} quality faces for frame_id {frame_id}")
            return faces
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def _is_quality_face(self, i_face) -> bool:
        """Quality check using original logic"""
        # Basic detection score threshold
        det_score = getattr(i_face, 'det_score', 0.0)
        if det_score < self.cfg.face_detection_threshold:
            return False
        
        # Face size check
        bbox = i_face.bbox.astype(int)
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        face_area = face_width * face_height
        
        min_face_area = 2500  # Can be made configurable
        if face_area < min_face_area:
            return False
        
        # Embedding norm check
        embedding_norm = getattr(i_face, 'embedding_norm', 0.0)
        if embedding_norm < 10.0:  # Can be made configurable
            return False
        
        # Pose check (simplified)
        pose = getattr(i_face, 'pose', (99.0, 99.0, 99.0))
        max_yaw = 45.0  # Can be made configurable
        max_pitch = 30.0  # Can be made configurable
        
        if abs(pose[0]) > max_yaw or abs(pose[1]) > max_pitch:
            return False
        
        return True
    
    def _calculate_quality(self, i_face) -> float:
        """Calculate quality using original algorithm"""
        det_score = getattr(i_face, 'det_score', 0.0)
        embedding_norm = getattr(i_face, 'embedding_norm', 0.0)
        norm_score = min(1.0, embedding_norm / 20.0)
        
        # Pose penalty
        pose = getattr(i_face, 'pose', (0, 0, 0))
        pose_penalty = 1.0 - (abs(pose[0]) + abs(pose[1])) / 90.0
        pose_penalty = max(0.0, pose_penalty)
        
        final_quality = (det_score * 0.6 + norm_score * 0.3 + pose_penalty * 0.1)
        return max(0.0, min(1.0, final_quality))
    
    def _get_pose_string(self, i_face) -> str:
        """Convert pose to string representation"""
        pose = getattr(i_face, 'pose', (0, 0, 0))
        return f"{pose[0]:.1f},{pose[1]:.1f},{pose[2]:.1f}"
    
    def _get_sex_string(self, i_face) -> str:
        """Convert gender to string"""
        gender = getattr(i_face, 'gender', None)
        if gender is None:
            return None
        return 'M' if int(gender) == 1 else 'F'
