# domain/tracking/repository.py
import abc
from typing import Type, Any, Optional, List


class AbstractRepository(abc.ABC):
    
    @abc.abstractmethod
    def add(self, entity: Any) -> None:
        raise NotImplementedError
    
    @abc.abstractmethod
    def get(self, entity_class: Type, entity_id: Any) -> Optional[Any]:
        raise NotImplementedError
    
    @abc.abstractmethod
    def list(self, entity_class: Type) -> List[Any]:
        raise NotImplementedError
