import asyncio
import cv2
import uuid
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List
from pathlib import Path

from the_judge.domain.tracking.ports import (
    FaceDetectorPort,
    BodyDetectorPort,
    FaceBodyMatcherPort,
    FaceRecognizerPort,
)
from the_judge.domain.tracking.model import Detection
from the_judge.domain.events import FrameAnalyzed, FrameIngested
from the_judge.application.messagebus import MessageBus
from the_judge.infrastructure.db.unit_of_work import AbstractUnitOfWork
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger("FrameProcessingService")


class FrameProcessingService:
    def __init__(
        self,
        face_detector: FaceDetectorPort,
        body_detector: BodyDetectorPort,
        face_body_matcher: FaceBodyMatcherPort,
        face_recognizer: FaceRecognizerPort,
        bus: MessageBus,
        uow_factory: Callable[[], AbstractUnitOfWork],
        max_workers: int = 4,
    ):
        self.face_detector = face_detector
        self.body_detector = body_detector
        self.face_body_matcher = face_body_matcher
        self.face_recognizer = face_recognizer
        self.bus = bus
        self.uow_factory = uow_factory
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def handle_frame(self, event: FrameIngested) -> None:
        image_path = (
            Path(get_settings().get_stream_path(event.collection_id))
            / f"{event.frame_id}.jpg"
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self.executor, self.process_frame, event.frame_id, str(image_path)
        )

    def process_frame(self, frame_id: str, image_path: str) -> None:
        try:
            image = self._load_image(image_path)
            if image is None:
                logger.error("Failed to load image %s", image_path)
                return

            faces, bodies = self._detect_objects(image, frame_id)
            self._persist_faces_bodies(faces, bodies)

            self.bus.handle(
                FrameAnalyzed(
                    frame_id=frame_id,
                    faces_detected=len(faces),
                    bodies_detected=len(bodies),
                    analyzed_at=datetime.now(),
                )
            )

            if not faces:
                logger.info("No faces detected in frame %s", frame_id)
                return

            '''detections = self._build_detections(frame_id, faces, bodies)
            self._persist_detections(detections)

            logger.info(
                "Frame %s: %d faces, %d bodies, %d detections",
                frame_id,
                len(faces),
                len(bodies),
                len(detections),
            )'''
        except Exception as exc:
            logger.exception("Error processing frame %s: %s", frame_id, exc)

    def _load_image(self, image_path: str):
        img = cv2.imread(image_path)
        return None if img is None else cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def _detect_objects(self, image: np.ndarray, frame_id: str):
        faces = self.face_detector.detect_faces(image, frame_id)
        bodies = self.body_detector.detect_bodies(image, frame_id)
        return faces, bodies

    def _persist_faces_bodies(self, faces, bodies) -> None:
        with self.uow_factory() as uow:
            for obj in (*faces, *bodies):
                uow.repository.add(obj)
            uow.commit()

    def _build_detections(
        self, frame_id: str, faces, bodies
    ) -> List[Detection]:
        face_body_map = self.face_body_matcher.match_faces_to_bodies(
            faces, bodies
        )
        recognition = self.face_recognizer.recognize_faces(faces)
        now = datetime.now()
        detections: List[Detection] = []
        for face in faces:
            detections.append(
                Detection(
                    id=str(uuid.uuid4()),
                    frame_id=frame_id,
                    face_id=face.id,
                    body_id=face_body_map.get(face.id),
                    visitor_record=recognition.get(face.id, {}),
                    captured_at=now,
                )
            )
        return detections

    def _persist_detections(self, detections) -> None:
        with self.uow_factory() as uow:
            for det in detections:
                uow.repository.add(det)
            uow.commit()
