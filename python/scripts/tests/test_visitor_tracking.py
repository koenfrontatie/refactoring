import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock

from the_judge.domain.tracking import Frame, Face, Body, FaceEmbedding, Composite, Visitor, VisitorState, Detection
from the_judge.application.tracking_service import TrackingService
from the_judge.common.datetime_utils import now


class MockRepository:
    def __init__(self):
        self.visitors_added = []
        self.faces_added = []
        self.embeddings_added = []
        self.bodies_added = []
        self.detections_added = []
        self._storage = {}
    
    def add(self, entity):
        if isinstance(entity, Visitor):
            self.visitors_added.append(entity)
        elif isinstance(entity, Face):
            self.faces_added.append(entity)
        elif isinstance(entity, FaceEmbedding):
            self.embeddings_added.append(entity)
        elif isinstance(entity, Body):
            self.bodies_added.append(entity)
        elif isinstance(entity, Detection):
            self.detections_added.append(entity)
        
        self._storage[entity.id] = entity
    
    def get(self, entity_class, entity_id):
        entity = self._storage.get(entity_id)
        return entity if isinstance(entity, entity_class) else None


class MockUnitOfWork:
    def __init__(self):
        self.repository = MockRepository()
        self.committed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def commit(self):
        self.committed = True


class MockFaceRecognizer:
    def __init__(self):
        self.recognition_map = {}
    
    def set_recognition_result(self, face_id, visitor):
        self.recognition_map[face_id] = visitor
    
    def recognize_faces(self, composites):
        result = []
        for comp in composites:
            comp_copy = Composite(
                face=comp.face,
                embedding=comp.embedding,
                body=comp.body,
                visitor=self.recognition_map.get(comp.face.id, comp.visitor)
            )
            result.append(comp_copy)
        return result


class MockFaceBodyMatcher:
    def match_faces_to_bodies(self, composites, bodies):
        return composites


class MockFaceMLProvider:
    def __init__(self, face_recognizer):
        self.face_recognizer = face_recognizer
    
    def get_face_recognizer(self):
        return self.face_recognizer


def create_composite(face_id="face-1", embedding_id="emb-1", visitor=None):
    face = Face(
        id=face_id,
        frame_id="frame-1",
        bbox=(10, 10, 50, 50),
        embedding_id=embedding_id,
        embedding_norm=1.0,
        det_score=0.9,
        quality_score=0.8,
        pose="frontal",
        age=25,
        sex="M",
        captured_at=now()
    )
    
    embedding = FaceEmbedding(
        id=embedding_id,
        embedding=np.random.rand(512),
        normed_embedding=np.random.rand(512)
    )
    
    return Composite(
        face=face,
        embedding=embedding,
        body=None,
        visitor=visitor
    )


def create_frame(collection_id="collection-1"):
    return Frame(
        id=str(uuid.uuid4()),
        camera_name="camera-1",
        captured_at=now(),
        collection_id=collection_id
    )


def test_creates_new_visitor_for_unrecognized_face():
    print("Testing: Creates new visitor for unrecognized face")
    
    # Arrange
    uow = MockUnitOfWork()
    recognizer = MockFaceRecognizer()
    face_provider = MockFaceMLProvider(recognizer)
    matcher = MockFaceBodyMatcher()
    bus = Mock()
    
    service = TrackingService(face_provider, matcher, lambda: uow, bus)
    
    composite = create_composite()
    frame = create_frame()
    
    # Act
    service.handle_frame(uow, frame, [composite], [])
    
    # Assert
    assert len(uow.repository.visitors_added) == 1
    assert uow.repository.visitors_added[0].state == VisitorState.TEMPORARY
    assert uow.repository.visitors_added[0].seen_count == 1
    print("✓ New visitor created successfully")


