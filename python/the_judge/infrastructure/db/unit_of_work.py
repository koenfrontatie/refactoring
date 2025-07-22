from __future__ import annotations
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from the_judge.infrastructure.db.repository import AbstractRepository, TrackingRepository
from the_judge.infrastructure.db.engine import get_session_factory


class AbstractUnitOfWork(ABC):
    repository: AbstractRepository

    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self.rollback()       
        self._session.close()     

    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory()

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session: Session = self._session_factory()
        self.repository = TrackingRepository(self._session)
        return super().__enter__()

    def __exit__(self, *args) -> None:
        super().__exit__(*args)
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
