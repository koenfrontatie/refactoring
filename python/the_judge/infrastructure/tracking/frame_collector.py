from domain.tracking.ports import FrameCollectorPort
from domain.tracking.model import Camera, Frame
from settings import get_settings
from pathlib import Path

class FrameCollectorAdapter(FrameCollectorPort):
    def __init__(self):
        self._cameras: set[str] = set()
        self.cfg = get_settings()

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
        
        collection_dir = Path(self.cfg.get_stream_path(command.collection_id))
        collection_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = collection_dir / f"{command.camera_name}.jpg"
        
        filepath.write_bytes(command.frame_data)  # ✅ Even simpler
        
        print(f"Saved frame from {command.camera_name} to {filepath.absolute()}")