# infrastructure/network/handlers.py
from datetime import datetime
from the_judge.application.dtos import CameraFrameDTO
from the_judge.domain.tracking.control import Camera
import logging

log = logging.getLogger("ws.handlers")

def register(sio, capture_cmd, tracking_svc) -> None:
    @sio.on(Camera.CAPTURE_FRAMES)              # event *is* the command
    async def _capture(_msg: dict):        # payload may only carry filename
        ok = await capture_cmd.execute(filename=_msg.get("filename"))
        log.info("capture %s", "✓" if ok else "✗")

    @sio.on(Camera.FRAME_CAPTURED)
    async def _frame(msg: dict):
        dto = CameraFrameDTO(
            camera_id  = msg["camera_id"],
            filename   = msg.get("filename") or datetime.utcnow().isoformat(),
            frame_data = msg["frame_data"],
            width      = msg["resolution"]["width"],
            height     = msg["resolution"]["height"],
        )
        await tracking_svc.ingest_frame(dto)
