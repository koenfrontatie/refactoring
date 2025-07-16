# application/commands/capture_frame.py
from common import datetime_utils
from the_judge.application.services.camera_service import CameraService
from the_judge.common.logger import setup_logger

log = setup_logger("capture-frame")

async def capture_frames(camera_service: CameraService, filename: str | None = None) -> bool:
    """
    One function — no class — that:
      1. Generates a filename if none is provided.
      2. Asks the service to collect frames.
      3. Logs success/failure and returns True/False.
    """
    filename = filename or f"{datetime_utils.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    log.info("Capturing frames → %s", filename)

    try:
        results = await camera_service.collect_frames_from_all(filename)
        ok = results["success_count"] > 0
        log.info("✓ %s frames collected", results["success_count"]) if ok else \
            log.warning("✗ no frames collected")
        return ok
    except Exception as exc:
        log.exception("Capture failed: %s", exc)
        return False
