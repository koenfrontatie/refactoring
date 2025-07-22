from typing import Type, Any, Optional, List
from dataclasses import asdict
import uuid

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from the_judge.domain.tracking.ports import AbstractRepository
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


class TrackingRepository(AbstractRepository):
    
    def __init__(self, session: Session):
        self.session = session
    
    def add(self, entity: Any) -> Any:
        entity_dict = asdict(entity)
        
        if not entity_dict.get('id'):
            entity_dict['id'] = str(uuid.uuid4())
        
        domain_instance = type(entity)(**entity_dict)
        self.session.add(domain_instance)
        self.session.flush()
        
        return domain_instance
    
    def get(self, entity_class: Type, entity_id: str) -> Optional[Any]:
        return self.session.query(entity_class).filter_by(id=entity_id).first()
    
    def list(self, entity_class: Type) -> List[Any]:
        return self.session.query(entity_class).all()
