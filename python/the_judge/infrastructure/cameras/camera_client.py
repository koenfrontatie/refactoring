#!/usr/bin/env python3
import asyncio
import cv2
import socketio
import socket
import platform
from camera import Camera

SERVER_HOSTNAME = ""            
DEFAULT_SERVER_PORT = 8081      

class CameraClient:
    def __init__(self):
        self.device_id = platform.node()
        self.camera = None
        self.sio = socketio.AsyncClient()
        self.server_url = self._find_server_ip()

        @self.sio.event
        async def connect():
            print(f"[{self.device_id}] Connect event triggered")
            await self._register()
        
        @self.sio.event  
        async def reconnect():
            print(f"[{self.device_id}] Reconnected, re-registering...")
            await self._register()
            
        @self.sio.on('camera.collect_frame')
        async def camera_collect_frame(payload):
            await self._on_collect(payload)

    def open(self) -> bool:
        try:
            self.camera = Camera(device=0, width=1920, height=1080)
            self.camera.start()
            print(f"Camera initialized")
            return True
        except RuntimeError as e:
            print(f"Failed to open camera: {e}")
            return False
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False

    def read(self) -> bytes:
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError(f"Failed to read from {self.device_id}")
        
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes()

    def close(self) -> None:
        if self.camera:
            self.camera.stop()

    async def _register(self):
        await self.sio.emit('camera.register', {
            'camera_name': self.device_id,
        })
        print(f"[{self.device_id}] Registered")

    async def _unregister(self):
        await self.sio.emit('camera.unregister', {
            'camera_name': self.device_id,
        })
        print(f"[{self.device_id}] Unregistered")

    async def _on_collect(self, payload):
        collection_id = payload.get('collection_id')
        try:
            jpg = self.read()
            await self.sio.emit('camera.frame', {
                'collection_id': collection_id,
                'camera_name': self.device_id,
                'frame_data': jpg
            })
            print(f"[{self.device_id}] Sent frame '{collection_id}'")
        except Exception as e:
            print(f"[{self.device_id}] Error capturing frame: {e}")

    def _find_server_ip(self) -> str:
        if not SERVER_HOSTNAME:  
            print("Using localhost")
            return f"http://localhost:{DEFAULT_SERVER_PORT}"
            
        try:
            server_ip = socket.gethostbyname(SERVER_HOSTNAME)
            print(f"Found {SERVER_HOSTNAME} at {server_ip}")
            return f"http://{server_ip}:{DEFAULT_SERVER_PORT}"
        except socket.gaierror:
            print(f"Could not resolve {SERVER_HOSTNAME}, using localhost")
            return f"http://localhost:{DEFAULT_SERVER_PORT}"
    
    async def run(self):
        if not self.open():
            print("Failed to initialize camera")
            return

        try:
            print(f"Connecting to {self.server_url}...")
            await self.sio.connect(self.server_url)
            print("Connected successfully")
            await self.sio.wait()
        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print(f"Error during connection: {e}")
        finally:
            print("Cleaning up...")
            try:
                await self._unregister()
                await self.sio.disconnect()
            except Exception as e:
                print(f"Cleanup error: {e}")
            self.close()
            print("Camera client stopped")

def main():
    cam = CameraClient()
    asyncio.run(cam.run())

if __name__ == '__main__':
    main()