import asyncio
import cv2
import uuid
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List
from pathlib import Path

from the_judge.domain.tracking import Frame, Face, Body, Visitor, Composite, FaceMLProvider, BodyMLProvider, FrameProcessed, FrameSaved
from the_judge.application.messagebus import MessageBus
from the_judge.application.tracking_service import TrackingService
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger("FrameProcessingService")


class FrameProcessingService:
    def __init__(
        self,
        face_provider: FaceMLProvider,
        body_provider: BodyMLProvider,
        tracking_service: TrackingService,
        bus: MessageBus,
        uow_factory: Callable[[], AbstractUnitOfWork],
        max_workers: int = 4,
    ):
        self.face_provider = face_provider
        self.body_provider = body_provider
        self.tracking_service = tracking_service
        self.bus = bus
        self.uow_factory = uow_factory
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.visitors: list[Visitor] = []

    async def on_frame_saved(self, event: FrameSaved) -> None:
        image_path = (
            Path(get_settings().get_stream_path(event.frame.collection_id))
            / f"{event.frame.camera_name}.jpg"
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self.executor, self.process_frame, event.frame, str(image_path)
        )

    def process_frame(self, frame: Frame, image_path: str) -> None:
        try:
            image = self._load_image(image_path)
            if image is None:
                logger.error("Failed to load image %s", image_path)
                return

            composites, bodies = self._detect_objects(image, frame.id)

            with self.uow_factory() as uow:
                for composite in composites:
                    uow.repository.add(composite.embedding)  # Save embedding first
                    uow.repository.add(composite.face)       # Then face (which references embedding)

                for body in bodies:
                    uow.repository.add(body)

                #await self.tracking_service.handle_frame(uow, frame, composites, bodies)

                uow.commit()

            # self.bus.handle(
            #     FrameProcessed(
            #         frame=frame,
            #         faces=faces_and_embeddings,
            #         bodies=bodies
            #     )
            # )

            logger.info("Processed frame %s from collection %s: %d faces, %d bodies", frame.id, frame.collection_id, len(faces_and_embeddings), len(bodies))

        except Exception as exc:
            logger.exception("Error processing frame %s", frame.id)

    def _load_image(self, image_path: str):
        img = cv2.imread(image_path)
        return None if img is None else cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def _detect_objects(self, image: np.ndarray, frame_id: str) -> tuple[list[Composite], list[Body]]:
        face_detector = self.face_provider.get_face_detector()
        body_detector = self.body_provider.get_body_detector()
        
        faces = face_detector.detect_faces(image, frame_id)
        bodies = body_detector.detect_bodies(image, frame_id)

        return faces, bodies
