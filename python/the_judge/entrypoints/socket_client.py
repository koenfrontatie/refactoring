# infrastructure/network/socket.py
import asyncio, logging, socketio

from the_judge.settings import get_settings
from the_judge.entrypoints.handlers import register as reg_handlers

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

    async def disconnect(self) -> None:
        """Disconnect from the socket server."""
        await self.sio.disconnect()

    def _install_basic_logs(self) -> None:
        """Attach Socket.IO lifecycle loggers."""
        sio = self.sio

        @sio.event         
        async def connect() -> None:
            log.info("SocketIO connected → %s", _URI)

        @sio.event         
        async def disconnect() -> None:
            log.warning("SocketIO disconnected")

        @sio.event         
        async def connect_error(err: Exception) -> None:
            log.error("SocketIO connection error → %s", err)
        
        @self.sio.event
        async def reconnect():
            print(f"[{self.device_id}] Reconnected, re-registering...")
            await self._register_client()

    
    async def _register_client(self):
        try:
            response = await self.call('register', {'clientType': 'python'})
            if response:
                log.info(f"Successfully registered: {response}")
            else:
                log.warning("Registration failed - no response received")       
        except Exception as e:
            log.error(f"Registration error: {e}")
