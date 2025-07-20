# infrastructure/db/unit_of_work.py
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from the_judge.infrastructure.db.repository import AbstractRepository, SqlAlchemyRepository


class AbstractUnitOfWork(abc.ABC):
    """Abstract Unit of Work interface following Cosmic Python patterns."""
    
    # Repository instances
    frames: AbstractRepository
    
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
    """SQLAlchemy implementation of Unit of Work."""
    
    def __init__(self, session_factory: sessionmaker = None):
        if session_factory is None:
            # Default session factory - replace with your actual DB config
            from .engine import get_session_factory
            self.session_factory = get_session_factory()
        else:
            self.session_factory = session_factory
    
    def __enter__(self):
        self.session: Session = self.session_factory()
        # Initialize repository with current session
        self.frames = SqlAlchemyRepository(self.session)
        return super().__enter__()
    
    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()
    
    def commit(self):
        self.session.commit()
    
    def rollback(self):
        self.session.rollback()
