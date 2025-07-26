from typing import List, Optional, Tuple, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from randomname import get_name
import uuid

from the_judge.domain.tracking.ports import FaceBodyMatcherPort, FaceRecognizerPort
from the_judge.domain.tracking.model import Frame, Detection, Face, Body, FaceEmbedding, Composite, Visitor, VisitorState

from the_judge.infrastructure.tracking.face_body_matcher import FaceBodyMatcher
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now
from the_judge.settings import get_settings
logger = setup_logger("TrackingService")

@dataclass
class CollectionBuffer:
    collection_id: str
    composites_in_collection: List[Composite] = field(default_factory=list)

    def add_composite(self, composite: Composite):
        self.composites_in_collection.append(composite)
    
    def has_visitor(self, visitor_id: str) -> bool:
        return any(comp.visitor and comp.visitor.id == visitor_id 
                  for comp in self.composites_in_collection)
    
    def get_composites(self) -> List[Composite]:
        return self.composites_in_collection

    def clear(self):
        self.composites_in_collection.clear()

class TrackingService:
    def __init__(
        self,
        face_recognizer: FaceRecognizerPort,
        face_body_matcher: FaceBodyMatcherPort,
        uow_factory: Callable[[], AbstractUnitOfWork],
        bus: MessageBus
    ):
        self.uow_factory = uow_factory
        self.bus = bus
        self.face_body_matcher = face_body_matcher
        self.face_recognizer = face_recognizer

        self.cached_collection: Optional[CollectionBuffer] = None

    def handle_frame(self, uow: AbstractUnitOfWork, frame: Frame, composites: List[Composite], bodies: List[Body]) -> None:
        if self.cached_collection is None or self.cached_collection.collection_id != frame.collection_id:
            if self.cached_collection:
                self.cached_collection.clear()
            self.cached_collection = CollectionBuffer(frame.collection_id)

        matched_composites = self.face_body_matcher.match_faces_to_bodies(composites, bodies)
        recognized_composites = self.face_recognizer.recognize_faces(matched_composites)

        for composite in recognized_composites:
            if composite.visitor:
                existing_visitor = composite.visitor
                
                if not self.cached_collection.has_visitor(existing_visitor.id):
                    existing_visitor.seen_count += 1
                    existing_visitor.captured_at = now()
                    
                    if existing_visitor.should_be_promoted:
                        existing_visitor.state = VisitorState.ACTIVE
                    elif existing_visitor.is_missing:
                        existing_visitor.state = VisitorState.MISSING
                    
                    composite.visitor = existing_visitor
                    self.cached_collection.add_composite(composite)
                else:
                    existing_visitor.captured_at = now()
                
                uow.repository.add(existing_visitor)
                visitor = existing_visitor
            else:
                visitor = self._find_in_collection_or_create_visitor(composite, uow)
            
            detection = Detection(
                id=str(uuid.uuid4()),
                frame_id=frame.id,
                face_id=composite.face.id,
                embedding_id=composite.embedding.id,
                body_id=composite.body.id if composite.body else None,
                visitor_record=visitor.record(),
                captured_at=now()
            )
            
            # TO DO: implement max embeddings per visitor (keep best quality)
            for composite in recognized_composites:
                uow.repository.add(composite.embedding)
                uow.repository.add(composite.face)

            for body in bodies:
                uow.repository.add(body)

            uow.repository.add(detection)

    def _find_in_collection_or_create_visitor(self, composite: Composite, uow: AbstractUnitOfWork) -> Visitor:
        collection_composites = self.cached_collection.get_composites()
        
        if collection_composites:
            matched_visitor = self.face_recognizer.match_against_collection(composite, collection_composites)
            if matched_visitor:
                matched_visitor.captured_at = now()
                uow.repository.add(matched_visitor)
                return matched_visitor
        
        new_visitor = Visitor(
            id=str(uuid.uuid4()),
            name=f"{get_name()}",
            state=VisitorState.TEMPORARY,
            face_id=composite.face.id,
            body_id=composite.body.id if composite.body else None,
            seen_count=1,
            captured_at=now(),
            created_at=now()
        )
        
        composite.visitor = new_visitor
        self.cached_collection.add_composite(composite)
        uow.repository.add(new_visitor)
        return new_visitor


    