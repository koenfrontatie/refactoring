#!/usr/bin/env python3
import asyncio
import argparse
import base64
import cv2
import socketio
import socket
import platform

# Configuration
SERVER_HOSTNAME = "KVDWPC"      # Hostname to look for
DEFAULT_SERVER_PORT = 8081      # Default socket port

class CameraClient:
    def __init__(self):
        self.camera_id = platform.node()
        self.cap = cv2.VideoCapture(0)  # Open default camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        self.sio = socketio.AsyncClient()
        self.server_url = self._find_server_ip()

        @self.sio.event
        async def connect():
            await self._register()

        @self.sio.on('camera.collect.frame')
        async def camera_collect_frame(payload):
            await self._on_collect(payload)

    def open(self) -> None:
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_id}")

    def read(self) -> bytes:
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read from {self.camera_id}")
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes()

    def close(self) -> None:
        self.cap.release()

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
            b64 = base64.b64encode(jpg).decode('utf-8')
            await self.sio.emit('camera.frame', {
                'collection_id': collection_id,
                'camera': self.camera_id,
                'b64': b64
            })
            print(f"[{self.camera_id}] Sent frame '{collection_id}'")
        except Exception as e:
            print(f"[{self.camera_id}] Error capturing frame: {e}")

    def _find_server_ip(self) -> str:
        try:
            server_ip = socket.gethostbyname(SERVER_HOSTNAME)
            print(f"Found {SERVER_HOSTNAME} at {server_ip}")
            return f"http://{server_ip}:{DEFAULT_SERVER_PORT}"
        except socket.gaierror:
            print(f"Could not resolve {SERVER_HOSTNAME}, using localhost")
            return "localhost"
    
    async def run(self):
        # open the camera once
        self.open()

        # connect & let the handlers take over
        await self.sio.connect(self.server_url)
        await self.sio.wait()

        # on shutdown
        self.close()

def main():
    parser = argparse.ArgumentParser(description="Simple USB Camera Client")
    parser.add_argument('--camera-id',    '-i', required=True,
                        help="Unique ID for this camera (e.g. 'usb1')")
    parser.add_argument('--device-index','-d', type=int, default=0,
                        help="OpenCV device index")
    parser.add_argument('--server-url',  '-s', default='http://localhost:8081',
                        help="Orchestrator URL")
    args = parser.parse_args()

    cam = CameraClient(args.camera_id, args.device_index, args.server_url)
    asyncio.run(cam.run())

if __name__ == '__main__':
    main()
