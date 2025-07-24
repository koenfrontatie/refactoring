import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import numpy as np
from datetime import datetime, timedelta

from the_judge.domain.tracking.model import Visitor, VisitorState
from the_judge.common.datetime_utils import now


def test_visitor_business_rules():
    print("=== Testing Visitor Business Rules ===\n")
    
    # Test 1: should_be_promoted logic
    print("Testing: should_be_promoted logic")
    
    visitor = Visitor(
        id=str(uuid.uuid4()),
        name="Test Visitor",
        state=VisitorState.TEMPORARY,
        face_id="face-1",
        body_id=None,
        seen_count=3,
        captured_at=now(),
        created_at=now()
    )
    
    assert visitor.should_be_promoted == True
    print("✓ Visitor with seen_count=3 should be promoted")
    
    visitor.seen_count = 2
    assert visitor.should_be_promoted == False
    print("✓ Visitor with seen_count=2 should not be promoted")
    
    # Test 2: is_missing logic
    print("\nTesting: is_missing logic")
    
    # Recent visitor
    visitor.captured_at = now()
    assert visitor.is_missing == False
    print("✓ Recently seen visitor is not missing")
    
    # Old visitor (over 1 minute)
    visitor.captured_at = now() - timedelta(minutes=2)
    assert visitor.is_missing == True
    print("✓ Visitor not seen for 2 minutes is missing")
    
    # Test 3: should_be_removed logic
    print("\nTesting: should_be_removed logic")
    
    temporary_visitor = Visitor(
        id=str(uuid.uuid4()),
        name="Temp Visitor",
        state=VisitorState.TEMPORARY,
        face_id="face-2",
        body_id=None,
        seen_count=1,
        captured_at=now() - timedelta(minutes=2),
        created_at=now()
    )
    
    assert temporary_visitor.should_be_removed == True
    print("✓ Old temporary visitor should be removed")
    
    permanent_visitor = Visitor(
        id=str(uuid.uuid4()),
        name="Permanent Visitor",
        state=VisitorState.PERMANENT,
        face_id="face-3",
        body_id=None,
        seen_count=5,
        captured_at=now() - timedelta(minutes=2),
        created_at=now()
    )
    
    assert permanent_visitor.should_be_removed == False
    print("✓ Old permanent visitor should not be removed")
    
    # Test 4: visitor record serialization
    print("\nTesting: visitor record serialization")
    
    visitor_record = visitor.record()
    expected_fields = {'id', 'name', 'state', 'face_id', 'body_id', 'seen_count', 'captured_at', 'created_at'}
    
    assert set(visitor_record.keys()) == expected_fields
    assert visitor_record['state'] == visitor.state  # Should be enum, not string
    print("✓ Visitor record contains all expected fields")
    
    print("\n🎉 All business rule tests passed!")


if __name__ == "__main__":
    test_visitor_business_rules()
