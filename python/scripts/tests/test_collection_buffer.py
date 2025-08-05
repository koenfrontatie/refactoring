import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import numpy as np

from the_judge.domain.tracking.model import Face, FaceEmbedding, Body, Composite, Visitor, VisitorState, VisitorCollection
from the_judge.application.services.collection_buffer import CollectionBuffer
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
            seen_count=1,
            last_seen=now(),
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
    
    print("Testing: Basic buffer operations")
    
    buffer = CollectionBuffer()
    assert buffer.current_collection is None
    print("✓ Empty buffer initialized correctly")
    
    collection = buffer.get_or_create_collection("test-collection")
    assert collection.id == "test-collection"
    assert len(collection.composites) == 0
    assert buffer.current_collection is not None
    print("✓ Collection created successfully")
    
    composite1 = create_test_composite()
    is_new = buffer.add_composite(composite1)
    
    assert len(buffer.current_collection.composites) == 1
    assert is_new == False  # No visitor, so not considered "new"
    print("✓ Composite without visitor added correctly")
    
    composite2 = create_test_composite(visitor_id="visitor-123")
    is_new = buffer.add_composite(composite2)
    
    assert len(buffer.current_collection.composites) == 2
    assert is_new == True  # New visitor in collection
    print("✓ Composite with visitor added correctly")
    
    print("\nTesting: Collection switching")
    
    new_collection = buffer.get_or_create_collection("new-collection")
    assert new_collection.id == "new-collection"
    assert len(new_collection.composites) == 0
    assert buffer.current_collection.id == "new-collection"
    print("✓ Collection switched successfully")
    
    print("\nTesting: Same collection persistence")
    
    same_collection = buffer.get_or_create_collection("new-collection")
    assert same_collection.id == "new-collection"
    assert same_collection is buffer.current_collection
    print("✓ Same collection returned when ID matches")
    
    print("\nTesting: Visitor deduplication in collection")
    
    composite_a = create_test_composite(visitor_id="visitor-A")
    composite_b = create_test_composite(visitor_id="visitor-A")  # Same visitor
    composite_c = create_test_composite(visitor_id="visitor-B")  # Different visitor
    
    is_new_a1 = buffer.add_composite(composite_a)
    is_new_a2 = buffer.add_composite(composite_b)  # Same visitor again
    is_new_b = buffer.add_composite(composite_c)
    
    assert is_new_a1 == True   # First time seeing visitor-A
    assert is_new_a2 == False  # Second time seeing visitor-A (not new)
    assert is_new_b == True    # First time seeing visitor-B
    
    assert len(buffer.current_collection.composites) == 3
    print("✓ Visitor deduplication works correctly")
    
    print("\n🎉 All collection buffer tests passed!")


def test_composite_enrichment():
    print("\n=== Testing Composite Enrichment ===\n")
    
    print("Testing: Progressive enrichment of composite")
    
    composite = create_test_composite()
    assert composite.visitor is None
    print("✓ Initial composite has no visitor")
    
    visitor = Visitor(
        id="visitor-456",
        name="Recognized Visitor",
        state=VisitorState.TEMPORARY,
        seen_count=1,
        last_seen=now(),
        created_at=now()
    )
    
    composite.visitor = visitor
    assert composite.visitor is not None
    assert composite.visitor.id == "visitor-456"
    print("✓ Visitor added to composite successfully")
    
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
