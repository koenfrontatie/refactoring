from typing import List, Dict, Optional, Callable
from randomname import get_name
import uuid

from the_judge.domain.tracking.model import Visitor, Detection, Face, FaceEmbedding, Body, Composite, Frame, VisitorSession, VisitorState
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.application.services.visitor_registry import VisitorRegistry
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now

logger = setup_logger("TrackingService")


class TrackingService:
    def __init__(
        self,
        face_recognizer: FaceRecognizerPort,
        uow_factory: Callable[[], AbstractUnitOfWork],
        bus: MessageBus
    ):
        self.face_recognizer = face_recognizer
        self.uow_factory = uow_factory
        self.bus = bus
        self.visitor_registry = VisitorRegistry()

    def handle_frame(
            self, uow: AbstractUnitOfWork, 
            frame: Frame, 
            paired_composites: List[Composite], 
            bodies: List[Body]) -> None:
        
        collection = self.visitor_registry.get_or_create_collection(frame.collection_id)
        recognized_composites = self.face_recognizer.recognize_faces(paired_composites)

        dirty_visitors = {}  
        
        # Process each composite and update visitor state
        for composite in recognized_composites:
            self._ensure_composite_has_visitor(composite, collection)
            is_new_in_collection = self.visitor_registry.add_composite(composite)
            self._update_visitor_for_detection(uow, composite, frame.id, is_new_in_collection)
            dirty_visitors[composite.visitor.id] = composite.visitor

        # Update all visitor states based on time (also returns visitors that have timed out)
        expired_visitors, state_changed_visitors = self.visitor_registry.update_all_states()
        for visitor in state_changed_visitors:
            if visitor.state == VisitorState.MISSING:
                ended_session_id = visitor.end_current_session("went_missing")
                if ended_session_id:
                    active_session = uow.repository.get(VisitorSession, ended_session_id)
                    if active_session and active_session.is_active:
                        active_session.end("system_generated", now())
                        uow.repository.merge(active_session)
            dirty_visitors[visitor.id] = visitor

        # Create detections with current visitor state
        detections = []
        for composite in recognized_composites:
            detection = self._create_detection(composite, frame)
            detections.append(detection)

        # Persist frame processing results
        uow.repository.persist_frame_batch(frame, bodies, recognized_composites, detections)
        for visitor in dirty_visitors.values():
            uow.repository.merge(visitor)
        
        # Handle expired visitor cleanup
        for visitor in expired_visitors:
            for event in visitor.events:
                self.bus.handle(event)
            visitor.events.clear()
        
        if expired_visitors:
            visitor_ids = [visitor.id for visitor in expired_visitors]
            uow.repository.cleanup_expired_visitors(visitor_ids)
        
        self._publish_visitor_events(recognized_composites)
        self.bus.handle(FrameProcessed(frame.id, len(detections)))

    def _create_new_visitor(self) -> Visitor:
        visitor = Visitor.create_new(get_name())
        return visitor

    def _ensure_composite_has_visitor(self, composite: Composite, collection) -> None:
        if not composite.visitor:
            visitor = self.face_recognizer.match_against_collection(composite, collection.composites)
            if not visitor:
                visitor = self._create_new_visitor()
            composite.visitor = visitor

    def _update_visitor_for_detection(
            self, uow: AbstractUnitOfWork, 
            composite: Composite, 
            frame_id: str, 
            is_new_in_collection: bool) -> None:
        
        visitor = composite.visitor
        new_session = visitor.process_detection(frame_id, is_new_in_collection)
        
        if new_session:
            uow.repository.add(new_session)
        else:
            active_session = uow.repository.get_by(
                VisitorSession, 
                visitor_id=visitor.id, 
                ended_at=None
            )
            if active_session:
                active_session.add_frame()
                uow.repository.merge(active_session)
        
    def _create_detection(self, composite: Composite, frame: Frame) -> Detection:
        return Detection(
            id=str(uuid.uuid4()),
            frame_id=frame.id,
            face_id=composite.face.id,
            embedding_id=composite.embedding.id,
            visitor_id=composite.visitor.id,
            visitor_record=composite.visitor.record(),  
            captured_at=now(),
            body_id=composite.body.id if composite.body else None
        )

    def _publish_visitor_events(self, composites: List[Composite]) -> None:
        for composite in composites:
            if composite.visitor:
                for event in composite.visitor.events:
                    self.bus.handle(event)
                composite.visitor.events.clear()


