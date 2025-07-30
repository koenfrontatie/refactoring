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
        dirty_visitors = set()
        
        for composite in recognized_composites:
            if not composite.visitor:
                visitor = self.face_recognizer.match_against_collection(composite, collection)
                if not visitor:
                    visitor = self._create_new_visitor()
                composite.visitor = visitor
            
            is_new_collection = collection.add_visitor_composite(composite.visitor.id, composite)
            visitor_record = composite.visitor.record_detection(frame.collection_id, frame.id, is_new_collection)
            
            self.visitor_registry.add_visitor_with_composite(composite.visitor, composite)
            dirty_visitors.add(composite.visitor)
            
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

        expired_visitors, state_changed_visitors = self.handle_visitor_timeouts_without_persist()
        dirty_visitors.update(state_changed_visitors)

        self._persist_everything(uow, frame, bodies, recognized_composites, detections, dirty_visitors)
        self._cleanup_expired_visitors(uow, expired_visitors)
        self._publish_visitor_events(recognized_composites)
        self.bus.handle(FrameProcessed(frame.id, len(detections)))

    def _create_new_visitor(self) -> Visitor:
        visitor = Visitor.create_new(get_name())
        return visitor

    def _persist_everything(self, uow: AbstractUnitOfWork, frame: Frame, bodies: List[Body], 
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
            if visitor.current_session:
                uow.repository.merge(visitor.current_session)

    def _publish_visitor_events(self, composites: List[Composite]) -> None:
        for composite in composites:
            if composite.visitor:
                for event in composite.visitor.events:
                    self.bus.handle(event)
                composite.visitor.events.clear()

    def handle_visitor_timeouts_without_persist(self) -> tuple[List[Visitor], List[Visitor]]:
        return self.visitor_registry.update_all_states()

    def _cleanup_expired_visitors(self, uow: AbstractUnitOfWork, expired_visitors: List[Visitor]) -> None:
        for visitor in expired_visitors:
            self._cleanup_visitor_data(uow, visitor)

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
