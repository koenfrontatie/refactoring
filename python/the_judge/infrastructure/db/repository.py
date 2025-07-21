# infrastructure/db/repository.py
from typing import Type, Any, Optional, List
from sqlalchemy.orm import Session
from the_judge.domain.tracking.repository import AbstractRepository


class SqlAlchemyRepository(AbstractRepository):
    
    def __init__(self, session: Session):
        self.session = session
    
    def add(self, entity: Any) -> None:
        self.session.add(entity)
    
    def get(self, entity_class: Type, entity_id: Any) -> Optional[Any]:
        return self.session.query(entity_class).filter(entity_class.id == entity_id).first()
    
    def list(self, entity_class: Type) -> List[Any]:
        return self.session.query(entity_class).all()
