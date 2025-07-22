# application/unit_of_work.py
from abc import ABC, abstractmethod
from the_judge.domain.tracking.ports import AbstractRepository


class AbstractUnitOfWork(ABC):
    
    repository: AbstractRepository
    
    def __enter__(self) -> "AbstractUnitOfWork":
        return self
    
    def __exit__(self, *args):
        self.rollback()
    
    @abstractmethod
    def commit(self):
        raise NotImplementedError
    
    @abstractmethod
    def rollback(self):
        raise NotImplementedError
