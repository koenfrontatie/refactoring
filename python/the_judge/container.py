# the_judge/container.py
from dataclasses import dataclass

from the_judge.settings import get_settings
from the_judge.infrastructure.db.engine import initialize_database
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.infrastructure.tracking.providers import InsightFaceProvider, YOLOProvider
from the_judge.infrastructure.tracking.frame_collector import FrameCollector
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
    initialize_database()

    # Only create the HEAVY things that are expensive
    face_provider = InsightFaceProvider()
    body_provider = YOLOProvider()
    
    # Create lightweight infrastructure
    bus = MessageBus()
    uow_factory = SqlAlchemyUnitOfWork
    
    # Services self-initialize with their adapters
    processing_service = FrameProcessingService(
        face_provider=face_provider,
        body_provider=body_provider,
        bus=bus,
        uow_factory=uow_factory
    )
    
    frame_collector = FrameCollector(
        bus=bus, 
        uow_factory=uow_factory
    )
    
    # Wire up the message bus
    bus.subscribe(FrameIngested, processing_service.handle_frame)
    
    # Only the entrypoint at this level
    ws_client = SocketIOClient(frame_collector)
    
    return App(ws_client=ws_client, bus=bus)
