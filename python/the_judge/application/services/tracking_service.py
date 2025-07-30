from typing import List, Dict, Optional, Callable
from randomname import get_name
import uuid

from the_judge.domain.tracking.model import DetectionFrame, Visitor, Detection, Face, FaceEmbedding, Body, Composite, Frame
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

    def handle_frame(self, uow: AbstractUnitOfWork, frame: Frame, unknown_composites: List[Composite], bodies: List[Body]) -> None:
        collection = self.visitor_registry.get_or_create_collection(frame.collection_id)
        recognized_composites = self.face_recognizer.recognize_faces(unknown_composites)

        detections = []
        for composite in recognized_composites:
            if not composite.visitor:
                visitor = self.face_recognizer.match_against_collection(composite, collection)
                if not visitor:
                    visitor = self._create_new_visitor()
                composite.visitor = visitor
            
            is_new_collection = collection.mark_visitor_seen(composite.visitor.id)
            visitor_record = composite.visitor.record_detection(frame.collection_id, frame.id, is_new_collection)
            
            self.visitor_registry.add_visitor_with_composite(composite.visitor, composite)
            
            detection = Detection(
                id=str(uuid.uuid4()),
                frame_id=frame.id,
                face_id=composite.face.id,
                embedding_id=composite.embedding.id,
                visitor_id=composite.visitor.id,
                visitor_record=visitor_record,
                captured_at=now(),
                body_id=composite.body.id if composite.body else None
            )
            detections.append(detection)

        self._persist_frame_and_visitors(uow, frame, bodies, recognized_composites, detections)
        self._publish_events(recognized_composites)
        self.bus.handle(FrameProcessed(frame.id, len(detections)))
        self.handle_visitor_timeouts(uow)

    def _create_new_visitor(self) -> Visitor:
        visitor = Visitor.create_new(get_name())
        return visitor

    def _persist_frame_and_visitors(self, uow: AbstractUnitOfWork, frame: DetectionFrame, bodies: List[Body], composites: List[Composite]) -> None:
        uow.repository.add(frame)
        
        for body in bodies:
            uow.repository.add(body)
        
        for composite in composites:
            uow.repository.add(composite.embedding)
            uow.repository.add(composite.face)
            
            visitor = self.visitor_registry.get_visitor(composite.visitor.id)
            if visitor:
                uow.repository.merge(visitor)
                
                if visitor.current_session:
                    uow.repository.merge(visitor.current_session)
        
        for detection in frame.detections:
            uow.repository.add(detection)

    def _publish_events(self, frame: DetectionFrame) -> None:
        for visitor_id in frame.get_visitor_ids():
            visitor = self.visitor_registry.get_visitor(visitor_id)
            if visitor:
                for event in visitor.events:
                    self.bus.handle(event)
                visitor.events.clear()

        for event in frame.events:
            self.bus.handle(event)
        frame.events.clear()

    def handle_visitor_timeouts(self, uow: AbstractUnitOfWork) -> int:
        expired_visitors = self.visitor_registry.update_all_states()
        
        if not expired_visitors:
            return 0
            
        for visitor in expired_visitors:
            self._cleanup_visitor_data(uow, visitor)
        
        return len(expired_visitors)

    def _cleanup_visitor_data(self, uow: AbstractUnitOfWork, visitor: Visitor) -> None:
        for event in visitor.events:
            self.bus.handle(event)
        visitor.events.clear()
        
        detections = uow.repository.list_by(Detection, visitor_id=visitor.id)
        for detection in detections:
            uow.repository.delete(detection)
        
        if visitor.current_session:
            uow.repository.delete(visitor.current_session)
        
        visitor_entity = uow.repository.get(Visitor, visitor.id)
        if visitor_entity:
            uow.repository.delete(visitor_entity)
