from the_judge.entrypoints.socket_client import SocketIOClient
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.tracking.frame_collector import FrameCollectorAdapter
from the_judge.infrastructure.tracking.face_detector import InsightFaceAdapter
from the_judge.infrastructure.tracking.body_detector import YoloBodyAdapter
from the_judge.infrastructure.tracking.matcher import GeometricMatcherAdapter
from the_judge.application.tracking_service import TrackingService
from the_judge.application.face_recognition_service import FaceRecognitionService
from the_judge.settings import get_settings

class Runtime:

    def __init__(self, ws_client, frame_collector: FrameCollectorAdapter, frame_processing_service: TrackingService):
        self.ws_client = ws_client
        self.frame_collector = frame_collector
        self.frame_processing_service = frame_processing_service

    def shutdown(self):
        # Add any cleanup logic here if needed
        print("Runtime shutting down...")


def build_runtime() -> Runtime:
    # Initialize database on startup
    print("Initializing database...")
    initialize_database()
    
    # Pre-load ML models for better startup performance
    print("Loading ML models...")
    from the_judge.infrastructure.tracking.providers import InsightFaceProvider, YOLOProvider
    InsightFaceProvider.get_instance()
    YOLOProvider.get_instance()
    print("ML models loaded successfully")
    
    # Initialize detection adapters
    face_detector = InsightFaceAdapter()
    body_detector = YoloBodyAdapter()
    face_body_matcher = GeometricMatcherAdapter()
    
    # Initialize services
    tracking_service = TrackingService(
        face_detector=face_detector,
        body_detector=body_detector, 
        face_body_matcher=face_body_matcher
    )
    
    frame_collector = FrameCollectorAdapter(tracking_service)

    ws_client = SocketIOClient(frame_collector)

    return Runtime(ws_client, frame_collector, tracking_service)
