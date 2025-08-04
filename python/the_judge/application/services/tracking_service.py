from typing import List, Dict, Optional, Callable
from randomname import get_name
import uuid

from the_judge.domain.tracking.model import Visitor, Detection, Face, FaceEmbedding, Body, Composite, Frame, VisitorSession, VisitorCollection
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed, SessionStarted, SessionEnded, VisitorExpired, VisitorWentMissing, VisitorReturned, VisitorPromoted
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

        # Ensure all composites have a (new) visitor
        recognized_composites = self.face_recognizer.recognize_faces(uow, paired_composites)
        self._ensure_visitors_for(recognized_composites, frame, collection)

        dirty_visitors = {}  
        detections = []

        # Update state of detected visitors and create detections.
        for composite in recognized_composites:
            is_new_in_collection = self.visitor_registry.add_composite(composite)
            composite.visitor.mark_sighting(composite.face.captured_at, is_new_in_collection)
            composite.visitor.update_state(composite.face.captured_at)
            detections.append(composite.visitor.create_detection(frame, composite))
            dirty_visitors[composite.visitor.id] = composite.visitor

        self._persist_data(uow, frame, bodies, recognized_composites, detections, dirty_visitors.values())

        self._publish_visitor_events(recognized_composites)
        
        self.bus.handle(FrameProcessed(frame.id, len(detections)))

    def _ensure_visitors_for(self, composites: List[Composite], frame: Frame, collection: VisitorCollection) -> None:
        for composite in composites:
            # There may be matches with current collection buffer, either match or create a new visitor.
            if not composite.visitor:
                visitor = self.face_recognizer.match_against_collection(composite, collection.composites)
                
                if not visitor:
                    visitor = Visitor.create_new(get_name(), composite.face.captured_at)
                    visitor.current_session = VisitorSession.create_new(
                        visitor_id=visitor.id,
                        frame=frame,
                    )

                composite.visitor = visitor

    def _persist_data(
            self, uow: AbstractUnitOfWork, frame: Frame, bodies: List[Body], 
            composites: List[Composite], detections: List[Detection], 
            dirty_visitors: dict) -> None:

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
            if visitor.current_session:
                uow.repository.merge(visitor.current_session)

    def _publish_visitor_events(self, composites: List[Composite]) -> None:
        for composite in composites:
            if composite.visitor:
                for event in getattr(composite.visitor, 'events', []):
                    self.bus.handle(event)
                composite.visitor.events.clear()


    def handle_timeouts(self) -> None:
        """Check for expired and missing visitors and handle them separately."""
        with self.uow_factory() as uow:
            current_time = now()
            sessions = uow.repository.list_by(VisitorSession, ended_at=None)
            visitors: List[Visitor] = []
            for session in sessions:
                visitor = uow.repository.get(Visitor, session.visitor_id)
                if visitor:
                    visitor.current_session = session
                    visitor.update_state(current_time)
                    visitors.append(visitor)

            expired_visitors = [v for v in visitors if any(isinstance(e, VisitorExpired) for e in v.events)]
            missing_visitors = [v for v in visitors if any(isinstance(e, VisitorWentMissing) for e in v.events)]

            for visitor in missing_visitors:
                if visitor.current_session and visitor.current_session.is_active:
                    visitor.current_session.end(current_time)
                    uow.repository.merge(visitor.current_session)
                visitor.current_session = None
                uow.repository.merge(visitor)
                for event in visitor.events:
                    self.bus.handle(event)
                visitor.events.clear()

            self._cleanup_expired_visitors(uow, expired_visitors)
            uow.commit()

    def _cleanup_expired_visitors(self, uow: AbstractUnitOfWork, expired_visitors: List[Visitor]) -> None:
        for visitor in expired_visitors:
            self._cleanup_visitor_data(uow, visitor)

    def _cleanup_visitor_data(self, uow: AbstractUnitOfWork, visitor: Visitor) -> None:
        for event in visitor.events:
            self.bus.handle(event)
        visitor.events.clear()

        detections = uow.repository.list_by(Detection, visitor_id=visitor.id)
        embeddings = {d.embedding for d in detections}

        for detection in detections:
            uow.repository.delete(detection)
        for embedding in embeddings:
            uow.repository.delete(embedding)

        sessions = uow.repository.list_by(VisitorSession, visitor_id=visitor.id)
        for session in sessions:
            uow.repository.delete(session)

        visitor_entity = uow.repository.get(Visitor, visitor.id)
        if visitor_entity:
            uow.repository.delete(visitor_entity)