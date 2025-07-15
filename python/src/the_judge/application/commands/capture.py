from datetime import datetime, timezone
from the_judge.application.dtos import CaptureFrameDTO
from the_judge.common.logger import setup_logger
from the_judge.common.datetime_utils import now

logger = setup_logger("CaptureCommand")

async def handle_capture(dto: CaptureFrameDTO, camera_service) -> dict:
    filename = dto.filename or now().strftime("%Y.%m.%d-%H.%M.%S.jpg")
    logger.info("Requesting frames: %s", filename)
    return await camera_service.request_frames_from_all(filename)
