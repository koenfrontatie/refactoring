from typing import Type, Any, Optional, List
from dataclasses import asdict
import uuid

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy import desc, inspect
from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Visitor


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