import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import numpy as np

from the_judge.domain.tracking.model import Face, FaceEmbedding, Body, Composite, Visitor, VisitorState
from the_judge.application.tracking_service import FrameCollection
from the_judge.common.datetime_utils import now


def create_test_composite(visitor_id=None):
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
    
    visitor = None
    if visitor_id:
        visitor = Visitor(
            id=visitor_id,
            name="Test Visitor",
            state=VisitorState.TEMPORARY,
            face_id=face.id,
            body_id=None,
            seen_count=1,
            captured_at=now(),
            created_at=now()
        )
    
    return Composite(
        face=face,
        embedding=embedding,
        body=None,
        visitor=visitor
    )


def test_collection_buffer():
    print("=== Testing Collection Buffer ===\n")
    
    # Test 1: Basic buffer operations
    print("Testing: Basic buffer operations")
    
    buffer = FrameCollection("test-collection")
    assert len(buffer.get_composites()) == 0
    print("✓ Empty buffer initialized correctly")
    
    # Add composite without visitor
    composite1 = create_test_composite()
    buffer.add_composite(composite1)
    
    assert len(buffer.get_composites()) == 1
    assert buffer.has_visitor("nonexistent") == False
    print("✓ Composite without visitor added correctly")
    
    # Add composite with visitor
    composite2 = create_test_composite(visitor_id="visitor-123")
    buffer.add_composite(composite2)
    
    assert len(buffer.get_composites()) == 2
    assert buffer.has_visitor("visitor-123") == True
    assert buffer.has_visitor("nonexistent") == False
    print("✓ Composite with visitor added correctly")
    
    # Test 2: Buffer clearing
    print("\nTesting: Buffer clearing")
    
    buffer.clear()
    assert len(buffer.get_composites()) == 0
    assert buffer.has_visitor("visitor-123") == False
    print("✓ Buffer cleared successfully")
    
    # Test 3: Multiple visitors
    print("\nTesting: Multiple visitors in buffer")
    
    composite_a = create_test_composite(visitor_id="visitor-A")
    composite_b = create_test_composite(visitor_id="visitor-B")
    composite_c = create_test_composite()  # No visitor
    
    buffer.add_composite(composite_a)
    buffer.add_composite(composite_b)
    buffer.add_composite(composite_c)
    
    assert len(buffer.get_composites()) == 3
    assert buffer.has_visitor("visitor-A") == True
    assert buffer.has_visitor("visitor-B") == True
    assert buffer.has_visitor("visitor-C") == False
    print("✓ Multiple visitors handled correctly")
    
    # Test 4: Collection ID consistency
    print("\nTesting: Collection ID consistency")
    
    assert buffer.collection_id == "test-collection"
    print("✓ Collection ID stored correctly")
    
    print("\n🎉 All collection buffer tests passed!")


def test_composite_enrichment():
    print("\n=== Testing Composite Enrichment ===\n")
    
    # Test 1: Progressive enrichment
    print("Testing: Progressive enrichment of composite")
    
    # Start with basic composite
    composite = create_test_composite()
    assert composite.visitor is None
    print("✓ Initial composite has no visitor")
    
    # Add visitor (simulating recognition)
    visitor = Visitor(
        id="visitor-456",
        name="Recognized Visitor",
        state=VisitorState.TEMPORARY,
        face_id=composite.face.id,
        body_id=None,
        seen_count=1,
        captured_at=now(),
        created_at=now()
    )
    
    composite.visitor = visitor
    assert composite.visitor is not None
    assert composite.visitor.id == "visitor-456"
    print("✓ Visitor added to composite successfully")
    
    # Add body (simulating body matching)
    body = Body(
        id="body-123",
        frame_id="frame-1",
        bbox=(5, 20, 60, 100),
        captured_at=now()
    )
    
    composite.body = body
    assert composite.body is not None
    assert composite.body.id == "body-123"
    print("✓ Body added to composite successfully")
    
    # Test 2: Complete composite validation
    print("\nTesting: Complete composite validation")
    
    assert composite.face is not None
    assert composite.embedding is not None
    assert composite.body is not None
    assert composite.visitor is not None
    print("✓ Complete composite has all components")
    
    print("\n🎉 All composite enrichment tests passed!")


def run_all_tests():
    test_collection_buffer()
    test_composite_enrichment()


if __name__ == "__main__":
    run_all_tests()
