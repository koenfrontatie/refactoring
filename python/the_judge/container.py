from the_judge.entrypoints.socket_client import SocketIOClient
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.tracking.frame_collector import FrameCollectorAdapter
from the_judge.settings import get_settings

class Runtime:

    def __init__(self, ws_client, frame_collector: FrameCollectorAdapter):
        self.ws_client = ws_client
        self.frame_collector = frame_collector

    def shutdown(self):
        # Add any cleanup logic here if needed
        print("Runtime shutting down...")


def build_runtime() -> Runtime:
    # Initialize database on startup
    print("Initializing database...")
    initialize_database()
    
    frame_collector = FrameCollectorAdapter()

    ws_client = SocketIOClient(frame_collector)

    return Runtime(ws_client, frame_collector)
