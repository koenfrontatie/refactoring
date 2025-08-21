import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import numpy as np
from datetime import datetime, timedelta

from the_judge.domain.tracking.model import (
    Visitor, VisitorState, VisitorSession, Frame, 
    Face, FaceEmbedding, Composite, Detection
)
from the_judge.domain.tracking.events import (
    VisitorPromoted, VisitorWentMissing, VisitorReturned, 
    VisitorExpired, SessionStarted, SessionEnded
)
from the_judge.common.datetime_utils import now


def create_test_frame(collection_id="collection-1"):
    return Frame(
        id=str(uuid.uuid4()),
        camera_name="camera-1",
        captured_at=now(),
        collection_id=collection_id
    )


def create_test_composite():
    face = Face(
        id=str(uuid.uuid4()),
        frame_id="frame-1",
        bbox=(10, 10, 50, 50),
        embedding_id="emb-1",
        embedding_norm=1.0,
        det_score=0.9,
        quality_score=0.8,
        pose="frontal",
        age=25,
        sex="M",
        captured_at=now()
    )
    
    embedding = FaceEmbedding(
        id="emb-1",
        embedding=np.random.rand(512),
        normed_embedding=np.random.rand(512)
    )
    
    return Composite(face=face, embedding=embedding)


def test_visitor_creation():
    print("=== Testing Visitor Creation ===\n")
    
    print("Testing: Factory method creates visitor properly")
    
    current_time = now()
    visitor = Visitor.create_new("Test Visitor", current_time)
    
    assert visitor.name == "Test Visitor"
    assert visitor.state == VisitorState.TEMPORARY
    assert visitor.seen_count == 0
    assert visitor.frame_count == 0
    assert visitor.last_seen == current_time
    assert visitor.created_at == current_time
    assert visitor.current_session is None
    assert len(visitor.events) == 0
    print("✓ Visitor created with correct initial state")
    
    print("\n🎉 Visitor creation tests passed!")


def test_visitor_sighting_mechanics():
    print("\n=== Testing Visitor Sighting Mechanics ===\n")
    
    print("Testing: First sighting creates session")
    
    visitor = Visitor.create_new("Test Visitor", now())
    frame = create_test_frame()
    
    visitor.mark_sighting(frame, increment_seen=True)
    
    assert visitor.seen_count == 1
    assert visitor.frame_count == 1
    assert visitor.last_seen == frame.captured_at
    assert visitor.current_session is not None
    assert visitor.current_session.is_active
    assert len(visitor.events) == 1
    assert isinstance(visitor.events[0], SessionStarted)
    print("✓ First sighting creates session and increments counts")
    
    print("\nTesting: Subsequent sightings in same session")
    
    visitor.events.clear()
    frame2 = create_test_frame()
    
    visitor.mark_sighting(frame2, increment_seen=True)
    
    assert visitor.seen_count == 2
    assert visitor.frame_count == 2
    assert visitor.current_session.frame_count == 2
    assert len(visitor.events) == 0
    print("✓ Subsequent sightings increment existing session")
    
    print("\nTesting: Sighting without incrementing seen count")
    
    frame3 = create_test_frame()
    
    visitor.mark_sighting(frame3, increment_seen=False)
    
    assert visitor.seen_count == 2
    assert visitor.frame_count == 3
    assert visitor.current_session.frame_count == 3
    print("✓ Frame count increments independently of seen count")
    
    print("\n🎉 Visitor sighting mechanics tests passed!")


