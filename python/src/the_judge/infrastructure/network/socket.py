import socketio
import asyncio
from typing import Dict, Callable, Any

from the_judge.common.logger import setup_logger

logger = setup_logger('SocketClient')


class SocketIOClient:
    
    def __init__(self, uri: str):
        self.uri = uri
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.handlers: Dict[str, Callable] = {}
        self.is_connected = False
        
        self._setup_connection_handlers()
    
    def _setup_connection_handlers(self):
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('connect_error', self._on_connect_error)
    
    async def _on_connect(self):
        logger.info(f"Connected to {self.uri}")
        self.is_connected = True
        await self.sio.emit('register', {'clientType': 'python'})
    
    async def _on_disconnect(self):
        logger.info("Disconnected")
        self.is_connected = False
    
    async def _on_connect_error(self, error):
        logger.error(f"Connection error: {error}")
    
    def register_handler(self, event_name: str, handler: Callable):
        self.handlers[event_name] = handler
        self.sio.on(event_name, handler)
        logger.debug(f"Registered handler for {event_name}")
    
    async def connect(self):
        logger.info(f"Connecting to {self.uri}")
        await self.sio.connect(self.uri, transports=['websocket', 'polling'])
        
        while self.is_connected:
            await asyncio.sleep(5)
    
    async def emit(self, event_name: str, data: Any = None):
        if self.is_connected:
            await self.sio.emit(event_name, data)
