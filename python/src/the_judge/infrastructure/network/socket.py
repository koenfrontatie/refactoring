# infrastructure/network/ws_client.py
import asyncio, logging, socketio, uuid
from the_judge.settings import get_settings
from .handlers import register as reg_handlers

log = logging.getLogger("SocketIOClient")

_URI = get_settings().socket_url.replace("ws://", "http://").replace("wss://", "https://")

class SocketIOClient:
    def __init__(self, capture_cmd, tracking_svc) -> None:
        self._sio = socketio.AsyncClient(reconnection=True)
        self._install_basic_logs()
        reg_handlers(self._sio, capture_cmd, tracking_svc)

    async def start(self) -> None:                       # blocks forever
        await self._sio.connect(_URI, transports=("websocket", "polling"))
        await self._sio.wait()

    async def emit(self, event: str, data=None) -> None:
        await self._sio.emit(event, data)

    async def call(self, event: str, data=None, timeout=8):
        """Emit + wait for ack (returns None on timeout)."""
        try:
            return await self._sio.call(event, data, timeout=timeout)
        except asyncio.TimeoutError:
            log.warning("ACK timeout for %s", event)

    def _install_basic_logs(self):
        s = self._sio
        s.event(lambda      : log.info("SocketIO connected  → %s", _URI))
        s.event(lambda      : log.warning("SocketIO disconnected"))
        s.event(lambda err  : log.error("SocketIO error      → %s", err))
