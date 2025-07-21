from typing import Dict, List, Callable, Type
from the_judge.domain.events import Event
from the_judge.common.logger import setup_logger

logger = setup_logger('MessageBus')

class MessageBus:
    
    def __init__(self):
        self._handlers: Dict[Type[Event], List[Callable]] = {}
    
    def handle(self, event: Event):
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        logger.info(f"Handling {event_type.__name__} with {len(handlers)} handlers")
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__} for {event_type.__name__}: {e}")
    
    def subscribe(self, event_type: Type[Event], handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type.__name__}")
