import numpy as np
from typing import List, Optional, Tuple
from scipy.optimize import linear_sum_assignment

from the_judge.domain.tracking.ports import FaceBodyMatcherPort
from the_judge.domain.tracking.model import Face, Body
from the_judge.common.logger import setup_logger

logger = setup_logger('FaceBodyMatcher')

class FaceBodyMatcher(FaceBodyMatcherPort):
    
    def match_faces_to_bodies(self, faces: List[Face], bodies: List[Body]) -> List[Tuple[Face, Optional[Body]]]:
        if not faces:
            return []
            
        if not bodies:
            return [(face, None) for face in faces]
        
        cost_matrix = np.zeros((len(faces), len(bodies)))
        
        for i, face in enumerate(faces):
            fx1, fy1, fx2, fy2 = face.bbox
            for j, body in enumerate(bodies):
                bx1, by1, bx2, by2 = body.bbox
                
                ix1, iy1 = max(fx1, bx1), max(fy1, by1)
                ix2, iy2 = min(fx2, bx2), min(fy2, by2)
                
                if ix1 >= ix2 or iy1 >= iy2:
                    cost_matrix[i, j] = 1.0
                    continue
                
                intersection_area = (ix2 - ix1) * (iy2 - iy1)
                face_area = (fx2 - fx1) * (fy2 - fy1)
                proportion_inside = intersection_area / face_area
                
                if proportion_inside == 0.0:
                    cost_matrix[i, j] = 1.0
                    continue
                
                face_center_y = (fy1 + fy2) / 2
                body_height = by2 - by1
                body_top_region = by1 + body_height * 0.4
                vertical_dist_from_top = max(0, face_center_y - body_top_region)
                vertical_position = np.exp(-vertical_dist_from_top / (body_height * 0.25))
                
                face_width = fx2 - fx1
                body_width = bx2 - bx1
                
                if body_width <= 0:
                    cost_matrix[i, j] = 1.0
                    continue
                
                width_ratio = face_width / body_width
                if width_ratio >= 0.25:
                    width_score = 1.0
                elif width_ratio >= 0.15:
                    width_score = 0.2
                else:
                    width_score = 0.0
                
                if width_score <= 0.1:
                    cost_matrix[i, j] = 1.0
                    continue
                
                match_score = (
                    proportion_inside * 0.5 + 
                    vertical_position * 0.3 +
                    width_score * 0.2
                )
                
                cost_matrix[i, j] = 1.0 - match_score
        
        face_indices, body_indices = linear_sum_assignment(cost_matrix)
        
        face_to_body = {}
        for f_idx, b_idx in zip(face_indices, body_indices):
            match_score = 1.0 - cost_matrix[f_idx, b_idx]
            if match_score >= 0.3:
                face_to_body[f_idx] = b_idx
                logger.debug(f"Face {faces[f_idx].id} matched to body {bodies[b_idx].id} with score {match_score:.3f}")
        
        result = []
        
        for face in faces:
            face_idx = faces.index(face)
            if face_idx in face_to_body:
                body_idx = face_to_body[face_idx]
                result.append((face, bodies[body_idx]))
            else:
                result.append((face, None))
        
        matched_count = len(face_to_body)
        logger.info(f"Matched {matched_count} faces to bodies out of {len(faces)} faces")
        return result
