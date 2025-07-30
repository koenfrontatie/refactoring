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
        det_frame = DetectionFrame(
            id=frame.id,
            collection_id=frame.collection_id,
            camera_name=frame.camera_name,
            captured_at=frame.captured_at
        )

        collection = self.visitor_registry.get_or_create_collection(det_frame.collection_id)

        recognized_composites = self.face_recognizer.recognize_faces(unknown_composites)

        for composite in recognized_composites:
            if not composite.visitor:
                visitor = self.face_recognizer.match_against_collection(composite, collection)
                if not visitor:
                    visitor = self._create_new_visitor()
                composite.visitor = visitor
            
            is_new_collection = collection.mark_visitor_seen(composite.visitor.id)
            visitor_record = composite.visitor.record_detection(det_frame.collection_id, det_frame.id, is_new_collection)
            
            self.visitor_registry.add_visitor_with_composite(composite.visitor, composite)
            
            det_frame.add_detection(
                face_id=composite.face.id,
                embedding_id=composite.embedding.id,
                visitor_id=composite.visitor.id,
                visitor_record=visitor_record,
                body_id=composite.body.id if composite.body else None
            )

        self._persist_frame_and_visitors(uow, det_frame, bodies, recognized_composites)
        self._publish_events(det_frame)
        self.bus.handle(FrameProcessed(det_frame.id, len(det_frame.detections)))
        self.process_timeouts()

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

    def process_timeouts(self) -> None:
        expired_visitors = self.visitor_registry.update_all_states()
        
        with self.uow_factory() as uow:
            for visitor in self.visitor_registry.get_all_visitors():
                uow.repository.merge(visitor)
                if visitor.current_session:
                    uow.repository.merge(visitor.current_session)
            
            for expired_visitor in expired_visitors:
                for event in expired_visitor.events:
                    self.bus.handle(event)
                expired_visitor.events.clear()
            
            uow.commit()

    def cleanup_expired_visitors(self) -> int:
        expired_visitors = self.visitor_registry.update_all_states()
        
        with self.uow_factory() as uow:
            for visitor in expired_visitors:
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
            
            uow.commit()
        
        return len(expired_visitors)
