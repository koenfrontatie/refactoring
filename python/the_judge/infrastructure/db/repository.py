# infrastructure/db/repository.py
import abc
from sqlalchemy.orm import Session

from the_judge.domain.tracking.model import Frame


class AbstractRepository(abc.ABC):
    
    @abc.abstractmethod
    def add(self, frame: Frame) -> None:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    
    def __init__(self, session: Session):
        self.session = session
    
    def add(self, frame: Frame) -> None:
        self.session.add(frame)
