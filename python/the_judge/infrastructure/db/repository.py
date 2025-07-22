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
    def get_recent(self, entity_class: Type, limit: int) -> List[Any]: ...
    @abstractmethod
    def get_all_sorted(self, entity_class: Type, offset: int = 0) -> List[Any]: ...


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
        return (
            self.session.query(entity_class)
            .filter_by(id=entity_id)
            .first()
        )

    def list(self, entity_class: Type) -> List[Any]:
        return self.session.query(entity_class).all()


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