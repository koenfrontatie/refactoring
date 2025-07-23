# the_judge/container.py
from dataclasses import dataclass

from the_judge.settings import get_settings
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.infrastructure.tracking.providers import InsightFaceProvider, YOLOProvider
from the_judge.infrastructure.tracking.frame_collector import FrameCollector
from the_judge.application.processing_service import FrameProcessingService
from the_judge.application.tracking_service import TrackingService
from the_judge.application.messagebus import MessageBus
from the_judge.domain.tracking import FrameSaved, FrameProcessed
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
    
    bus = MessageBus()
    uow_factory = SqlAlchemyUnitOfWork
    
    processing_service = FrameProcessingService(
        face_provider=face_provider,
        body_provider=body_provider,
        bus=bus,
        uow_factory=uow_factory
    )
    
    tracking_service = TrackingService(
        face_provider=face_provider,
        uow_factory=uow_factory,
        bus=bus
    )

    frame_collector = FrameCollector(
        bus=bus, 
        uow_factory=uow_factory
    )
    
    
    # Wire up the message bus
    bus.subscribe(FrameSaved, processing_service.on_frame_saved)
    bus.subscribe(FrameProcessed, tracking_service.handle_frame_processed)
    
    # Only the entrypoint at this level
    ws_client = SocketIOClient(frame_collector)
    
    return App(ws_client=ws_client, bus=bus)