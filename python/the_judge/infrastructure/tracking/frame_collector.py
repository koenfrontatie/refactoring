import uuid, asyncio
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from the_judge.domain.tracking.model import Frame
from the_judge.domain.tracking.ports import FrameCollectorPort
from the_judge.domain.tracking.events import FrameSaved
from the_judge.application.messagebus import MessageBus
from the_judge.common.logger import setup_logger
from the_judge.settings import get_settings

logger = setup_logger("FrameCollector")

class FrameCollector(FrameCollectorPort):
    def __init__(
        self, 
        bus: MessageBus, 
        max_workers: int = 2
    ):
        self._cameras: set[str] = set()
        self.cfg = get_settings()
        self.bus = bus
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

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

        collection_dir = Path(self.cfg.get_stream_path(command.collection_id))
        collection_dir.mkdir(parents=True, exist_ok=True)
        filepath = collection_dir / f"{command.camera_name}.jpg"

        await asyncio.get_event_loop().run_in_executor(
            self.executor, filepath.write_bytes, command.frame_data
        )

        frame_id = str(uuid.uuid4())
        frame = Frame(
            id=frame_id,
            camera_name=command.camera_name,
            captured_at=datetime.now(),
            collection_id=command.collection_id,
        )
        
        event = FrameSaved(
            frame=frame
        )

        self.bus.handle(event)

        logger.info(
            f"Saved frame from {command.camera_name} to {filepath.absolute()}"
        )
