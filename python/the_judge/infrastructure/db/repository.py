# infrastructure/db/repository.py
import abc
from sqlalchemy.orm import Session

from the_judge.domain.tracking.model import Frame


class AbstractRepository(abc.ABC):
    """Abstract repository interface following Cosmic Python patterns."""
    
    @abc.abstractmethod
    def add_frame(self, frame: Frame) -> None:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """SQLAlchemy implementation of the repository."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_frame(self, frame: Frame) -> None:
        self.session.add(frame)
