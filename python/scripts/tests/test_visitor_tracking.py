import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock

from the_judge.domain.tracking.model import (
    Frame, Face, Body, FaceEmbedding, Composite, Visitor, VisitorState, 
    Detection, VisitorSession, VisitorCollection
)
from the_judge.application.services.tracking_service import TrackingService
from the_judge.domain.tracking.ports import FaceRecognizerPort
from the_judge.domain.tracking.events import FrameProcessed, SessionStarted, VisitorPromoted
from the_judge.common.datetime_utils import now


class MockRepository:
    def __init__(self):
        self.added_entities = []
        self.merged_entities = []
        self.deleted_entities = []
        self._storage = {}
    
    def add(self, entity):
        self.added_entities.append(entity)
        self._storage[entity.id] = entity
    
    def merge(self, entity):
        self.merged_entities.append(entity)
        self._storage[entity.id] = entity
    
    def delete(self, entity):
        self.deleted_entities.append(entity)
        if entity.id in self._storage:
            del self._storage[entity.id]
    
    def get(self, entity_class, entity_id):
        entity = self._storage.get(entity_id)
        return entity if isinstance(entity, entity_class) else None
    
    def list_by(self, entity_class, **kwargs):
        results = []
        for entity in self._storage.values():
            if isinstance(entity, entity_class):
                match = True
                for key, value in kwargs.items():
                    if not hasattr(entity, key) or getattr(entity, key) != value:
                        match = False
                        break
                if match:
                    results.append(entity)
        return results


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


class MockFaceRecognizer(FaceRecognizerPort):
    def __init__(self):
        self.recognition_map = {}
        self.collection_matches = {}
    
    def set_recognition_result(self, face_id, visitor):
        self.recognition_map[face_id] = visitor
    
    def set_collection_match(self, face_id, visitor):
        self.collection_matches[face_id] = visitor
    
    def recognize_faces(self, uow, composites):
        result = []
        for comp in composites:
            matched_visitor = self.recognition_map.get(comp.face.id)
            comp_copy = Composite(
                face=comp.face,
                embedding=comp.embedding,
                body=comp.body,
                visitor=matched_visitor
            )
            result.append(comp_copy)
        return result
    
    def match_against_collection(self, composite, collection_composites):
        return self.collection_matches.get(composite.face.id)


class MockMessageBus:
    def __init__(self):
        self.handled_events = []
    
    def handle(self, event):
        self.handled_events.append(event)


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
    
    uow = MockUnitOfWork()
    recognizer = MockFaceRecognizer()
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite = create_composite()
    frame = create_frame()
    
    service.handle_frame(uow, frame, [composite], [])
    
    visitors_added = [e for e in uow.repository.added_entities if isinstance(e, Visitor)]
    assert len(visitors_added) == 1
    assert visitors_added[0].state == VisitorState.TEMPORARY
    assert visitors_added[0].seen_count == 1
    assert visitors_added[0].frame_count == 1
    print("✓ New visitor created successfully")


def test_visitor_promotion_after_threshold():
    print("Testing: Visitor promotion after seen threshold")
    
    existing_visitor = Visitor.create_new("Test Visitor", now())
    existing_visitor.seen_count = 2
    
    uow = MockUnitOfWork()
    uow.repository.add(existing_visitor)
    
    recognizer = MockFaceRecognizer()
    recognizer.set_recognition_result("face-1", existing_visitor)
    
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite = create_composite(face_id="face-1")
    frame = create_frame(collection_id="new-collection")
    
    service.handle_frame(uow, frame, [composite], [])
    
    merged_visitors = [e for e in uow.repository.merged_entities if isinstance(e, Visitor)]
    assert len(merged_visitors) == 1
    updated_visitor = merged_visitors[0]
    assert updated_visitor.seen_count == 3
    assert updated_visitor.state == VisitorState.ACTIVE
    
    promotion_events = [e for e in bus.handled_events if isinstance(e, VisitorPromoted)]
    assert len(promotion_events) == 1
    print("✓ Visitor promoted to ACTIVE successfully")