def test_visitor_promotion_after_threshold():
    print("Testing: Visitor promotion after seen threshold")
    
    # Arrange
    existing_visitor = Visitor(
        id="visitor-123",
        name="Test Visitor",
        state=VisitorState.TEMPORARY,
        face_id="face-1",
        body_id=None,
        seen_count=2,
        captured_at=now(),
        created_at=now()
    )
    
    uow = MockUnitOfWork()
    uow.repository.add(existing_visitor)
    
    recognizer = MockFaceRecognizer()
    recognizer.set_recognition_result("face-1", existing_visitor)
    
    face_provider = MockFaceMLProvider(recognizer)
    matcher = MockFaceBodyMatcher()
    bus = Mock()
    
    service = TrackingService(face_provider, matcher, lambda: uow, bus)
    
    composite = create_composite(face_id="face-1")
    frame = create_frame(collection_id="new-collection")
    
    # Act
    service.handle_frame(uow, frame, [composite], [])
    
    # Assert
    updated_visitor = next(v for v in uow.repository.visitors_added if v.id == "visitor-123")
    assert updated_visitor.seen_count == 3
    assert updated_visitor.state == VisitorState.PERMANENT
    print("✓ Visitor promoted to PERMANENT successfully")


def test_collection_scoped_seen_count():
    print("Testing: Collection-scoped seen count (no double counting)")
    
    # Arrange
    existing_visitor = Visitor(
        id="visitor-456",
        name="Test Visitor",
        state=VisitorState.TEMPORARY,
        face_id="face-2",
        body_id=None,
        seen_count=1,
        captured_at=now(),
        created_at=now()
    )
    
    uow = MockUnitOfWork()
    uow.repository.add(existing_visitor)
    
    recognizer = MockFaceRecognizer()
    recognizer.set_recognition_result("face-2", existing_visitor)
    
    face_provider = MockFaceMLProvider(recognizer)
    matcher = MockFaceBodyMatcher()
    bus = Mock()
    
    service = TrackingService(face_provider, matcher, lambda: uow, bus)
    
    # Same collection, same visitor on different cameras
    composite1 = create_composite(face_id="face-2", embedding_id="emb-1")
    composite2 = create_composite(face_id="face-2", embedding_id="emb-2")
    frame = create_frame(collection_id="same-collection")
    
    # Act - process first camera
    service.handle_frame(uow, frame, [composite1], [])
    initial_count = next(v for v in uow.repository.visitors_added if v.id == "visitor-456").seen_count
    
    # Act - process second camera (same collection)
    service.handle_frame(uow, frame, [composite2], [])
    final_count = next(v for v in uow.repository.visitors_added if v.id == "visitor-456").seen_count
    
    # Assert
    assert initial_count == 2  # Incremented once
    assert final_count == 2    # Not incremented again (same collection)
    print("✓ Collection-scoped counting works correctly")


def test_detections_always_created():
    print("Testing: Detections created for every recognition")
    
    # Arrange
    existing_visitor = Visitor(
        id="visitor-789",
        name="Test Visitor",
        state=VisitorState.TEMPORARY,
        face_id="face-3",
        body_id=None,
        seen_count=1,
        captured_at=now(),
        created_at=now()
    ) 
    
    uow = MockUnitOfWork()
    uow.repository.add(existing_visitor)
    
    recognizer = MockFaceRecognizer()
    recognizer.set_recognition_result("face-3", existing_visitor)
    
    face_provider = MockFaceMLProvider(recognizer)
    matcher = MockFaceBodyMatcher()
    bus = Mock()
    
    service = TrackingService(face_provider, matcher, lambda: uow, bus)
    
    composite = create_composite(face_id="face-3")
    frame = create_frame()
    
    # Act
    service.handle_frame(uow, frame, [composite], [])
    
    # Assert
    assert len(uow.repository.detections_added) == 1
    detection = uow.repository.detections_added[0]
    assert detection.frame_id == frame.id
    assert detection.face_id == "face-3"
    assert detection.visitor_record['id'] == "visitor-789"
    print("✓ Detection created successfully")


def run_all_tests():
    print("=== Running Visitor Tracking Tests ===\n")
    
    try:
        test_creates_new_visitor_for_unrecognized_face()
        print()
        
        test_visitor_promotion_after_threshold()
        print()
        
        test_collection_scoped_seen_count()
        print()
        
        test_detections_always_created()
        print()
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
