from typing import Type, Any, Optional, List
from dataclasses import asdict
import uuid

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy import desc, inspect
from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Visitor, FaceEmbedding, VisitorSession, Composite


class AbstractRepository(ABC):
    @abstractmethod
    def add(self, entity: Any) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def get(self, entity_class: Type, entity_id: Any) -> Optional[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def list(self, entity_class: Type) -> List[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def get_by(self, entity_class: Type, **filters) -> Optional[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def list_by(self, entity_class: Type, **filters) -> List[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, entity: Any) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def get_recent(self, entity_class: Type, limit: int) -> List[Any]: 
        raise NotImplementedError
        
    @abstractmethod
    def merge(self, entity: Any) -> Any:
        raise NotImplementedError
        
    @abstractmethod
    def get_all_sorted(self, entity_class: Type, offset: int = 0) -> List[Any]: 
        raise NotImplementedError
    
    @abstractmethod
    def cascade_delete_visitor(self, visitor_id: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def persist_frame_batch(self, frame: Frame, bodies: List[Body], composites: List[Composite], detections: List[Detection]) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def cleanup_expired_visitors(self, visitor_ids: List[str]) -> None:
        raise NotImplementedError


class TrackingRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, entity: Any) -> Any:
        if getattr(entity, "id", None) in (None, ""):
            setattr(entity, "id", str(uuid.uuid4()))
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_class: Type, entity_id: str) -> Optional[Any]:
        entity = (
            self.session.query(entity_class)
            .filter_by(id=entity_id)
            .first()
        )
        if entity and entity_class == Visitor:
            self._ensure_visitor_events(entity)
        return entity

    def list(self, entity_class: Type) -> List[Any]:
        entities = self.session.query(entity_class).all()
        if entity_class == Visitor:
            for entity in entities:
                self._ensure_visitor_events(entity)
        return entities

    def get_by(self, entity_class: Type, **filters) -> Optional[Any]:
        """Get first entity matching the given filters."""
        entity = (
            self.session.query(entity_class)
            .filter_by(**filters)
            .first()
        )
        if entity and entity_class == Visitor:
            self._ensure_visitor_events(entity)
        return entity
    
    def list_by(self, entity_class: Type, **filters) -> List[Any]:
        """Get all entities matching the given filters."""
        entities = (
            self.session.query(entity_class)
            .filter_by(**filters)
            .all()
        )
        if entity_class == Visitor:
            for entity in entities:
                self._ensure_visitor_events(entity)
        return entities
    
    def delete(self, entity: Any) -> None:
        """Delete an entity from the database."""
        self.session.delete(entity)
        self.session.flush()
    
    def merge(self, entity: Any) -> Any:
        """Merge entity (insert if new, update if exists)."""
        if getattr(entity, "id", None) in (None, ""):
            setattr(entity, "id", str(uuid.uuid4()))
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def get_recent(self, entity_class: Type, limit: int) -> List[Any]:
        col = self._order_col(entity_class)
        return (
            self.session.query(entity_class)
            .order_by(desc(col))
            .limit(limit)
            .all()
        )

    def get_all_sorted(self, entity_class: Type, offset: int = 0) -> List[Any]:
        col = self._order_col(entity_class)
        return (
            self.session.query(entity_class)
            .order_by(desc(col))
            .offset(offset)
            .all()
        )
    
    def _order_col(self, cls: Type):
        cols = inspect(cls).c
        for name in ("captured_at", "pk"):
            if name in cols:
                return cols[name]
        raise ValueError(f"{cls} lacks captured_at and pk columns")
    
    def _ensure_visitor_events(self, visitor: Visitor) -> None:
        """Ensure visitor has events list initialized after loading from DB."""
        if not hasattr(visitor, 'events') or visitor.events is None:
            visitor.events = []
    
    def cascade_delete_visitor(self, visitor_id: str) -> None:
        """Handles all related data cleanup when removing a visitor"""
        detections = self.list_by(Detection, visitor_id=visitor_id)
        embedding_ids = {detection.embedding_id for detection in detections}
        
        for detection in detections:
            self.delete(detection)
        
        for embedding_id in embedding_ids:
            embedding = self.get(FaceEmbedding, embedding_id)
            if embedding:
                self.delete(embedding)
        
        active_session = self.get_by(VisitorSession, visitor_id=visitor_id, ended_at=None)
        if active_session:
            from the_judge.common.datetime_utils import now
            active_session.end("system_generated", now())
            self.merge(active_session)
        
        sessions = self.list_by(VisitorSession, visitor_id=visitor_id)
        for session in sessions:
            self.delete(session)
        
        visitor_entity = self.get(Visitor, visitor_id)
        if visitor_entity:
            self.delete(visitor_entity)
    
    def persist_frame_batch(self, frame: Frame, bodies: List[Body], composites: List[Composite], detections: List[Detection]) -> None:
        """Optimized batch persistence for frame processing"""
        self.add(frame)
        
        for body in bodies:
            self.add(body)
        
        for composite in composites:
            self.add(composite.embedding)
            self.add(composite.face)
        
        for detection in detections:
            self.add(detection)
    
    def cleanup_expired_visitors(self, visitor_ids: List[str]) -> None:
        """Batch cleanup of multiple expired visitors"""
        for visitor_id in visitor_ids:
            self.cascade_delete_visitor(visitor_id)