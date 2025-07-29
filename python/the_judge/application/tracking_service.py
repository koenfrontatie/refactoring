from typing import List, Optional, Tuple, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from randomname import get_name

from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.domain.tracking.model import Frame, Detection, Face, Body, FaceEmbedding, Composite, Visitor, VisitorState, VisitorSession
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameProcessed
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now

logger = setup_logger("TrackingService")


class TrackedVisitors:
    def __init__(self):
        self.latest_collection_id: Optional[str] = None
        self.visitors: Dict[str, Visitor] = {}
        self.sessions: Dict[str, VisitorSession] = {}  # session_id -> session

    def ingest_composites(self, composites: List[Composite], collection_id: str, frame_id: str) -> None:
        is_new_collection = collection_id != self.latest_collection_id
        
        for composite in composites:
            visitor = composite.visitor
            if visitor.id not in self.visitors:
                # New visitor - first time seeing them
                visitor.seen_count = 1
                visitor.last_seen = now()
                # Start new session
                session = self._start_session(visitor.id, frame_id)
                visitor.current_session_id = session.id
                self.visitors[visitor.id] = visitor
            else:
                # Existing visitor - update based on collection
                if is_new_collection:
                    self.visitors[visitor.id].seen_count += 1
                
                self.visitors[visitor.id].last_seen = now()
                # Update existing session
                self._update_session(visitor.id, frame_id)
        
        if is_new_collection:
            self.latest_collection_id = collection_id
        
        self.update_states()

    def _start_session(self, visitor_id: str, frame_id: str) -> VisitorSession:
        """Start a new session for visitor."""
        session_start_time = now()
        session = VisitorSession(
            id=str(uuid.uuid4()),
            visitor_id=visitor_id,
            start_frame_id=frame_id,
            end_frame_id=None,
            started_at=session_start_time,
            ended_at=None,
            captured_at=session_start_time,
            frame_count=1
        )
        self.sessions[session.id] = session
        
        # Update visitor's session_started_at
        if visitor_id in self.visitors:
            self.visitors[visitor_id].session_started_at = session_start_time
            
        return session
    
    def _update_session(self, visitor_id: str, frame_id: str) -> None:
        """Update existing session for visitor."""
        visitor = self.visitors[visitor_id]
        if visitor.current_session_id and visitor.current_session_id in self.sessions:
            session = self.sessions[visitor.current_session_id]
            session.increment_frame_count()
            session.captured_at = now()

    def update_states(self) -> None:
        """Update the state of all visitors based on their last seen time and session timing."""
        current_time = now()
        to_remove = []
        
        for visitor_id, visitor in self.visitors.items():
            # Update visitor state using new clean logic
            visitor.update_state(current_time)
            
            # Handle timeout cleanup
            if visitor.should_be_removed:
                to_remove.append(visitor_id)
                # End session if active
                if visitor.current_session_id and visitor.current_session_id in self.sessions:
                    session = self.sessions[visitor.current_session_id]
                    if session.is_active:
                        session.end_session("timeout", current_time)
                continue
            
            # Handle missing visitors (end their sessions)
            if visitor.state == VisitorState.MISSING:
                if visitor.current_session_id and visitor.current_session_id in self.sessions:
                    session = self.sessions[visitor.current_session_id]
                    if session.is_active:
                        session.end_session("missing", current_time)
                        visitor.current_session_id = None
        
        # Remove expired temporary visitors
        for visitor_id in to_remove:
            self._cleanup_visitor(visitor_id)
    
    def _cleanup_visitor(self, visitor_id: str) -> None:
        """Clean up visitor and their associated session - mark for deletion."""
        visitor = self.visitors.get(visitor_id)
        if visitor and visitor.current_session_id:
            # End the session
            session = self.sessions.get(visitor.current_session_id)
            if session and session.is_active:
                session.end_session("cleanup", now())
        
        # Remove visitor from tracking (will be deleted from DB)
        if visitor_id in self.visitors:
            del self.visitors[visitor_id]
    
    def get_visitors_to_delete(self) -> List[str]:
        """Get list of visitor IDs that should be deleted from database."""
        to_delete = []
        for visitor_id, visitor in self.visitors.items():
            if visitor.should_be_removed:
                to_delete.append(visitor_id)
        return to_delete

    def get_visitor(self, visitor_id: str) -> Optional[Visitor]:
        return self.visitors.get(visitor_id)

    def get_session(self, session_id: str) -> Optional[VisitorSession]:
        return self.sessions.get(session_id)

    def get_all_visitors(self) -> List[Visitor]:
        return list(self.visitors.values())
    
    def get_all_sessions(self) -> List[VisitorSession]:
        return list(self.sessions.values())


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
        self.tracked_visitors = TrackedVisitors()

    def handle_frame(self, uow: AbstractUnitOfWork, frame: Frame, unknown_composites: List[Composite], bodies: List[Body]) -> None:
        # Ensure we have a collection buffer for this frame
        self._ensure_collection_buffer(frame.collection_id)

        # Recognize faces and enrich composites with visitor data
        recognized_composites = self.face_recognizer.recognize_faces(unknown_composites)

        # Process each composite
        processed_composites = []
        for composite in recognized_composites:
            if not composite.visitor:    
                # Try matching against current collection first
                visitor = self._match_in_collection(composite)
                if not visitor:
                    # Create new visitor
                    visitor = self._create_new_visitor(composite)
                composite.visitor = visitor

            # Only add to collection if not already there (prevent duplicates)
            if not self.cached_collection.has_visitor(composite.visitor.id):
                self.cached_collection.add_composite(composite)
                processed_composites.append(composite)

        # Update visitor tracking state
        if processed_composites:
            self.tracked_visitors.ingest_composites(processed_composites, frame.collection_id, frame.id)

        # Persist data
        self._persist_frame_data(uow, frame, processed_composites, bodies)

        # Publish events
        self.bus.handle(FrameProcessed(frame.id, len(processed_composites)))

    def _ensure_collection_buffer(self, collection_id: str) -> None:
        if self.cached_collection is None or self.cached_collection.collection_id != collection_id:
            if self.cached_collection:
                self.cached_collection.clear()
            self.cached_collection = FrameCollection(collection_id)

    def _match_in_collection(self, composite: Composite) -> Optional[Visitor]:
        """Try to match composite against visitors already seen in this collection."""
        collection_composites = self.cached_collection.get_composites()
        if collection_composites:
            return self.face_recognizer.match_against_collection(composite, collection_composites)
        return None

    def _create_new_visitor(self, composite: Composite) -> Visitor:
        """Create a new visitor for this composite."""
        return Visitor(
            id=str(uuid.uuid4()),
            name=get_name(),
            state=VisitorState.TEMPORARY,
            seen_count=0,  # Will be set to 1 by TrackedVisitors
            current_session_id=None,
            last_seen=now(),
            created_at=now()
        )

    def _persist_frame_data(self, uow: AbstractUnitOfWork, frame: Frame, composites: List[Composite], bodies: List[Body]) -> None:
        """Persist all frame-related data to database."""
        
        # Save frame
        uow.repository.add(frame)
        
        # Save bodies
        for body in bodies:
            uow.repository.add(body)
        
        # Save face data and create detections
        for composite in composites:
            # Save face embedding
            uow.repository.add(composite.embedding)
            
            # Save face
            uow.repository.add(composite.face)
            
            # Save/update visitor
            tracked_visitor = self.tracked_visitors.get_visitor(composite.visitor.id)
            if tracked_visitor:
                uow.repository.add(tracked_visitor)
                
                # Save/update session if exists
                if tracked_visitor.current_session_id:
                    session = self.tracked_visitors.get_session(tracked_visitor.current_session_id)
                    if session:
                        uow.repository.add(session)
            
            # Create detection linking everything together
            detection = Detection(
                id=str(uuid.uuid4()),
                frame_id=frame.id,
                face_id=composite.face.id,
                embedding_id=composite.embedding.id,
                body_id=composite.body.id if composite.body else None,
                visitor_id=composite.visitor.id,
                captured_at=now()
            )
            uow.repository.add(detection)

    def process_timeouts(self) -> None:
        """Process visitor timeouts and update states."""
        self.tracked_visitors.update_states()
        
        # Persist updated visitor states and ended sessions
        with self.uow_factory() as uow:
            # Save all active visitors
            for visitor in self.tracked_visitors.get_all_visitors():
                uow.repository.add(visitor)
            
            # Save all sessions (including newly ended ones)
            for session in self.tracked_visitors.get_all_sessions():
                uow.repository.add(session)
            
            uow.commit()
    
    def cleanup_expired_visitors(self) -> int:
        """Clean up expired temporary visitors - DELETE all their data from database."""
        # Get visitors to delete before cleanup
        visitors_to_delete = []
        for visitor_id, visitor in self.tracked_visitors.visitors.items():
            if visitor.should_be_removed:
                visitors_to_delete.append(visitor_id)
        
        if not visitors_to_delete:
            return 0
        
        # Delete all associated data from database
        with self.uow_factory() as uow:
            for visitor_id in visitors_to_delete:
                # Delete all detections for this visitor
                detections = uow.repository.list_by(Detection, visitor_id=visitor_id)
                for detection in detections:
                    uow.repository.delete(detection)
                
                # Get visitor to find session
                visitor = self.tracked_visitors.get_visitor(visitor_id)
                if visitor and visitor.current_session_id:
                    session = self.tracked_visitors.get_session(visitor.current_session_id)
                    if session:
                        uow.repository.delete(session)
                
                # Delete the visitor itself
                visitor_entity = uow.repository.get(Visitor, visitor_id)
                if visitor_entity:
                    uow.repository.delete(visitor_entity)
            
            uow.commit()
        
        # Now clean up from tracking (this removes from cache)
        self.tracked_visitors.update_states()
        
        return len(visitors_to_delete)
