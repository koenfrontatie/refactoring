from typing import List, Dict, Optional, Callable
from randomname import get_name
import uuid

from the_judge.domain.tracking.model import Visitor, Detection, Face, FaceEmbedding, Body, Composite, Frame, VisitorSession
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed, SessionStarted, SessionEnded
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
            self._update_visitor_for_detection(composite, frame.id, is_new_in_collection)
            dirty_visitors[composite.visitor.id] = composite.visitor

        # Update all visitor states based on time (also returns visitors that have timed out)
        expired_visitors, state_changed_visitors = self.visitor_registry.update_all_states()
        for visitor in state_changed_visitors:
            dirty_visitors[visitor.id] = visitor

        # Create detections with current visitor state
        detections = []
        for composite in recognized_composites:
            detection = self._create_detection(composite, frame)
            detections.append(detection)

        self._persist_data(uow, frame, bodies, recognized_composites, detections, dirty_visitors.values())
        self._cleanup_expired_visitors(uow, expired_visitors)
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
            self, composite: Composite, 
            frame_id: str, 
            is_new_in_collection: bool) -> None:
        
        visitor = composite.visitor
        visitor.last_seen = now()
        visitor.frame_count += 1
        
        if is_new_in_collection:
            visitor.seen_count += 1
            visitor._check_promotion()
        
        # Find active session directly through the repository
        with self.uow_factory() as uow:
            active_session = uow.repository.get_by(
                VisitorSession, 
                visitor_id=visitor.id, 
                ended_at=None
            )
            
            if not active_session:
                # Create a new session
                session_id = str(uuid.uuid4())
                new_session = VisitorSession(
                    id=session_id,
                    visitor_id=visitor.id,
                    start_frame_id=frame_id,
                    started_at=now(),
                    captured_at=now()
                )
                uow.repository.add(new_session)
                
                # Add event
                visitor.events.append(SessionStarted(
                    visitor_id=visitor.id,
                    session_id=session_id,
                    frame_id=frame_id
                ))
            else:
                # Update existing session
                active_session.add_frame()
                uow.repository.merge(active_session)
            
            uow.commit()

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

    def _persist_data(
            self, uow: AbstractUnitOfWork, frame: Frame, bodies: List[Body], 
            composites: List[Composite], detections: List[Detection], 
            dirty_visitors: set) -> None:
        
        uow.repository.add(frame)
        
        for body in bodies:
            uow.repository.add(body)
        
        for composite in composites:
            uow.repository.add(composite.embedding)
            uow.repository.add(composite.face)
        
        for detection in detections:
            uow.repository.add(detection)
        
        for visitor in dirty_visitors:
            uow.repository.merge(visitor)

    def _publish_visitor_events(self, composites: List[Composite]) -> None:
        for composite in composites:
            if composite.visitor:
                for event in composite.visitor.events:
                    self.bus.handle(event)
                composite.visitor.events.clear()

    def _cleanup_expired_visitors(self, uow: AbstractUnitOfWork, expired_visitors: List[Visitor]) -> None:
        for visitor in expired_visitors:
            self._cleanup_visitor_data(uow, visitor)

    def _cleanup_visitor_data(self, uow: AbstractUnitOfWork, visitor: Visitor) -> None:
        for event in visitor.events:
            self.bus.handle(event)
        visitor.events.clear()
        
        detections = uow.repository.list_by(Detection, visitor_id=visitor.id)
        embedding_ids = {detection.embedding_id for detection in detections}
        
        for detection in detections:
            uow.repository.delete(detection)
        
        for embedding_id in embedding_ids:
            embedding = uow.repository.get(FaceEmbedding, embedding_id)
            if embedding:
                uow.repository.delete(embedding)
        
        # End active session if exists
        active_session = uow.repository.get_by(VisitorSession, visitor_id=visitor.id, ended_at=None)
        if active_session:
            # End the session
            active_session.end("expired", now())
            uow.repository.merge(active_session)
            
            # Add SessionEnded event
            self.bus.handle(SessionEnded(
                visitor_id=visitor.id,
                session_id=active_session.id,
                reason="expired"
            ))
        
        # Delete all sessions for this visitor
        sessions = uow.repository.list_by(VisitorSession, visitor_id=visitor.id)
        for session in sessions:
            uow.repository.delete(session)
        
        visitor_entity = uow.repository.get(Visitor, visitor.id)
        if visitor_entity:
            uow.repository.delete(visitor_entity)
