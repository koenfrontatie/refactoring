# application/frame_processing_service.py

import asyncio
import cv2
import numpy as np
from datetime import datetime
from typing import List, NamedTuple
from concurrent.futures import ThreadPoolExecutor

from the_judge.domain.tracking.model import Frame, Face, Body
from the_judge.domain.tracking.ports import FaceDetectionPort, BodyDetectionPort, FaceBodyMatchingPort
from the_judge.domain.events import FrameAnalyzed
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.common.logger import setup_logger

logger = setup_logger('FrameProcessingService')

class FrameProcessingService:
    
    def __init__(
        self, 
        face_detector: FaceDetectionPort,
        body_detector: BodyDetectionPort, 
        face_body_matcher: FaceBodyMatchingPort,
        recognition_service,
        tracking_service,
        bus: MessageBus
    ):
        self.face_detector = face_detector
        self.body_detector = body_detector
        self.face_body_matcher = face_body_matcher
        self.recognition_service = recognition_service
        self.tracking_service = tracking_service
        self.bus = bus
        self.executor = ThreadPoolExecutor(max_workers=2)
    
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
            
            faces = self.face_detector.detect_faces(image, frame_id)
            bodies = self.body_detector.detect_bodies(image, frame_id)
            
            with uow:
                for face in faces:
                    uow.tracking.add_face(face)
                for body in bodies:
                    uow.tracking.add_body(body)
                uow.commit()
            
            # Raise FrameAnalyzed event
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
            
            face_body_matches = self.face_body_matcher.match_faces_to_bodies(faces, bodies)
            
            recognition_results = self.recognition_service.recognize_faces(faces, uow)
            
            tracking_result = self.tracking_service.track_visitors(
                frame_id=frame_id,
                face_body_matches=face_body_matches,
                recognition_results=recognition_results,
                uow=uow
            )
            
            logger.info(f"Frame {frame_id}: {len(faces)} faces, {len(bodies)} bodies, {len(tracking_result.detections)} detections")
            
        except Exception as e:
            logger.error(f"Error in complete frame processing for {frame_id}: {e}")
    
    async def _load_image(self, image_path: str) -> np.ndarray:
        def load_sync():
            image = cv2.imread(image_path)
            if image is None:
                return None
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, load_sync
        )
