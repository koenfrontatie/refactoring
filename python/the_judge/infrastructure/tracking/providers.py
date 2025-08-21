import os
import sys
import contextlib
from io import StringIO
from pathlib import Path
from insightface.app import FaceAnalysis
from ultralytics import YOLO
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.ports import FaceMLProvider, BodyMLProvider

logger = setup_logger("Providers")

@contextlib.contextmanager
def suppress_stdout_stderr():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class InsightFaceProvider(FaceMLProvider):
    def __init__(self):
        cfg = get_settings()
        model_path = Path(cfg.model_path).resolve() / "insightface"
        model_path.mkdir(parents=True, exist_ok=True)

        with suppress_stdout_stderr():
            self.app = FaceAnalysis(
                providers=["CUDAExecutionProvider"],
                root=str(model_path),
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace initialized from %s", model_path)
    
    def get_face_model(self):
        return self.app


class YOLOProvider(BodyMLProvider):
    def __init__(self):
        cfg = get_settings()
        model_dir = Path(cfg.model_path).resolve() / "yolo"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "yolov8n.pt"

        if model_path.exists():
            self.model = YOLO(str(model_path))
            logger.info("YOLO model loaded from %s", model_path)
        else:
            self.model = YOLO("yolov8n.pt")
            self.model.save(str(model_path))
            logger.info("YOLO model downloaded and saved to %s", model_path)
            
        self.model.to("cuda")
        self.model.conf, self.model.iou, self.model.classes = 0.3, 0.5, [0]
    
    def get_body_model(self):
        return self.model