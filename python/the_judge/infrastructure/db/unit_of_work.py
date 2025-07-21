# infrastructure/db/unit_of_work.py
from typing import Type
from sqlalchemy.orm import sessionmaker, Session
from the_judge.application.unit_of_work import AbstractUnitOfWork
from the_judge.domain.tracking.repository import AbstractRepository
from the_judge.infrastructure.db.repository import SqlAlchemyRepository


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    
    def __init__(self, session_factory: sessionmaker = None, repository_class: Type[AbstractRepository] = SqlAlchemyRepository):
        if session_factory is None:
            from .engine import get_session_factory
            self.session_factory = get_session_factory()
        else:
            self.session_factory = session_factory
        self.repository_class = repository_class
    
    def __enter__(self):
        self.session: Session = self.session_factory()
        self.repository = self.repository_class(self.session)
        return super().__enter__()
    
    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()
    
    def commit(self):
        self.session.commit()
    
    def rollback(self):
        self.session.rollback()
