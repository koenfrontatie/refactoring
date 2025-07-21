import uuid
from datetime import datetime
from typing import List, Optional

from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Collection
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork


class FrameProcessingService:
    
    def __init__(self):
        pass
    
    async def process_frame(self, frame_id: int, uow: AbstractUnitOfWork):
        with uow:
            frame = uow.tracking.get_frame(frame_id)
            if not frame:
                raise ValueError(f"Frame {frame_id} not found")
            
            await self._ensure_collection(frame.collection_id, uow)
            
            faces = await self._extract_faces(frame)
            bodies = await self._extract_bodies(frame)
            
            for face in faces:
                uow.tracking.add_face(face)
            for body in bodies:
                uow.tracking.add_body(body)
            
            face_body_matches = await self._match_faces_to_bodies(faces, bodies)
            recognition_results = await self._recognize_faces(faces)
            
            detections = await self._create_detections(
                frame, face_body_matches, recognition_results
            )
            
            for detection in detections:
                uow.tracking.add_detection(detection)
            
            uow.commit()
    
    async def _ensure_collection(self, collection_id: Optional[int], uow: AbstractUnitOfWork) -> Collection:
        if not collection_id:
            return None
            
        collection = uow.tracking.get_collection(collection_id)
        if not collection:
            collection = Collection(
                id=collection_id,
                created_at=datetime.now(),
                uuid=str(uuid.uuid4())
            )
            uow.tracking.add_collection(collection)
        
        return collection
    
    async def _extract_faces(self, frame: Frame) -> List[Face]:
        # TODO: Implement actual face detection
        # For now, return empty list as placeholder
        return []
    
    async def _extract_bodies(self, frame: Frame) -> List[Body]:
        # TODO: Implement actual body detection
        # For now, return empty list as placeholder
        return []
    
    async def _match_faces_to_bodies(self, faces: List[Face], bodies: List[Body]) -> dict:
        # TODO: Implement face-to-body matching logic
        # Return mapping of face_id -> body_id
        return {}
    
    async def _recognize_faces(self, faces: List[Face]) -> dict:
        # TODO: Implement face recognition against historical data
        # Return mapping of face_id -> visitor_record
        return {}
    
    async def _create_detections(
        self, 
        frame: Frame, 
        face_body_matches: dict, 
        recognition_results: dict
    ) -> List[Detection]:
        detections = []
        
        for face_id, recognition_data in recognition_results.items():
            body_id = face_body_matches.get(face_id)
            
            detection = Detection(
                frame_id=frame.id,
                face_id=face_id,
                body_id=body_id,
                visitor_record=recognition_data,
                captured_at=datetime.now(),
                uuid=str(uuid.uuid4())
            )
            detections.append(detection)
        
        return detections
