from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session
from the_judge.infrastructure.db.repository import TrackingRepository
from the_judge.infrastructure.db.engine import get_session_factory
from the_judge.domain.tracking.ports import AbstractRepository   


class AbstractUnitOfWork(ABC, AbstractContextManager):
    repository: AbstractRepository

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type:
            self.rollback()      
        else:
            self.commit()        
        self._session.close()
        return False             

    def commit(self) -> None:
        self._commit()

    def rollback(self) -> None:
        self._rollback()

    @abstractmethod
    def _commit(self) -> None: ...
    @abstractmethod
    def _rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory()

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session: Session = self._session_factory()
        self.repository = TrackingRepository(self._session)   
        return self

    def _commit(self) -> None:
        self._session.commit()

    def _rollback(self) -> None:
        self._session.rollback()
