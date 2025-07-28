# the_judge/container.py
from dataclasses import dataclass

from the_judge.settings import get_settings
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.infrastructure.tracking.providers import InsightFaceProvider, YOLOProvider
from the_judge.infrastructure.tracking.face_detector import FaceDetector
from the_judge.infrastructure.tracking.face_recognizer import FaceRecognizer
from the_judge.infrastructure.tracking.body_detector import BodyDetector
from the_judge.infrastructure.tracking.face_body_matcher import FaceBodyMatcher
from the_judge.infrastructure.tracking.frame_collector import FrameCollector
from the_judge.application.processing_service import FrameProcessingService
from the_judge.application.tracking_service import TrackingService
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking.events import FrameSaved, FrameProcessed
from the_judge.entrypoints.socket_client import SocketIOClient


@dataclass
class App:
    ws_client: SocketIOClient
    bus: MessageBus

    async def start(self):
        await self.ws_client.connect()

    async def stop(self):
        await self.ws_client.disconnect()


def create_app() -> App:
    initialize_database()

    face_provider = InsightFaceProvider()
    body_provider = YOLOProvider()
    
    face_detector = FaceDetector(face_provider.get_face_model())
    body_detector = BodyDetector(body_provider.get_body_model())
    
    face_body_matcher = FaceBodyMatcher()
    
    bus = MessageBus()
    uow_factory = SqlAlchemyUnitOfWork
    
    face_recognizer = FaceRecognizer(
        face_provider.get_face_model(),
        uow_factory
    )
    
    tracking_service = TrackingService(
        face_recognizer=face_recognizer,
        uow_factory=uow_factory,
        bus=bus
    )

    processing_service = FrameProcessingService(
        face_detector=face_detector,
        body_detector=body_detector,
        face_body_matcher=face_body_matcher,
        tracking_service=tracking_service,
        bus=bus,
        uow_factory=uow_factory
    )
    
    frame_collector = FrameCollector(
        bus=bus
    )
    
    bus.subscribe(FrameSaved, processing_service.on_frame_saved)
    #bus.subscribe(FrameProcessed, tracking_service.handle_frame_processed)
    
    # Only the entrypoint at this level
    ws_client = SocketIOClient(frame_collector)
    
    return App(ws_client=ws_client, bus=bus)