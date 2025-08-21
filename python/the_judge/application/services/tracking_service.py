from typing import List, Dict, Optional, Callable
from randomname import get_name
import uuid
import asyncio

from the_judge.domain.tracking.model import Visitor, Detection, VisitorState, Body, Frame, VisitorSession
from the_judge.application.dtos import Composite, VisitorCollection
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.application.services.collection_buffer import CollectionBuffer
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
        self.collection_buffer = CollectionBuffer()
        self._timeout_task = None
        self._running = False

    def handle_frame(
            self, uow: AbstractUnitOfWork, 
            frame: Frame, 
            paired_composites: List[Composite], 
            bodies: List[Body]) -> None:
        
        collection = self.collection_buffer.get_or_create_collection(frame.collection_id)

        # Ensure all composites have a (new) visitor
        recognized_composites = self.face_recognizer.recognize_faces(uow, paired_composites)
        self._handle_unmatched_composites(uow, recognized_composites, collection)

        dirty_visitors = {}  
        detections = []

        # Update state of detected visitors and create detections.
        for composite in recognized_composites:
            is_new_in_collection = self.collection_buffer.add_composite(composite)
            composite.visitor.mark_sighting(frame, is_new_in_collection)
            composite.visitor.update_state(frame.captured_at)
            detections.append(composite.visitor.create_detection(frame, composite.face, composite.embedding, composite.body))
            dirty_visitors[composite.visitor.id] = composite.visitor

        self._persist_data(uow, frame, bodies, recognized_composites, detections, dirty_visitors.values())

        self._publish_visitor_events(recognized_composites)
        
        self.bus.handle(FrameProcessed(frame.id, len(detections)))

    def _handle_unmatched_composites(
            self, 
            uow: AbstractUnitOfWork,
            composites: List[Composite], 
            collection: VisitorCollection) -> None:
        
        for composite in composites:
            # There may be matches with current collection buffer, either match or create a new visitor.
            if not composite.visitor:
                matched_visitor = self.face_recognizer.match_against_collection(composite, collection.composites)
                
                if matched_visitor:
                    visitor = uow.repository.get(Visitor, matched_visitor.id)
                else:
                    visitor = Visitor.create_new(get_name(), composite.face.captured_at)
                    
                composite.visitor = visitor

    def _persist_data(
            self, uow: AbstractUnitOfWork, frame: Frame, bodies: List[Body], 
            composites: List[Composite], detections: List[Detection], 
            dirty_visitors) -> None:

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

    def _cleanup_visitor(self, uow: AbstractUnitOfWork, visitor: Visitor) -> None:
        for event in visitor.events:
            self.bus.handle(event)
        visitor.events.clear()

        detections = uow.repository.list_by(Detection, visitor_id=visitor.id)
        embeddings = {d.embedding for d in detections}

        for detection in detections:
            uow.repository.delete(detection)
        for embedding in embeddings:
            uow.repository.delete(embedding)

        uow.repository.delete(visitor)

    def _handle_timeouts(self) -> None:
        with self.uow_factory() as uow:
            current_time = now()
            
            # Get visitors with active sessions 
            active_sessions = uow.repository.list_by(VisitorSession, ended_at=None)
            visitor_ids = [session.visitor_id for session in active_sessions]
            
            # Get the actual visitor objects
            active_visitors = []
            for visitor_id in visitor_ids:
                visitor = uow.repository.get(Visitor, visitor_id)
                if visitor:
                    active_visitors.append(visitor)
            
            # Let domain model handle state transitions
            for visitor in active_visitors:
                visitor.update_state(current_time)
                
                uow.repository.merge(visitor)
                if visitor.current_session:
                    uow.repository.merge(visitor.current_session)
                
                # Publish any domain events generated during state transition
                for event in visitor.events:
                    self.bus.handle(event)
                visitor.events.clear()
            
            # Now handle visitors that became expired during update_state
            expired_visitors = [v for v in active_visitors if v.state == VisitorState.EXPIRED]
            for visitor in expired_visitors:
                self._cleanup_visitor(uow, visitor)
            
            uow.commit()

    async def start_timeout_worker(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Starting timeout worker")
        self._timeout_task = asyncio.create_task(self._timeout_loop())

    async def stop_timeout_worker(self) -> None:
        self._running = False
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

    async def _timeout_loop(self) -> None:
        logger.info("Timeout worker loop started")
        while self._running:
            await asyncio.sleep(1)
            try:
                logger.debug("Running timeout check")
                self._handle_timeouts()
            except Exception as e:
                logger.error(f"Timeout worker error: {e}")