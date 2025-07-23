import asyncio
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

from the_judge.domain.tracking.ports import FaceMLProvider

from the_judge.application.messagebus import MessageBus
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now
from the_judge.domain.tracking import Frame, Detection, Face, Body
from the_judge.domain.tracking import FaceBodyMatcherPort, FaceRecognizerPort
from the_judge.settings import get_settings
logger = setup_logger("TrackingService")

@dataclass
class CollectionBuffer:
    # this buffer resets / clears when a new collection id is detected in incoming frames
    collection_id: str
    frames: set[Frame] = field(default_factory=set)
    detections: set[Detection] = field(default_factory=set)

    def add_frame(self, frame: Frame):
        self.frames.add(frame)

    def add_detection(self, detection: Detection):
        self.detections.add(detection)

    def clear(self):
        self.frames.clear()
        self.detections.clear()

class TrackingService:
    def __init__(
        self,
        face_provider: FaceMLProvider,
        uow_factory: Callable[[], AbstractUnitOfWork],
        bus: MessageBus
    ):
        self.uow_factory = uow_factory
        self.bus = bus
        self.face_body_matcher = face_provider.get_face_body_matcher()
        self.face_recognizer = face_provider.get_face_recognizer()

        self.current_collection: Optional[CollectionBuffer] = None
    
    async def handle_frame_processed(self, event: FrameProcessed):        
        # Check if this is a new collection
        if self.current_collection is None or self.current_collection.collection_id != event.frame.collection_id:
            self.current_collection.clear()
            self.current_collection = CollectionBuffer(event.frame.collection_id)

        self.current_collection.add_frame(event.frame)  

        composites = self.face_body_matcher.match_faces_to_bodies(event.faces, event.bodies)

        # we need to create detections for these composites, but detections should be created only after recognition
        # we need to either identify composites to a visitor id or create a new visitor / visitor record
        matches_after_identification = self.perform_detection(composites)

        with self.uow_factory() as uow:
            # Get the face recognizer
            # Perform recognition
            result = await self.face_recognizer.recognize(event.faces) #faces: List[Face])
            # Handle the result
            await self.handle_recognition_result(result)
    
    '''
    id: str
    frame_id: str
    face_id: Optional[str]
    body_id: Optional[str]
    visitor_record: dict
    captured_at: datetime


            for face, body in matches:
            detection = Detection(
                frame_id=event.frame.id,
                face_id=face.id,
                body_id=body.id,
                visitor_record= None,
                captured_at=now()
            )
            self.current_collection.add_detection(detection)
    '''
    async def perform_detection(self, faces: List[Tuple[Face, Optional[Body]]]) -> List[Tuple[Face, Optional[Body], Optional[str]]]:
        if not faces:
            logger.warning("No faces to recognize")
            return []

        results = self.face_recognizer.recognize_faces(faces)
        # recognize faces should return 
        with self.uow_factory() as uow:
            for face_id, result in results.items():
                if result is None:
                    continue
                # Create detection or update existing one
                detection = Detection(
                    id=result['id'],
                    frame_id=result['frame_id'],
                    face_id=face_id,
                    body_id=result.get('body_id'),
                    visitor_record=result.get('visitor_record', {}),
                    captured_at=now()
                )
                uow.repository.add(detection)
            uow.commit()
        
        # Notify the bus about the processed frame
        self.bus.handle(FrameProcessed(frame=faces[0], faces=faces))