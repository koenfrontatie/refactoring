from the_judge.common.logger import setup_logger
from the_judge.application.commands.capture import CaptureFrameCommand

logger = setup_logger('SocketHandlers')


class SocketHandlers:
    
    def __init__(self, capture_command: CaptureFrameCommand):
        self.capture_command = capture_command
    
    async def handle_camera_capture(self, payload=None):
        logger.info("Camera capture requested")
        result = await self.capture_command.execute()
        
        if result:
            logger.info(f"Frame capture result: {result}")
        else:
            logger.error("Frame capture failed")
