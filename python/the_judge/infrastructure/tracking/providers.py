from pathlib import Path
from insightface.app import FaceAnalysis
from ultralytics import YOLO
from the_judge.settings import get_settings
from the_judge.common.logger import setup_logger
from the_judge.domain.tracking.ports import FaceMLProvider, BodyMLProvider, FaceDetectorPort, FaceRecognizerPort, BodyDetectorPort
from the_judge.infrastructure.tracking.face_detector import InsightFaceDetector
from the_judge.infrastructure.tracking.face_recognizer import InsightFaceRecognizer
from the_judge.infrastructure import BodyDetector, FaceDetector, FaceRecognizer

logger = setup_logger("Providers")


class InsightFaceProvider(FaceMLProvider):
    def __init__(self):
        cfg = get_settings()
        model_path = Path(cfg.model_path).resolve() / "insightface"
        model_path.mkdir(parents=True, exist_ok=True)

        self.app = FaceAnalysis(
            providers=["CUDAExecutionProvider"],
            root=str(model_path),
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace initialized from %s", model_path)
        
        self._face_detector = FaceDetector(self.app)
        self._face_recognizer = FaceRecognizer(self.app)
    
    def get_face_detector(self) -> FaceDetectorPort:
        return self._face_detector
    
    def get_face_recognizer(self) -> FaceRecognizerPort:
        return self._face_recognizer


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
        
        self._body_detector = BodyDetector(self.model)
    
    def get_body_detector(self) -> BodyDetectorPort:
        return self._body_detector