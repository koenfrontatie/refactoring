import argparse
import asyncio
import base64
import platform
import socket
import sys
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import socketio

DEFAULT_PORT = 8081
CAM_COUNT = 1
RESOLUTION = (1920, 1080)
HOST_TO_DISCOVER = "KVDWPC"


class RemoteCameraClient:

    def __init__(self, device_name: str, server_ip: str, *, cam_count: int = CAM_COUNT):
        self.device_name = device_name or platform.node()
        self.server_url = f"http://{server_ip}:{DEFAULT_PORT}"
        self.cam_count = cam_count
        self.cameras: Dict[int, cv2.VideoCapture] = {}

        self.sio = socketio.AsyncClient(reconnection=True, request_timeout=10)
        self._register_socket_handlers()

    def _register_socket_handlers(self):
        
        @self.sio.event
        async def connect():
            print(f"[socket] connected → {self.server_url}")
            await self._register_cameras()

        @self.sio.event
        async def disconnect():
            print("[socket] disconnected")

        @self.sio.on("camera.capture_frames")
        async def on_capture_frames(data: dict):
            filename = data.get("filename")
            await self._capture_all_cameras(filename)

    def _discover_and_open_cameras(self):
        print("[init] discovering cameras...")
        
        for idx in range(5):
            if len(self.cameras) >= self.cam_count:
                break
                
            cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
            if cap.isOpened():
                w, h = RESOLUTION
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                
                actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                self.cameras[idx] = cap
                print(f"  ✓ camera {idx} ready ({actual_w}×{actual_h})")

        if not self.cameras:
            raise RuntimeError("no working cameras found")

    async def _register_cameras(self):
        for cam_idx in self.cameras.keys():
            camera_name = f"{self.device_name}.{cam_idx+1}"
            await self.sio.emit("camera.register", {
                "name": camera_name
            })
            print(f"[socket] registered camera: {camera_name}")

    async def _capture_all_cameras(self, filename: str):
        print(f"[capture] capturing frames: {filename}")
        
        tasks = []
        for cam_idx, capture in self.cameras.items():
            task = asyncio.create_task(self._capture_single_camera(cam_idx, capture, filename))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        print(f"[capture] completed: {filename}")

    async def _capture_single_camera(self, cam_idx: int, capture: cv2.VideoCapture, filename: str):
        try:
            ret, frame = capture.read()
            if not ret:
                print(f"  ✗ capture failed on camera {cam_idx}")
                return

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if not ok:
                print(f"  ✗ encode failed on camera {cam_idx}")
                return

            camera_id = f"{self.device_name}.{cam_idx+1}"
            await self.sio.emit("camera.frame", {
                "camera_id": camera_id,
                "filename": filename,
                "frame_data": base64.b64encode(buf).decode()
            })
            
            print(f"  → sent frame from camera {cam_idx+1}")
            
        except Exception as e:
            print(f"  ✗ error capturing camera {cam_idx}: {e}")

    async def run(self):
        self._discover_and_open_cameras()
        
        try:
            await self.sio.connect(self.server_url)
            print("[run] started (Ctrl-C to quit)")
            
            while True:
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def _shutdown(self):
        try:
            await self.sio.disconnect()
        except:
            pass
            
        for capture in self.cameras.values():
            capture.release()
            
        print("[shutdown] complete")


def _auto_discover_server_ip() -> str:
    try:
        return socket.gethostbyname(HOST_TO_DISCOVER)
    except socket.gaierror:
        return "localhost"


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote camera client")
    parser.add_argument("-d", "--device-name", default="", help="Device name")
    parser.add_argument("-s", "--server-ip", help="Server IP address")
    args = parser.parse_args()

    client = RemoteCameraClient(
        device_name=args.device_name or platform.node(),
        server_ip=args.server_ip or _auto_discover_server_ip()
    )

    try:
        asyncio.run(client.run())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
