# infrastructure/db/repository.py
import abc
from sqlalchemy.orm import Session

from domain.tracking.model import Frame


class AbstractRepository(abc.ABC):
    """Abstract repository interface following Cosmic Python patterns."""
    
    @abc.abstractmethod
    def add(self, frame: Frame) -> None:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """SQLAlchemy implementation following Cosmic Python approach."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add(self, frame: Frame) -> None:
        """Add frame directly - SQLAlchemy handles the mapping."""
        self.session.add(frame)
