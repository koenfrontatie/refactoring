from typing import Optional
from insightface.app import FaceAnalysis
from ultralytics import YOLO
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger

logger = setup_logger('DetectionProviders')

class InsightFaceProvider:
    _instance: Optional[FaceAnalysis] = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        try:
            cfg = get_settings()
            model_path = cfg.model_path / "insightface"
            
            face_app = FaceAnalysis(
                providers=['CPUExecutionProvider'],  # Can add GPU later
                root=str(model_path)
            )
            face_app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info(f"InsightFace initialized from {model_path}")
            return face_app
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            return None


class YOLOProvider:
    _instance: Optional[YOLO] = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls._initialize()
        return cls._instance
    
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
            
            model.conf = 0.5
            model.iou = 0.5
            model.classes = [0]  # Person class only
            
            logger.info("YOLO model initialized")
            return model
        except Exception as e:
            logger.error(f"Failed to initialize YOLO: {e}")
            return None
