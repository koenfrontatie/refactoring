from settings import get_settings
from entrypoints.socket_client import SocketIOClient
from infrastructure.tracking.frame_collector import FrameCollectorAdapter

class Runtime:

    def __init__(self, ws_client, frame_collector: FrameCollectorAdapter):
        self.ws_client = ws_client
        self.frame_collector = frame_collector

    def shutdown(self):
        self.frame_collector.shutdown_all()


def build_runtime() -> Runtime:
    
    frame_collector = FrameCollectorAdapter()

    ws_client = SocketIOClient(frame_collector)

    return Runtime(ws_client, frame_collector)
