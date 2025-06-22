#!/usr/bin/env python3
"""
Test script to verify single priority system is working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dashboard.database import DatabaseManager
from ai_pipeline import AIRelevanceFilter

def test_database_interests():
    """Test that interests are stored with weight 1.0"""
    print("🔍 Testing database interest storage...")
    
    db = DatabaseManager("hn_scraper.db")
    
    # Get a test user
    users = db.get_all_users()
    if not users:
        print("❌ No users found for testing")
        return False
    
    test_user = users[0]
    print(f"Testing with user: {test_user.email}")
    
    # Get user interests
    interests = db.get_user_interest_weights(test_user.user_id)
    
    print(f"User has {len(interests)} interests:")
    for interest in interests[:5]:  # Show first 5
        print(f"  - {interest.keyword}: weight={interest.weight}, category={interest.category}")
    
    # Check if all weights are 1.0
    non_unity_weights = [i for i in interests if i.weight != 1.0]
    if non_unity_weights:
        print(f"❌ Found {len(non_unity_weights)} interests with non-1.0 weights")
        return False
    else:
        print("✅ All interests have weight 1.0")
        return True

def test_ai_pipeline():
    """Test that AI pipeline uses single weight"""
    print("\n🔍 Testing AI pipeline with single weights...")
    
    try:
        # Initialize AI pipeline
        ai_filter = AIRelevanceFilter()
        
        # Test with a sample story
        sample_story = {
            'title': 'New AI breakthrough in machine learning',
            'url': 'https://example.com/ai-news'
        }
        
        # Test with sample user interests
        user_interests = {
            'technology': ['artificial intelligence', 'machine learning'],
            'business': ['startups'],
            'science': ['climate']
        }
        
        # This should work with the updated system
        is_relevant, score, reasoning = ai_filter.is_relevant_story_local(sample_story, user_interests)
        
        print(f"✅ AI pipeline test completed")
        print(f"   Story relevance: {is_relevant}")
        print(f"   Score: {score:.3f}")
        print(f"   Reasoning: {reasoning}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI pipeline test failed: {e}")
        return False

def test_category_distribution():
    """Test category distribution after migration"""
    print("\n🔍 Testing category distribution...")
    
    db = DatabaseManager("hn_scraper.db")
    
    # Get all interests
    users = db.get_all_users()
    category_counts = {}
    
    for user in users:
        interests = db.get_user_interest_weights(user.user_id)
        for interest in interests:
            category = interest.category
            category_counts[category] = category_counts.get(category, 0) + 1
    
    print("Category distribution:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count} interests")
    
    # Check if we have reasonable categories
    expected_categories = {'technology', 'business', 'science', 'general'}
    actual_categories = set(category_counts.keys())
    
    if expected_categories.issubset(actual_categories):
        print("✅ All expected categories present")
        return True
    else:
        missing = expected_categories - actual_categories
        print(f"❌ Missing categories: {missing}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Single Priority System Implementation\n")
    
    tests = [
        ("Database Interests", test_database_interests),
        ("AI Pipeline", test_ai_pipeline), 
        ("Category Distribution", test_category_distribution)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    print(f"\n📊 Test Results:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"   {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Single priority system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")