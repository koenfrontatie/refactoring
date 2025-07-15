import argparse
import asyncio
import base64
import platform
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import socketio

# ───────────────────────── configuration ───────────────────────── #

DEFAULT_PORT   = 8081
CAM_COUNT      = 1
RESOLUTION     = (1920, 1080)
HOST_TO_DISCOVER = "KVDWPC"

# ───────────────────────── dataclasses ────────────────────────── #

@dataclass(slots=True)
class CameraInfo:
    index: int
    width: int
    height: int
    capture: cv2.VideoCapture

# ───────────────────────── core client ────────────────────────── #

class RemoteCameraClient:
    """Async Socket‑IO camera client (single process, n cameras)."""

    def __init__(
        self,
        device_name: str,
        server_ip: str,
        *,
        cam_count: int = CAM_COUNT,
    ) -> None:
        self.device_name = device_name or platform.node()
        self.server_url  = f"http://{server_ip}:{DEFAULT_PORT}"
        self.cam_count   = cam_count
        self.cameras: Dict[int, CameraInfo] = {}

        self.sio = socketio.AsyncClient(reconnection=True, request_timeout=10)
        self._register_socket_handlers()

    # ───── Socket‑IO event handlers ───── #

    def _register_socket_handlers(self) -> None:

        @self.sio.event
        async def connect():
            print(f"[socket] connected → {self.server_url}")
            await self._register_cameras()

        @self.sio.event
        async def disconnect():
            print("[socket] disconnected")

        @self.sio.on("camera.capture_frames")
        async def _on_capture(payload: dict):
            await self._capture_all(payload.get("filename"))

    # ───── camera discovery / init ───── #

    def _discover_and_open(self) -> None:
        print("[init] enumerating cameras…")
        for idx in range(5):  # probe first 5 indices
            if len(self.cameras) >= self.cam_count:
                break
            cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
            if cap.isOpened():
                w, h = RESOLUTION
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.cameras[idx] = CameraInfo(idx, w, h, cap)
                print(f"  ✓ camera {idx} ready ({w}×{h})")

        if not self.cameras:
            raise RuntimeError("no working cameras found")

    # ───── registration ───── #

    async def _register_cameras(self) -> None:
        cam_ids = [f"{self.device_name}.{i+1}" for i in self.cameras]
        await self.sio.emit("camera.register",
                            {"device_name": self.device_name,
                             "camera_ids": cam_ids})
        print(f"[socket] sent camera.register → {cam_ids}")

    async def _unregister(self) -> None:
        await self.sio.emit("camera.unregister",
                            {"device_name": self.device_name})

    # ───── capture & push ───── #

    async def _capture_all(self, filename_stub: str | None) -> None:
        print("[capture] request received")
        await asyncio.gather(*(
            self._capture_one(cam, filename_stub, ordinal)
            for ordinal, cam in self.cameras.items()
        ))

    async def _capture_one(
        self,
        cam: CameraInfo,
        filename_stub: str | None,
        ordinal: int,
    ) -> None:
        ret, frame = cam.capture.read()
        if not ret:
            return print(f"  ✗ capture failed on {ordinal}")

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ok:
            return print(f"  ✗ encode failed on {ordinal}")

        await self.sio.emit("camera.frame", {
            "camera_id":  f"{self.device_name}.{ordinal+1}",
            "filename":   filename_stub,
            "frame_data": base64.b64encode(buf).decode(),
            "resolution": {"width": cam.width, "height": cam.height},
        })
        print(f"  → pushed frame from cam {ordinal+1}")

    # ───── lifecycle ───── #

    async def run(self) -> None:
        self._discover_and_open()
        try:
            await self.sio.connect(self.server_url)
            print("[run] started (Ctrl‑C to quit)")
            while True:
                await asyncio.sleep(30)   # simple keep‑alive
        except asyncio.CancelledError:
            pass
        finally:
            await self._unregister()
            await self.sio.disconnect()
            for cam in self.cameras.values():
                cam.capture.release()
            print("[shutdown] done")

# ───────────────────────── CLI entry‑point ───────────────────────── #

def _auto_server_ip() -> str:
    try:
        return socket.gethostbyname(HOST_TO_DISCOVER)
    except socket.gaierror:
        return "localhost"

def main() -> int:
    ap = argparse.ArgumentParser(description="Remote camera client")
    ap.add_argument("-d", "--device-name", default="")
    ap.add_argument("-s", "--server-ip", help="server IP (defaults to hostname lookup)")
    ns = ap.parse_args()

    client = RemoteCameraClient(
        device_name=ns.device_name or platform.node(),
        server_ip=ns.server_ip or _auto_server_ip(),
    )

    try:
        asyncio.run(client.run())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"fatal: {exc}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
