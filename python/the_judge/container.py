from the_judge.entrypoints.socket_client import SocketIOClient
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.tracking.frame_collector import FrameCollector
from the_judge.infrastructure.tracking.face_detector import FaceDetector
from the_judge.infrastructure.tracking.body_detector import BodyDetector
from the_judge.infrastructure.tracking.face_body_matcher import FaceBodyMatcher
from the_judge.infrastructure.tracking.face_recognizer import FaceRecognizer
from the_judge.application.processing_service import FrameProcessingService
from the_judge.application.messagebus import MessageBus
from the_judge.domain.events import FrameIngested, FrameAnalyzed
from the_judge.infrastructure.tracking.providers import InsightFaceProvider, YOLOProvider
from the_judge.settings import get_settings

class Runtime:

    def __init__(self, ws_client, frame_collector: FrameCollector, frame_processing_service: FrameProcessingService, bus: MessageBus):
        self.ws_client = ws_client
        self.frame_collector = frame_collector
        self.frame_processing_service = frame_processing_service
        self.bus = bus

    def shutdown(self):
        # Add any cleanup logic here if needed
        print("Runtime shutting down...")


def build_runtime() -> Runtime:
    print("Initializing database...")
    initialize_database()
    
    print("Starting ORM mappers...")
    from the_judge.infrastructure.db.orm import start_mappers
    start_mappers()
    
    print("Loading ML models...")
    InsightFaceProvider.get_instance()
    YOLOProvider.get_instance()
    print("ML models loaded successfully")
    
    # Create message bus
    print("Setting up message bus...")
    bus = MessageBus()
    
    # Initialize infrastructure adapters
    face_detector = FaceDetector()
    body_detector = BodyDetector()
    face_body_matcher = FaceBodyMatcher()
    face_recognizer = FaceRecognizer()
    
    # Initialize processing service with dependency injection
    processing_service = FrameProcessingService(
        face_detector=face_detector,
        body_detector=body_detector,
        face_body_matcher=face_body_matcher,
        face_recognizer=face_recognizer,
        bus=bus
    )
    
    bus.subscribe(FrameIngested, processing_service.handle_frame_ingested)
    
    frame_collector = FrameCollector(bus)
    
    ws_client = SocketIOClient(frame_collector)

    return Runtime(ws_client, frame_collector, processing_service, bus)