def test_visitor_state_transitions():
    print("\n=== Testing Visitor State Transitions ===\n")
    
    print("Testing: Promotion from TEMPORARY to ACTIVE")
    
    visitor = Visitor.create_new("Promotable Visitor", now())
    visitor.seen_count = 2
    
    current_time = now()
    visitor.update_state(current_time)
    assert visitor.state == VisitorState.TEMPORARY
    assert len(visitor.events) == 0
    
    visitor.seen_count = 3
    visitor.update_state(current_time)
    assert visitor.state == VisitorState.ACTIVE
    assert len(visitor.events) == 1
    assert isinstance(visitor.events[0], VisitorPromoted)
    print("✓ Visitor promoted correctly at seen_count threshold")
    
    print("\nTesting: Going MISSING after timeout")
    
    visitor.events.clear()
    old_time = now() - timedelta(minutes=2)
    visitor.last_seen = old_time
    visitor.current_session = VisitorSession.create_new(visitor.id, create_test_frame())
    
    current_time = now()
    visitor.update_state(current_time)
    
    assert visitor.state == VisitorState.MISSING
    assert not visitor.current_session.is_active
    assert len(visitor.events) == 2
    event_types = [type(event) for event in visitor.events]
    assert VisitorWentMissing in event_types
    assert SessionEnded in event_types
    print("✓ Visitor goes missing and ends session correctly")
    
    print("\nTesting: RETURNING from MISSING")
    
    visitor.events.clear()
    visitor.state = VisitorState.MISSING
    
    visitor.update_state(current_time)
    assert visitor.state == VisitorState.RETURNING
    assert len(visitor.events) == 1
    assert isinstance(visitor.events[0], VisitorReturned)
    print("✓ Missing visitor returns correctly")
    
    print("\nTesting: EXPIRED state for old temporary visitors")
    
    temp_visitor = Visitor.create_new("Temp Visitor", now())
    temp_visitor.state = VisitorState.TEMPORARY
    temp_visitor.last_seen = now() - timedelta(minutes=3)
    
    current_time = now()
    temp_visitor.update_state(current_time)
    
    assert temp_visitor.state == VisitorState.EXPIRED
    assert len(temp_visitor.events) == 1
    assert isinstance(temp_visitor.events[0], VisitorExpired)
    print("✓ Old temporary visitor expires correctly")
    
    print("\n🎉 Visitor state transition tests passed!")


def test_visitor_session_mechanics():
    print("\n=== Testing Visitor Session Mechanics ===\n")
    
    print("Testing: Session creation and management")
    
    visitor = Visitor.create_new("Session Visitor", now())
    frame1 = create_test_frame()
    
    session = VisitorSession.create_new(visitor.id, frame1)
    
    assert session.visitor_id == visitor.id
    assert session.start_frame_id == frame1.id
    assert session.started_at == frame1.captured_at
    assert session.captured_at == frame1.captured_at
    assert session.frame_count == 1
    assert session.is_active == True
    assert session.ended_at is None
    print("✓ Session created correctly")
    
    print("\nTesting: Session frame incrementing")
    
    frame2 = create_test_frame()
    session.increment_frame(frame2)
    
    assert session.frame_count == 2
    assert session.captured_at == frame2.captured_at
    assert session.is_active == True
    print("✓ Session frame incremented correctly")
    
    print("\nTesting: Session ending")
    
    end_time = now()
    session.end(end_time)
    
    assert session.ended_at == end_time
    assert session.is_active == False
    assert session.duration is not None
    print("✓ Session ended correctly")
    
    print("\n🎉 Visitor session mechanics tests passed!")


def test_detection_creation():
    print("\n=== Testing Detection Creation ===\n")
    
    print("Testing: Visitor creates detection correctly")
    
    visitor = Visitor.create_new("Detection Visitor", now())
    visitor.state = VisitorState.ACTIVE
    
    frame = create_test_frame()
    composite = create_test_composite()
    
    detection = visitor.create_detection(frame, composite)
    
    assert detection.frame == frame
    assert detection.face == composite.face
    assert detection.embedding == composite.embedding
    assert detection.visitor == visitor
    assert detection.state == VisitorState.ACTIVE
    assert detection.captured_at == visitor.last_seen
    assert detection.body == composite.body
    print("✓ Detection created with correct properties")
    
    print("\n🎉 Detection creation tests passed!")


def run_all_tests():
    test_visitor_creation()
    test_visitor_sighting_mechanics()
    test_visitor_state_transitions()
    test_visitor_session_mechanics()
    test_detection_creation()


if __name__ == "__main__":
    run_all_tests()
