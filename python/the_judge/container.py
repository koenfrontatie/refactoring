# the_judge/container.py
from dataclasses import dataclass
from pathlib import Path

from the_judge.settings import get_settings
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.infrastructure.tracking.providers import InsightFaceProvider, YOLOProvider
from the_judge.infrastructure.tracking.frame_collector import FrameCollector
from the_judge.infrastructure.tracking.face_detector import FaceDetector
from the_judge.infrastructure.tracking.body_detector import BodyDetector
from the_judge.infrastructure.tracking.face_body_matcher import FaceBodyMatcher
from the_judge.infrastructure.tracking.face_recognizer import FaceRecognizer
from the_judge.application.processing_service import FrameProcessingService
from the_judge.application.messagebus import MessageBus
from the_judge.domain.events import FrameIngested
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
    cfg = get_settings()

    initialize_database()

    # ML providers
    face_model = InsightFaceProvider()
    body_model = YOLOProvider()

    # Message bus and UoW factory
    bus = MessageBus()
    uow_factory = SqlAlchemyUnitOfWork

    # Adapters
    face_detector = FaceDetector(
        insight_provider=face_model,
        det_thresh=0.5,
        min_area=2500,
        min_norm=15.0,
        max_yaw=45.0,
        max_pitch=30.0,
    )

    body_detector = BodyDetector(model=body_model)
    
    face_body_matcher = FaceBodyMatcher()
    
    face_recognizer = FaceRecognizer(
        uow_factory=uow_factory,
        model=face_model,
        threshold=cfg.face_recognition_threshold,
    )

    # Service
    processing_service = FrameProcessingService(
        face_detector,
        body_detector,
        face_body_matcher,
        face_recognizer,
        bus,
        uow_factory,
    )

    bus.subscribe(FrameIngested, processing_service.handle_frame)

    # Collector + socket
    frame_collector = FrameCollector(bus=bus, uow_factory=uow_factory)
    ws_client = SocketIOClient(
        frame_collector
    )

    return App(ws_client=ws_client, bus=bus)
