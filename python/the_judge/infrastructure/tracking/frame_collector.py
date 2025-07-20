import uuid
from datetime import datetime
from pathlib import Path

from the_judge.domain.tracking.model import Frame
from the_judge.domain.tracking.ports import FrameCollectorPort
from the_judge.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from the_judge.settings import get_settings

class FrameCollectorAdapter(FrameCollectorPort):
    def __init__(self):
        self._cameras: set[str] = set()
        self.cfg = get_settings()
        self.uow = SqlAlchemyUnitOfWork()

    async def register_camera(self, command):
        self._cameras.add(command.camera_name)
        print(f"Registered camera {command.camera_name}")

    async def unregister_camera(self, command):
        self._cameras.remove(command.camera_name)
        print(f"Unregistered camera {command.camera_name}")

    async def ingest_frame(self, command):
        if command.camera_name not in self._cameras:
            print(f"Camera {command.camera_name} is not registered.")
            return
        
        if not command.frame_data:
            print(f"No frame data received from {command.camera_name}")
            return
        
        # Save file to disk
        collection_dir = Path(self.cfg.get_stream_path(command.collection_id))
        collection_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = collection_dir / f"{command.camera_name}.jpg"
        filepath.write_bytes(command.frame_data)
        
        # Save to database using UoW pattern
        with self.uow as uow:
            frame = Frame(
                camera_name=command.camera_name,
                captured_at=datetime.now(),
                uuid=str(uuid.uuid4()),
                collection_id=command.collection_id
            )
            uow.frames.add(frame)
            uow.commit()
        
        print(f"Saved frame from {command.camera_name} to {filepath.absolute()} and database")