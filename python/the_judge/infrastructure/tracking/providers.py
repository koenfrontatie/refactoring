# infrastructure/tracking/providers.py
from insightface.app import FaceAnalysis
from ultralytics import YOLO
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger("Providers")


class InsightFaceProvider:
    def __init__(self):
        cfg = get_settings()
        model_path = cfg.model_path / "insightface"

        self.app = FaceAnalysis(
            providers=["CUDAExecutionProvider"],
            root=str(model_path),
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace initialized from %s", model_path)


class YOLOProvider:
    def __init__(self):
        cfg = get_settings()
        model_path = cfg.model_path / "yolo" / "yolov8n.pt"

        self.model = YOLO(str(model_path)) if model_path.exists() else YOLO("yolov8n.pt")
        self.model.to("cuda")
        self.model.conf, self.model.iou, self.model.classes = 0.3, 0.5, [0]
        logger.info("YOLO model initialized")

