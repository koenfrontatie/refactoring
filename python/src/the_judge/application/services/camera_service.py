from typing import Dict, List
from pathlib import Path

from the_judge.common.logger import setup_logger
from the_judge.infrastructure.hardware.usb_camera import USBCameraAdapter
from the_judge.infrastructure.hardware.remote_camera import RemoteCameraAdapter

logger = setup_logger('CameraService')


class CameraService:
    
    def __init__(self):
        self.usb_cameras: List[USBCameraAdapter] = []
        self.remote_cameras: List[RemoteCameraAdapter] = []
        
    def add_usb_camera(self, camera_adapter: USBCameraAdapter):
        self.usb_cameras.append(camera_adapter)
        
    def add_remote_camera(self, camera_adapter: RemoteCameraAdapter):
        self.remote_cameras.append(camera_adapter)
        
    async def initialize_all(self) -> bool:
        success = True
        
        for camera in self.usb_cameras:
            if not await camera.initialize():
                success = False
                
        for camera in self.remote_cameras:
            if not await camera.initialize():
                success = False
                
        return success
    
    async def request_frames_from_all(self, filename: str) -> dict:
        results = {
            'filename': filename,
            'usb_captures': [],
            'remote_requests': []
        }
        
        for camera in self.usb_cameras:
            try:
                frame_path = await camera.capture_frame(filename)
                if frame_path:
                    results['usb_captures'].append({
                        'camera_id': camera.camera.id,
                        'path': str(frame_path),
                        'success': True
                    })
                else:
                    results['usb_captures'].append({
                        'camera_id': camera.camera.id,
                        'success': False
                    })
            except Exception as e:
                logger.error(f"USB camera {camera.camera.id} capture failed: {e}")
                results['usb_captures'].append({
                    'camera_id': camera.camera.id,
                    'success': False,
                    'error': str(e)
                })
        
        for camera in self.remote_cameras:
            try:
                request_data = camera.request_frames_from_all(filename)
                results['remote_requests'].extend(request_data)
            except Exception as e:
                logger.error(f"Remote camera {camera.camera.id} request failed: {e}")
        
        logger.info(f"Frame capture requested: {len(results['usb_captures'])} USB, {len(results['remote_requests'])} remote")
        return results
    
    def shutdown_all(self):
        for camera in self.usb_cameras:
            camera.shutdown()
        for camera in self.remote_cameras:
            camera.shutdown()
