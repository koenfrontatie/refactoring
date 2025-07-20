from enum import Enum

from pydantic import ValidationError

from the_judge.common.datetime_utils import now
from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.commands import StartCollectionCommand, IngestFrameCommand, RegisterCameraCommand, UnregisterCameraCommand
from the_judge.domain.tracking.ports import FrameCollectorPort

logger = setup_logger('SocketHandlers')

class Event(str, Enum):
    REGISTER = "camera.register"
    TRIGGER_COLLECTION = "camera.trigger_collection"
    UNREGISTER = "camera.unregister"
    FRAME = "camera.frame"
    COLLECT_FRAME = "camera.collect_frame"

def register(sio, frame_collector: FrameCollectorPort):
    
    # Inbound
    @sio.on(Event.REGISTER)
    async def register_camera(payload):
        try:
            command = RegisterCameraCommand.model_validate(payload)
        except ValidationError as e:
            logger.warning(f"Invalid registration payload: {e}")
            return
        logger.info(f"Registering camera: {command.camera_name}")
        await frame_collector.register_camera(command)

    @sio.on(Event.UNREGISTER)
    async def unregister_camera(payload):
        try:
            command = UnregisterCameraCommand.model_validate(payload)
        except ValidationError as e:
            logger.warning(f"Invalid unregistration payload: {e}")
            return
        logger.info(f"Unregistering camera: {command.camera_name}")
        await frame_collector.unregister_camera(command)

    @sio.on(Event.TRIGGER_COLLECTION)
    async def trigger_collection(payload):
        try:
            command = StartCollectionCommand(
                collection_id=now().strftime("%Y%m%d%H%M%S")
            )
        except ValidationError as e:
            logger.warning(f"Invalid trigger collection payload: {e}")
            return
        logger.info(f"Triggering collection with ID: {command.collection_id}")
        await send_collect_request(command)

    @sio.on(Event.FRAME)
    async def handle_camera_frame(payload):
        try:
            command = IngestFrameCommand.model_validate(payload)
        except ValidationError as e:
            logger.warning(f"Invalid frame payload: {e}")
            return
        logger.info(f"Processing frame for camera: {command.camera_name}")
        await frame_collector.ingest_frame(command)

    # Outbound
    async def send_collect_request(payload):
        try:
            command = StartCollectionCommand.model_validate(payload)
        except ValidationError as e:
            logger.warning(f"Invalid collect frame payload: {e}")
            return
        logger.info(f"Sending collect request: {command.collection_id}")
        await sio.emit(Event.COLLECT_FRAME, command.model_dump())