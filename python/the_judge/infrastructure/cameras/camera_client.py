#!/usr/bin/env python3
import asyncio
import argparse
import base64
import cv2
import socketio
import socket
import platform

# Configuration
SERVER_HOSTNAME = ""            # Empty string means use localhost
DEFAULT_SERVER_PORT = 8081      # Default socket port

class CameraClient:
    def __init__(self):
        self.camera_id = platform.node()
        self.camera = None
        self.sio = socketio.AsyncClient()
        self.server_url = self._find_server_ip()

        @self.sio.event
        async def connect():
            print(f"[{self.camera_id}] Connect event triggered")
            await self._register()

        @self.sio.on('camera.collect_frame')
        async def camera_collect_frame(payload):
            await self._on_collect(payload)

    def open(self) -> None:
        try:
            # Try to initialize with DirectShow backend first (Windows)
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            # If that fails, try the default backend
            if not self.camera.isOpened():
                self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                print("Failed to open camera with any backend")
                return False
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            print(f"Camera initialized")
            return True
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
    

    def read(self) -> bytes:
        for _ in range(2):  # Clear buffer
            ret, _ = self.camera.read()
            if not ret:
                break
        
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError(f"Failed to read from {self.camera_id}")
        
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes()

    def close(self) -> None:
        self.camera.release()

    async def _register(self):
        await self.sio.emit('camera.register', {
            'camera': self.camera_id,
            'action': 'register'
        })
        print(f"[{self.camera_id}] Registered")

    async def _on_collect(self, payload):
        collection_id = payload.get('collection_id')
        try:
            jpg = self.read()
            await self.sio.emit('camera.frame', {
                'collection_id': collection_id,
                'camera': self.camera_id,
                'bytes': jpg
            })
            print(f"[{self.camera_id}] Sent frame '{collection_id}'")
        except Exception as e:
            print(f"[{self.camera_id}] Error capturing frame: {e}")

    def _find_server_ip(self) -> str:
        if not SERVER_HOSTNAME:  # Empty string means use localhost
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
            await self.sio.wait()   # blocks until socket disconnect
        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print(f"Error during connection: {e}")
        finally:
            print("Cleaning up...")
            try:
                await self.sio.emit('camera.register', {
                    'camera': self.camera_id,
                    'action': 'unregister'
                })
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