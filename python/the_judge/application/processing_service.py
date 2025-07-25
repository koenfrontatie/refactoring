import asyncio
import cv2
import uuid
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List
from pathlib import Path

from the_judge.domain.tracking.model import Frame, Face, Body, Visitor, Composite
from the_judge.domain.tracking.ports import FaceDetectorPort, BodyDetectorPort
from the_judge.domain.tracking.events import FrameProcessed, FrameSaved
from the_judge.application.messagebus import MessageBus
from the_judge.application.tracking_service import TrackingService
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger("FrameProcessingService")


class FrameProcessingService:
    def __init__(
        self,
        face_detector: FaceDetectorPort,
        body_detector: BodyDetectorPort,
        tracking_service: TrackingService,
        bus: MessageBus,
        uow_factory: Callable[[], AbstractUnitOfWork],
        max_workers: int = 4,
    ):
        self.face_detector = face_detector
        self.body_detector = body_detector
        self.tracking_service = tracking_service
        self.bus = bus
        self.uow_factory = uow_factory
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.visitors: list[Visitor] = []
        self.settings = get_settings()
    
    async def on_frame_saved(self, event: FrameSaved) -> None:
        image_path = (
            Path(self.settings.get_stream_path(event.frame.collection_id))
            / f"{event.frame.camera_name}.jpg"
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self.executor, self.process_frame, event.frame, str(image_path)
        )

    def process_frame(self, frame: Frame, image_path: str) -> None:
        frame_id = frame.id
        collection_id = frame.collection_id
        
        try:
            image = self._load_image(image_path)
            if image is None:
                logger.error("Failed to load image %s", image_path)
                return

            composites, bodies = self._detect_objects(image, frame_id)

            with self.uow_factory() as uow:
                uow.repository.add(frame)
                self.tracking_service.handle_frame(uow, frame, composites, bodies)
                logger.info("Processed frame %s from collection %s: %d faces, %d bodies", frame_id, collection_id, len(composites), len(bodies))
                uow.commit()

        except Exception as exc:
            logger.exception("Error processing frame %s", frame_id)

    def _load_image(self, image_path: str):
        img = cv2.imread(image_path)
        return None if img is None else cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def _detect_objects(self, image: np.ndarray, frame_id: str) -> tuple[list[Composite], list[Body]]:
        faces = self.face_detector.detect_faces(image, frame_id)
        bodies = self.body_detector.detect_bodies(image, frame_id)

        return faces, bodies
