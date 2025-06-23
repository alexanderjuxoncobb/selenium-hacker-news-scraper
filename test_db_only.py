#!/usr/bin/env python3
"""
Simple test script to verify database changes for single priority system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dashboard.database import DatabaseManager

def main():
    print("🔍 Testing Single Priority Database Implementation\n")
    
    db = DatabaseManager()
    
    # Test 1: Check that all weights are 1.0
    print("Test 1: Verifying all interests have weight 1.0")
    users = db.get_all_users()
    
    total_interests = 0
    weight_1_0_count = 0
    category_distribution = {}
    
    for user in users:
        interests = db.get_user_interest_weights(user.user_id)
        for interest in interests:
            total_interests += 1
            if interest.weight == 1.0:
                weight_1_0_count += 1
            
            category = interest.category
            category_distribution[category] = category_distribution.get(category, 0) + 1
    
    print(f"   Total interests: {total_interests}")
    print(f"   Interests with weight 1.0: {weight_1_0_count}")
    print(f"   Success rate: {(weight_1_0_count/total_interests)*100:.1f}%")
    
    if weight_1_0_count == total_interests:
        print("   ✅ PASSED: All interests have weight 1.0")
    else:
        print("   ❌ FAILED: Some interests have non-1.0 weights")
    
    # Test 2: Check category distribution
    print(f"\nTest 2: Verifying category distribution")
    print("   Categories found:")
    for category, count in sorted(category_distribution.items()):
        print(f"     {category}: {count} interests")
    
    expected_categories = {'technology', 'business', 'science', 'general'}
    actual_categories = set(category_distribution.keys())
    
    if expected_categories.issubset(actual_categories):
        print("   ✅ PASSED: All expected categories present")
    else:
        missing = expected_categories - actual_categories
        print(f"   ❌ FAILED: Missing categories: {missing}")
    
    # Test 3: Sample a few users to show their interests by category
    print(f"\nTest 3: Sample user interests by category")
    sample_users = users[:2]  # First 2 users
    
    for user in sample_users:
        print(f"\n   User: {user.email}")
        interests = db.get_user_interest_weights(user.user_id)
        
        # Group by category
        by_category = {}
        for interest in interests:
            cat = interest.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(interest.keyword)
        
        for category, keywords in by_category.items():
            print(f"     {category}: {len(keywords)} interests - {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}")
    
    print(f"\n🎉 Database verification complete!")

if __name__ == "__main__":
    main()