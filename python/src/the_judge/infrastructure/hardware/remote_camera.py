"""
Remote camera adapter for network-based cameras.
"""

import base64
import asyncio
from pathlib import Path
from typing import Optional, Dict

from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.entities import Camera
from the_judge.infrastructure.hardware.base import CameraAdapter

logger = setup_logger('RemoteCameraAdapter')


class RemoteCameraAdapter(CameraAdapter):
    """Remote camera adapter for network cameras based on judge-camera."""
    
    def __init__(self, camera: Camera, stream_dir: Path = Path("stream")):
        super().__init__(camera)
        self.stream_dir = stream_dir
        self.frames_received = 0
        self.registered_cameras: Dict[str, dict] = {}
        
    async def initialize(self) -> bool:
        """Initialize remote camera (just mark as active)."""
        logger.info(f"Remote camera {self.camera.name} ready")
        self.camera.activate()
        return True
    
    async def capture_frame(self, filename: str) -> Optional[Path]:
        """Remote cameras don't capture directly - frames come via network."""
        logger.warning("Remote camera capture_frame called - frames should come via network")
        return None
    
    def register_remote_camera(self, camera_id: str, device_name: str) -> bool:
        """Register a remote camera client."""
        try:
            self.registered_cameras[camera_id] = {
                'device_name': device_name,
                'is_active': True,
                'frames_received': 0
            }
            
            camera_dir = self.stream_dir / camera_id
            camera_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Registered remote camera: {camera_id} ({device_name})")
            return True
            
        except Exception as e:
            logger.error(f"Error registering remote camera {camera_id}: {e}")
            return False
    
    def unregister_remote_camera(self, camera_id: str) -> bool:
        """Unregister a remote camera client."""
        if camera_id in self.registered_cameras:
            self.registered_cameras[camera_id]['is_active'] = False
            logger.info(f"Unregistered remote camera: {camera_id}")
            return True
        return False
    
    def receive_frame(self, camera_id: str, frame_data_base64: str, filename: str) -> Optional[Path]:
        """Receive frame data from remote camera and save to file."""
        try:
            if camera_id not in self.registered_cameras:
                logger.warning(f"Received frame from unregistered camera: {camera_id}")
                return None
            
            if frame_data_base64.startswith('data:image/'):
                frame_data_base64 = frame_data_base64.split(',')[1]
            
            frame_bytes = base64.b64decode(frame_data_base64)
            
            camera_dir = self.stream_dir / camera_id
            camera_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = camera_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(frame_bytes)
                
            if filepath.exists():
                logger.info(f"Received frame from {camera_id}: {filename}")
                self.camera.update_activity()
                self.registered_cameras[camera_id]['frames_received'] += 1
                self.frames_received += 1
                return filepath
            else:
                logger.error(f"Failed to save received frame: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving received frame from {camera_id}: {e}")
            self.camera.mark_error()
            return None
    
    def request_frames_from_all(self, filename: str) -> list:
        """Request frames from all active remote cameras."""
        active_cameras = [
            camera_id for camera_id, info in self.registered_cameras.items() 
            if info['is_active']
        ]
        
        if active_cameras:
            logger.info(f"Requesting frames from {len(active_cameras)} remote cameras")
            return [{
                'filename': filename,
                'camera_ids': active_cameras
            }]
        
        return []
    
    def get_status(self) -> dict:
        """Get remote camera adapter status."""
        active_cameras = sum(1 for info in self.registered_cameras.values() if info['is_active'])
        
        return {
            'total_registered': len(self.registered_cameras),
            'active_cameras': active_cameras,
            'frames_received': self.frames_received,
            'cameras': [
                {
                    'camera_id': camera_id,
                    'device_name': info['device_name'],
                    'is_active': info['is_active'],
                    'frames_received': info['frames_received']
                }
                for camera_id, info in self.registered_cameras.items()
            ]
        }
    
    def shutdown(self):
        """Clean shutdown."""
        for camera_id in list(self.registered_cameras.keys()):
            self.unregister_remote_camera(camera_id)
        
        logger.info(f"Remote camera {self.camera.name} shutdown")
        self.camera.deactivate()
