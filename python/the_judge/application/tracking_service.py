import asyncio
from typing import List, Optional, Tuple, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime

from sympy import composite

from the_judge.domain.tracking import FaceMLProvider
from the_judge.domain.tracking.model import Frame, Detection, Face, Body, FaceEmbedding, Composite, Visitor, VisitorState
from the_judge.domain.tracking import FaceBodyMatcherPort, FaceRecognizerPort
from the_judge.infrastructure import FaceBodyMatcher
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.common.logger import setup_logger
import uuid
from the_judge.common.datetime_utils import now
from the_judge.settings import get_settings
logger = setup_logger("TrackingService")

@dataclass
class CollectionBuffer:
    # this buffer resets / clears when a new collection id is detected in incoming frames
    collection_id: str
    composites_in_collection: List[Composite] = field(default_factory=list)

    def add_composite(self, composite: Composite):
        self.composites_in_collection.append(composite)
    
    def has_visitor(self, visitor_id: str) -> bool:
        return any(comp.visitor and comp.visitor.id == visitor_id 
                  for comp in self.composites_in_collection)
    
    def get_composites_for_recognition(self) -> List[Composite]:
        return self.composites_in_collection

    def clear(self):
        self.composites_in_collection.clear()

class TrackingService:
    def __init__(
        self,
        face_provider: FaceMLProvider,
        face_body_matcher: FaceBodyMatcherPort,
        uow_factory: Callable[[], AbstractUnitOfWork],
        bus: MessageBus
    ):
        self.uow_factory = uow_factory
        self.bus = bus
        self.face_body_matcher = face_body_matcher
        self.face_recognizer = face_provider.get_face_recognizer()

        self.cached_collection: Optional[CollectionBuffer] = None

    async def handle_frame(self, uow: AbstractUnitOfWork, frame: Frame, composites: List[Composite], bodies: List[Body]) -> None:
        if self.cached_collection is None or self.cached_collection.collection_id != frame.collection_id:
            if self.cached_collection:
                self.cached_collection.clear()
            self.cached_collection = CollectionBuffer(frame.collection_id)

        # Step 1: Match faces to bodies
        matched_composites = self.face_body_matcher.match_faces_to_bodies(composites, bodies)

        # Step 2: Recognize faces against database (returns composites with visitor field populated)
        recognized_composites = self.face_recognizer.recognize_faces(matched_composites)

        # Step 3: Process each composite - update existing visitors or create new ones
        for composite in recognized_composites:
            visitor = None
            
            if composite.visitor:
                # Matched visitor found in database
                existing_visitor = composite.visitor
                
                # Check if we've already processed this visitor in current collection
                if not self.cached_collection.has_visitor(existing_visitor.id):
                    existing_visitor.seen_count += 1
                    existing_visitor.captured_at = now()
                    
                    # Update state based on business rules
                    if existing_visitor.should_be_promoted:
                        existing_visitor.state = VisitorState.ACTIVE
                    elif existing_visitor.is_missing:
                        existing_visitor.state = VisitorState.MISSING
                    
                    # Add to collection buffer to track we've seen them
                    composite.visitor = existing_visitor
                    self.cached_collection.add_composite(composite)
                    
                    # Update visitor in database
                    uow.repository.add(existing_visitor)
                else:
                    existing_visitor.captured_at = now()
                    uow.repository.add(existing_visitor)
                
                visitor = existing_visitor
            else:
                # No match found in database - check against visitors created in this collection
                visitor = await self._find_or_create_collection_visitor(composite, uow)
            
            # Step 4: Create detection for this visitor
            detection = Detection(
                id=str(uuid.uuid4()),
                frame_id=frame.id,
                face_id=composite.face.id,
                embedding_id=composite.embedding.id,
                body_id=composite.body.id if composite.body else None,
                visitor_record=visitor.record(),
                captured_at=now()
            )
            
            uow.repository.add(detection)

    async def _find_or_create_collection_visitor(self, composite: Composite, uow: AbstractUnitOfWork) -> Visitor:
        """Find existing visitor in collection or create new one using face recognition."""
        collection_composites = self.cached_collection.get_composites_for_recognition()
        
        if collection_composites:
            # Use face recognizer to check if current composite matches any collection visitors
            # No database queries needed - we already have complete composites!
            test_composites = [composite] + collection_composites
            recognized_composites = self.face_recognizer.recognize_faces(test_composites)
            
            # Check if the first composite (our current one) got matched to a collection visitor
            if recognized_composites[0].visitor:
                matched_visitor = recognized_composites[0].visitor
                # Make sure the matched visitor is actually from our collection
                if self.cached_collection.has_visitor(matched_visitor.id):
                    # Update the existing collection visitor
                    matched_visitor.captured_at = now()
                    uow.repository.add(matched_visitor)
                    return matched_visitor
        
        # No match found in collection - create new visitor
        new_visitor = Visitor(
            id=str(uuid.uuid4()),
            name=f"Visitor_{str(uuid.uuid4())[:8]}",
            state=VisitorState.TEMPORARY,
            face_id=composite.face.id,
            body_id=composite.body.id if composite.body else None,
            seen_count=1,
            captured_at=now(),
            created_at=now()
        )
        
        # Create composite with new visitor and add to collection buffer
        composite.visitor = new_visitor
        self.cached_collection.add_composite(composite)
        
        # Add new visitor to database
        uow.repository.add(new_visitor)
        return new_visitor


    