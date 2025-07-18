# infrastructure/network/socket.py
import asyncio, logging, socketio, uuid
from settings import get_settings
from entrypoints.handlers import register as reg_handlers

log = logging.getLogger("SocketIOClient")

_URI = get_settings().socket_url.replace("ws://", "http://").replace("wss://", "https://")

class SocketIOClient:
    def __init__(self, camera_service) -> None:
        self.sio = socketio.AsyncClient(reconnection=True)
        self._install_basic_logs()
        reg_handlers(self.sio, camera_service)

    async def connect(self) -> None:
        await self.sio.connect(_URI, transports=("websocket", "polling"))
        await self._register_client()
        await self.sio.wait()

    async def emit(self, event: str, data=None) -> None:
        await self.sio.emit(event, data)

    async def call(self, event: str, data=None, timeout=8):
        try:
            return await self.sio.call(event, data, timeout=timeout)
        except asyncio.TimeoutError:
            log.warning("ACK timeout for %s", event)

    def _install_basic_logs(self):
        s = self.sio
        s.event(lambda      : log.info("SocketIO connected  → %s", _URI))
        s.event(lambda      : log.warning("SocketIO disconnected"))
        s.event(lambda err  : log.error("SocketIO error      → %s", err))
        
        # Add catch-all event handler to see what events we're receiving
        @s.event
        def catch_all(event, *args):
            log.info(f"Received event: {event} with args: {args}")
    
    async def _register_client(self):
        try:
            response = await self.call('register', {'clientType': 'python'})
            if response:
                log.info(f"Successfully registered: {response}")
            else:
                log.warning("Registration failed - no response received")       
        except Exception as e:
            log.error(f"Registration error: {e}")
