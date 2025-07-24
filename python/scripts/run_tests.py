#!/usr/bin/env python3
"""
Run all visitor tracking tests
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.test_visitor_tracking import run_all_tests as run_tracking_tests
from tests.test_visitor_domain import test_visitor_business_rules
from tests.test_collection_buffer import run_all_tests as run_buffer_tests


def main():
    print("🧪 Running All Visitor Tracking Tests\n")
    print("=" * 50)
    
    try:
        # Test 1: Domain model business rules
        test_visitor_business_rules()
        print("\n" + "=" * 50)
        
        # Test 2: Collection buffer functionality  
        run_buffer_tests()
        print("\n" + "=" * 50)
        
        # Test 3: Full tracking service integration
        run_tracking_tests()
        print("\n" + "=" * 50)
        
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("Your visitor tracking system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
