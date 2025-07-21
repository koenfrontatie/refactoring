import uuid
import asyncio
import cv2
import numpy as np
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Collection
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from the_judge.application.face_recognition_service import FaceRecognitionService
from the_judge.common.logger import setup_logger

logger = setup_logger('TrackingService')

class TrackingService:
    
    def __init__(self, face_detector, body_detector, face_body_matcher):
        self.face_detector = face_detector
        self.body_detector = body_detector  
        self.face_body_matcher = face_body_matcher
        self.face_recognition_service = FaceRecognitionService()
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def process_frame(self, frame_id: int, image_path: str):
        """Process frame from saved file"""
        try:
            # Load image from file
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to load image from {image_path}")
                return
            
            # Convert BGR to RGB for ML models
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Run processing in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._process_frame_sync,
                frame_id,
                image_rgb
            )
            
        except Exception as e:
            logger.error(f"Error processing frame {frame_id}: {e}")
    
    def _process_frame_sync(self, frame_id: int, image: np.ndarray):
        """Synchronous frame processing"""
        try:
            uow = SqlAlchemyUnitOfWork()
            
            # Detect faces and bodies
            faces = self.face_detector.detect_faces(image, frame_id)
            bodies = self.body_detector.detect_bodies(image, frame_id)
            
            with uow:
                # Save faces and bodies
                for face in faces:
                    uow.tracking.add_face(face)
                for body in bodies:
                    uow.tracking.add_body(body)
                
                uow.commit()
                
                # Match and recognize
                face_body_matches = self.face_body_matcher.match_faces_to_bodies(faces, bodies)
                recognition_results = self.face_recognition_service.recognize_faces(faces, uow)
                
                # Create detections
                detections = self._create_detections(frame_id, face_body_matches, recognition_results)
                
                for detection in detections:
                    uow.tracking.add_detection(detection)
                
                uow.commit()
                
            logger.info(f"Processed frame {frame_id}: {len(faces)} faces, {len(bodies)} bodies, {len(detections)} detections")
            
        except Exception as e:
            logger.error(f"Error in frame processing for {frame_id}: {e}")
    
    def _ensure_collection(self, collection_id: Optional[int], uow: AbstractUnitOfWork) -> Collection:
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
    
    def _create_detections(self, frame_id: int, face_body_matches: dict, recognition_results: dict) -> List[Detection]:
        detections = []
        
        for face_id, recognition_data in recognition_results.items():
            body_id = face_body_matches.get(face_id)
            
            detection = Detection(
                frame_id=frame_id,
                face_id=face_id,
                body_id=body_id,
                visitor_record=recognition_data or {},
                captured_at=datetime.now(),
                uuid=str(uuid.uuid4())
            )
            detections.append(detection)
        
        return detections
