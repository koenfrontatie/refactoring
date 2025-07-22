from typing import Optional
from insightface.app import FaceAnalysis
from ultralytics import YOLO
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger('Providers')

class InsightFaceProvider:
    @classmethod
    def _initialize(cls):
        try:
            cfg = get_settings()
            model_path = cfg.model_path / "insightface"

            face_app = FaceAnalysis(
                providers=['CUDAExecutionProvider'],  
                root=str(model_path)
            )
            face_app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info(f"InsightFace initialized from {model_path}")
            return face_app
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            return None

class YOLOProvider:
    @classmethod
    def _initialize(cls):
        try:
            cfg = get_settings()
            model_path = cfg.model_path / "yolo" / "yolov8n.pt"
            
            if model_path.exists():
                model = YOLO(str(model_path))
            else:
                # Auto-download on first use
                model = YOLO('yolov8n.pt')
            
            model.to('cuda')
            model.conf = 0.3
            model.iou = 0.5
            model.classes = [0]  # Person class only
            
            logger.info("YOLO model initialized")
            return model
        except Exception as e:
            logger.error(f"Failed to initialize YOLO: {e}")
            return None