def test_collection_scoped_seen_count():
    print("Testing: Collection-scoped seen count (no double counting)")
    
    existing_visitor = Visitor.create_new("Test Visitor", now())
    existing_visitor.seen_count = 1
    
    uow = MockUnitOfWork()
    uow.repository.add(existing_visitor)
    
    recognizer = MockFaceRecognizer()
    recognizer.set_recognition_result("face-2", existing_visitor)
    
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite1 = create_composite(face_id="face-2", embedding_id="emb-1")
    composite2 = create_composite(face_id="face-2", embedding_id="emb-2") 
    frame = create_frame(collection_id="same-collection")
    
    service.handle_frame(uow, frame, [composite1], [])
    merged_visitors = [e for e in uow.repository.merged_entities if isinstance(e, Visitor)]
    initial_count = merged_visitors[0].seen_count
    
    uow.repository.merged_entities.clear()
    service.handle_frame(uow, frame, [composite2], [])
    merged_visitors = [e for e in uow.repository.merged_entities if isinstance(e, Visitor)]
    final_count = merged_visitors[0].seen_count
    
    assert initial_count == 2
    assert final_count == 2
    print("✓ Collection-scoped counting works correctly")


def test_detections_always_created():
    print("Testing: Detections created for every recognition")
    
    existing_visitor = Visitor.create_new("Test Visitor", now())
    existing_visitor.seen_count = 1
    
    uow = MockUnitOfWork()
    uow.repository.add(existing_visitor)
    
    recognizer = MockFaceRecognizer()
    recognizer.set_recognition_result("face-3", existing_visitor)
    
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite = create_composite(face_id="face-3")
    frame = create_frame()
    
    service.handle_frame(uow, frame, [composite], [])
    
    detections = [e for e in uow.repository.added_entities if isinstance(e, Detection)]
    assert len(detections) == 1
    detection = detections[0]
    assert detection.frame == frame
    assert detection.face.id == "face-3"
    assert detection.visitor == existing_visitor
    print("✓ Detection created successfully")


def test_session_management():
    print("Testing: Session creation and management")
    
    uow = MockUnitOfWork()
    recognizer = MockFaceRecognizer()
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite = create_composite()
    frame = create_frame()
    
    service.handle_frame(uow, frame, [composite], [])
    
    visitors_added = [e for e in uow.repository.added_entities if isinstance(e, Visitor)]
    assert len(visitors_added) == 1
    visitor = visitors_added[0]
    assert visitor.current_session is not None
    assert visitor.current_session.is_active
    
    session_events = [e for e in bus.handled_events if isinstance(e, SessionStarted)]
    assert len(session_events) == 1
    print("✓ Session created and managed correctly")


def test_frame_processed_event():
    print("Testing: FrameProcessed event is published")
    
    uow = MockUnitOfWork()
    recognizer = MockFaceRecognizer()
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite1 = create_composite(face_id="face-1")
    composite2 = create_composite(face_id="face-2")
    frame = create_frame()
    
    service.handle_frame(uow, frame, [composite1, composite2], [])
    
    frame_events = [e for e in bus.handled_events if isinstance(e, FrameProcessed)]
    assert len(frame_events) == 1
    assert frame_events[0].frame_id == frame.id
    assert frame_events[0].detection_count == 2
    print("✓ FrameProcessed event published correctly")


def test_collection_buffer_integration():
    print("Testing: Collection buffer integration")
    
    existing_visitor = Visitor.create_new("Buffer Visitor", now())
    
    uow = MockUnitOfWork()
    recognizer = MockFaceRecognizer()
    recognizer.set_collection_match("face-buffer", existing_visitor)
    
    bus = MockMessageBus()
    
    service = TrackingService(recognizer, lambda: uow, bus)
    
    composite = create_composite(face_id="face-buffer")
    frame = create_frame(collection_id="buffer-collection")
    
    service.handle_frame(uow, frame, [composite], [])
    
    collection = service.collection_buffer.current_collection
    assert collection is not None
    assert collection.id == "buffer-collection"
    assert len(collection.composites) == 1
    assert collection.composites[0].visitor is not None
    print("✓ Collection buffer integration works correctly")


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
        
        test_session_management()
        print()
        
        test_frame_processed_event()
        print()
        
        test_collection_buffer_integration()
        print()
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
