# infrastructure/db/unit_of_work.py
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from the_judge.infrastructure.db.repositories.tracking_repo import AbstractTrackingRepository, SqlAlchemyTrackingRepository


class AbstractUnitOfWork(abc.ABC):
    
    tracking: AbstractTrackingRepository
    
    def __enter__(self) -> "AbstractUnitOfWork":
        return self
    
    def __exit__(self, *args):
        self.rollback()
    
    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError
    
    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    
    def __init__(self, session_factory: sessionmaker = None):
        if session_factory is None:
            from .engine import get_session_factory
            self.session_factory = get_session_factory()
        else:
            self.session_factory = session_factory
    
    def __enter__(self):
        self.session: Session = self.session_factory()
        self.tracking = SqlAlchemyTrackingRepository(self.session)
        return super().__enter__()
    
    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()
    
    def commit(self):
        self.session.commit()
    
    def rollback(self):
        self.session.rollback()
