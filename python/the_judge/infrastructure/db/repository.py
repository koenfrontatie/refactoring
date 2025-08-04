from typing import Type, Any, Optional, List
from datetime import datetime
import uuid

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy import desc, inspect, and_
from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Visitor, VisitorSession, VisitorState


class AbstractTrackingRepository(ABC):
    @abstractmethod
    def add(self, entity: Any) -> Any:
        raise NotImplementedError
    
    @abstractmethod
    def get(self, entity_class: Type, entity_id: str) -> Optional[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, entity: Any) -> None:
        raise NotImplementedError
        
    @abstractmethod
    def merge(self, entity: Any) -> Any:
        raise NotImplementedError
    
    @abstractmethod
    def list(self, entity_class: Type) -> List[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def list_by(self, entity_class: Type, **filters) -> List[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def get_by(self, entity_class: Type, **filters) -> Optional[Any]:
        raise NotImplementedError
    
    @abstractmethod
    def get_active_visitors(self) -> List[Visitor]:
        raise NotImplementedError
    
    @abstractmethod
    def get_expired_visitors(self, current_time: datetime) -> List[Visitor]:
        raise NotImplementedError
    
    @abstractmethod
    def get_visitor_detections(self, visitor_id: str) -> List[Detection]:
        raise NotImplementedError
    
    @abstractmethod
    def get_recent_frames(self, limit: int) -> List[Frame]:
        raise NotImplementedError


class TrackingRepository(AbstractTrackingRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, entity: Any) -> Any:
        if getattr(entity, "id", None) in (None, ""):
            setattr(entity, "id", str(uuid.uuid4()))
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_class: Type, entity_id: str) -> Optional[Any]:
        return (
            self.session.query(entity_class)
            .filter_by(id=entity_id)
            .first()
        )
    
    def delete(self, entity: Any) -> None:
        self.session.delete(entity)
        self.session.flush()
    
    def merge(self, entity: Any) -> Any:
        if getattr(entity, "id", None) in (None, ""):
            setattr(entity, "id", str(uuid.uuid4()))
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def list(self, entity_class: Type) -> List[Any]:
        return self.session.query(entity_class).all()
    
    def list_by(self, entity_class: Type, **filters) -> List[Any]:
        query = self.session.query(entity_class)
        for key, value in filters.items():
            query = query.filter(getattr(entity_class, key) == value)
        return query.all()
    
    def get_by(self, entity_class: Type, **filters) -> Optional[Any]:
        query = self.session.query(entity_class)
        for key, value in filters.items():
            query = query.filter(getattr(entity_class, key) == value)
        return query.first()

    def get_active_visitors(self) -> List[Visitor]:
        return (
            self.session.query(Visitor)
            .join(VisitorSession, and_(
                Visitor.id == VisitorSession.visitor_id,
                VisitorSession.ended_at == None
            ))
            .all()
        )
    
    def get_expired_visitors(self, current_time: datetime) -> List[Visitor]:
        cutoff = current_time - Visitor.REMOVE_AFTER
        return (
            self.session.query(Visitor)
            .filter(
                Visitor.state == VisitorState.TEMPORARY,
                Visitor.last_seen < cutoff
            )
            .all()
        )
    
    def get_visitor_detections(self, visitor_id: str) -> List[Detection]:
        return (
            self.session.query(Detection)
            .filter_by(visitor_id=visitor_id)
            .all()
        )
    
    def get_recent_frames(self, limit: int) -> List[Frame]:
        return (
            self.session.query(Frame)
            .order_by(desc(Frame.captured_at))
            .limit(limit)
            .all()
        )