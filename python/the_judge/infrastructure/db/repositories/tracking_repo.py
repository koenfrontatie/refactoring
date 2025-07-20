import abc
from typing import Optional, List
from sqlalchemy.orm import Session

from the_judge.domain.tracking.model import Frame, Face, Body, Detection, Collection


class AbstractTrackingRepository(abc.ABC):
    
    @abc.abstractmethod
    def add_frame(self, frame: Frame) -> None:
        raise NotImplementedError
    
    @abc.abstractmethod
    def add_face(self, face: Face) -> None:
        raise NotImplementedError
        
    @abc.abstractmethod
    def add_body(self, body: Body) -> None:
        raise NotImplementedError
        
    @abc.abstractmethod
    def add_detection(self, detection: Detection) -> None:
        raise NotImplementedError
        
    @abc.abstractmethod
    def add_collection(self, collection: Collection) -> None:
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_frame(self, frame_id: int) -> Optional[Frame]:
        raise NotImplementedError
        
    @abc.abstractmethod
    def get_collection(self, collection_id: int) -> Optional[Collection]:
        raise NotImplementedError
        
    @abc.abstractmethod
    def get_collection_by_uuid(self, uuid: str) -> Optional[Collection]:
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_faces_for_frame(self, frame_id: int) -> List[Face]:
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_bodies_for_frame(self, frame_id: int) -> List[Body]:
        raise NotImplementedError
        
    @abc.abstractmethod
    def get_detections_for_frame(self, frame_id: int) -> List[Detection]:
        raise NotImplementedError
        
    @abc.abstractmethod
    def get_frames_for_collection(self, collection_id: int) -> List[Frame]:
        raise NotImplementedError


class SqlAlchemyTrackingRepository(AbstractTrackingRepository):
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_frame(self, frame: Frame) -> None:
        self.session.add(frame)
    
    def add_face(self, face: Face) -> None:
        self.session.add(face)
        
    def add_body(self, body: Body) -> None:
        self.session.add(body)
        
    def add_detection(self, detection: Detection) -> None:
        self.session.add(detection)
        
    def add_collection(self, collection: Collection) -> None:
        self.session.add(collection)
    
    def get_frame(self, frame_id: int) -> Optional[Frame]:
        return self.session.query(Frame).filter(Frame.id == frame_id).first()
        
    def get_collection(self, collection_id: int) -> Optional[Collection]:
        return self.session.query(Collection).filter(Collection.id == collection_id).first()
        
    def get_collection_by_uuid(self, uuid: str) -> Optional[Collection]:
        return self.session.query(Collection).filter(Collection.uuid == uuid).first()
    
    def get_faces_for_frame(self, frame_id: int) -> List[Face]:
        return self.session.query(Face).filter(Face.frame_id == frame_id).all()
    
    def get_bodies_for_frame(self, frame_id: int) -> List[Body]:
        return self.session.query(Body).filter(Body.frame_id == frame_id).all()
        
    def get_detections_for_frame(self, frame_id: int) -> List[Detection]:
        return self.session.query(Detection).filter(Detection.frame_id == frame_id).all()
        
    def get_frames_for_collection(self, collection_id: int) -> List[Frame]:
        return self.session.query(Frame).filter(Frame.collection_id == collection_id).all()
