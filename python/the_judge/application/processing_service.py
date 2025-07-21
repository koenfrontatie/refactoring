import asyncio
import cv2
import uuid
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from the_judge.domain.tracking.ports import (
    FaceDetectorPort, 
    BodyDetectorPort, 
    FaceBodyMatcherPort,
    FaceRecognizerPort
)
from the_judge.domain.tracking.model import Detection
from the_judge.domain.events import FrameAnalyzed, FrameIngested
from the_judge.application.messagebus import MessageBus
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger('FrameProcessingService')

class FrameProcessingService:
    
    def __init__(
        self,
        face_detector: FaceDetectorPort,
        body_detector: BodyDetectorPort, 
        face_body_matcher: FaceBodyMatcherPort,
        face_recognizer: FaceRecognizerPort,
        bus: MessageBus
    ):
        self.face_detector = face_detector
        self.body_detector = body_detector
        self.face_body_matcher = face_body_matcher
        self.face_recognizer = face_recognizer
        self.bus = bus
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def handle_frame_ingested(self, event: FrameIngested):
        """Event handler for FrameIngested events"""
        # Get the image path from the frame info - reconstruct the path
        from pathlib import Path
        collection_dir = Path(get_settings().get_stream_path(event.collection_id))
        image_path = str(collection_dir / f"{event.camera_name}.jpg")
        
        # Start async processing
        asyncio.create_task(
            self.process_frame(event.frame_id, image_path)
        )
    
    async def process_frame(self, frame_id: int, image_path: str):
        try:
            image = await self._load_image(image_path)
            if image is None:
                logger.error(f"Failed to load image from {image_path}")
                return
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._process_frame_complete,
                frame_id,
                image
            )
            
        except Exception as e:
            logger.error(f"Error processing frame {frame_id}: {e}")
    
    def _process_frame_complete(self, frame_id: int, image: np.ndarray):
        try:
            uow = SqlAlchemyUnitOfWork()
            
            # Step 1: Detect faces and bodies via ports
            faces = self.face_detector.detect_faces(image, frame_id)
            bodies = self.body_detector.detect_bodies(image, frame_id)
            
            # Step 2: Save detected objects to database
            with uow:
                for face in faces:
                    uow.tracking.add_face(face)
                for body in bodies:
                    uow.tracking.add_body(body)
                uow.commit()
            
            # Raise frame analyzed event
            event = FrameAnalyzed(
                frame_id=frame_id,
                faces_detected=len(faces),
                bodies_detected=len(bodies),
                analyzed_at=datetime.now()
            )
            self.bus.handle(event)
            
            if not faces:
                logger.info(f"No faces detected in frame {frame_id}")
                return
            
            # Step 3: Match faces to bodies via port
            face_body_matches = self.face_body_matcher.match_faces_to_bodies(faces, bodies)
            
            # Step 4: Recognize faces via port
            recognition_results = self.face_recognizer.recognize_faces(faces)
            
            # Step 5: Create detections with visitor records
            detections = self._create_detections(frame_id, face_body_matches, recognition_results)
            
            # Step 6: Save detections to database
            with uow:
                for detection in detections:
                    uow.tracking.add_detection(detection)
                uow.commit()
            
            logger.info(f"Frame {frame_id}: {len(faces)} faces, {len(bodies)} bodies, {len(detections)} detections")
            
        except Exception as e:
            logger.error(f"Error in complete frame processing for {frame_id}: {e}")
    
    async def _load_image(self, image_path: str) -> Optional[np.ndarray]:
        def load_sync():
            image = cv2.imread(image_path)
            if image is None:
                return None
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, load_sync
        )
    
    def _create_detections(self, frame_id: int, face_body_matches: dict, recognition_results: dict) -> list:
        detections = []
        current_time = datetime.now()
        
        for face_id, recognition_data in recognition_results.items():
            body_id = face_body_matches.get(face_id)
            
            visitor_record = recognition_data or {}
            
            detection = Detection(
                frame_id=frame_id,
                face_id=face_id,
                body_id=body_id,
                visitor_record=visitor_record,
                captured_at=current_time,
                uuid=str(uuid.uuid4())
            )
            detections.append(detection)
        
        return detections
