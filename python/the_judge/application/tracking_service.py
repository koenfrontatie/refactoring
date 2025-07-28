from typing import List, Optional, Tuple, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from randomname import get_name
import uuid
from __future__ import annotations

from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.domain.tracking.model import Frame, Detection, Face, Body, FaceEmbedding, Composite, Visitor, VisitorState
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now
from the_judge.settings import get_settings

logger = setup_logger("TrackingService")


class TrackedVisitors:
    def __init__(self):
        self.latest_collection_id: Optional[str] = None
        self.visitors: Dict[str, Visitor] = {}

    def ingest_composites(self, composites: List[Composite], collection_id: str) -> None:
        for composite in composites:
            if composite.visitor.id not in self.visitors:
                # add new visitor to tracked visitors
                self.visitors[composite.visitor.id] = composite.visitor
            else:
                # update existing visitor
                self.update_tracked_visitor(composite.visitor, collection_id)
        
        self.latest_collection_id = collection_id
        self.update_states()


    def update_tracked_visitor(self, visitor: Visitor, collection_id: str) -> None:
        if collection_id != self.latest_collection_id:
            visitor.seen_count += 1

        visitor.face_id = visitor.face_id
        visitor.body_id = visitor.body_id
        visitor.captured_at = now()
        self.visitors[visitor.id] = visitor

    def update_states(self) -> None:
        """Update the state of all visitors based on their last seen time."""
        to_remove = []
        for id, visitor in enumerate(self.visitors):
            if visitor.should_be_promoted():
                visitor.state = VisitorState.ACTIVE
            if visitor.is_missing():
                visitor.state = VisitorState.MISSING
            if visitor.should_be_removed():
                to_remove.append(visitor.id)



'''
    id: str
    name: str
    state: VisitorState
    face_id: str
    body_id: str
    seen_count: int
    captured_at: datetime
    created_at: datetime
'''

@dataclass
class FrameCollection:
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
        uow_factory: Callable[[], AbstractUnitOfWork],
        bus: MessageBus
    ):
        self.uow_factory = uow_factory
        self.bus = bus
        self.face_recognizer = face_recognizer

        self.cached_collection: Optional[FrameCollection] = None

    def handle_frame(self, uow: AbstractUnitOfWork, frame: Frame, unknown_composites: List[Composite]) -> None:
        if self.cached_collection is None or self.cached_collection.collection_id != frame.collection_id:
            if self.cached_collection:
                self.cached_collection.clear()
            self.cached_collection = FrameCollection(frame.collection_id)

        recognized_composites = self.face_recognizer.recognize_faces(unknown_composites)

        for composite in recognized_composites:
            if not composite.visitor:    
                # do a second check against the current collection
                visitor = self._match_in_collection(composite)
                if not visitor:
                    visitor = self._update_composite_with_new_visitor(composite)

            self.cached_collection.add_composite(composite)
        


            '''
                detection = Detection(
                id=str(uuid.uuid4()),
                frame_id=frame.id,
                face_id=composite.face.id,
                embedding_id=composite.embedding.id,
                body_id=composite.body.id if composite.body else None,
                visitor_record=visitor.record(),
                captured_at=now()
            )'''
            
            # TO DO: implement max embeddings per visitor (keep best quality)
            for composite in recognized_composites:
                uow.repository.add(composite.embedding)
                uow.repository.add(composite.face)

            for body in bodies:
                uow.repository.add(body)

            uow.repository.add(detection)

    def _update_composite_with_new_visitor(self, composite: Composite, visitor: Visitor) -> Composite:
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
        return composite

    def _match_in_collection(self, composite: Composite) -> Optional[Visitor]:
        return self.face_recognizer.match_against_collection(composite, self.cached_collection.get_composites())


    