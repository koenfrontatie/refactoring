import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from the_judge.domain.tracking.model import Frame
from the_judge.domain.tracking.ports import FrameCollectorPort
from the_judge.domain.events import FrameIngested
from the_judge.application.messagebus import MessageBus
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.common.logger import setup_logger
from the_judge.settings import get_settings

logger = setup_logger('FrameCollector')

class FrameCollector(FrameCollectorPort):
    def __init__(self, bus: MessageBus):
        self._cameras: set[str] = set()
        self.cfg = get_settings()
        self.uow = SqlAlchemyUnitOfWork()
        self.bus = bus
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def register_camera(self, command):
        self._cameras.add(command.camera_name)
        logger.info(f"Registered camera {command.camera_name}")

    async def unregister_camera(self, command):
        self._cameras.remove(command.camera_name)
        logger.info(f"Unregistered camera {command.camera_name}")

    async def ingest_frame(self, command):
        if command.camera_name not in self._cameras:
            logger.warning(f"Camera {command.camera_name} is not registered.")
            return
        
        if not command.frame_data:
            logger.warning(f"No frame data received from {command.camera_name}")
            return
        
        # Save file to disk
        collection_dir = Path(self.cfg.get_stream_path(command.collection_id))
        collection_dir.mkdir(parents=True, exist_ok=True)
        filepath = collection_dir / f"{command.camera_name}.jpg"
        
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            filepath.write_bytes,
            command.frame_data
        )
        
        # Save frame to database
        frame_id = None
        with self.uow as uow:
            frame = Frame(
                camera_name=command.camera_name,
                captured_at=datetime.now(),
                uuid=str(uuid.uuid4()),
                collection_id=command.collection_id
            )
            uow.tracking.add_frame(frame)
            uow.commit()
            frame_id = frame.id
        
        logger.info(f"Saved frame from {command.camera_name} to {filepath.absolute()} and database")
        
        # Raise FrameIngested event instead of direct service call
        if frame_id:
            event = FrameIngested(
                frame_id=frame_id,
                camera_name=command.camera_name,
                collection_id=command.collection_id,
                ingested_at=datetime.now()
            )
            self.bus.handle(event)