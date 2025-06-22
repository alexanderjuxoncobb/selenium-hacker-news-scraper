#!/usr/bin/env python3
"""
Migration script to convert priority-based interests to topic-based categories
Removes the priority system and makes all interests equal weight (1.0)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dashboard.database import DatabaseManager

def get_topic_category_mapping():
    """Map keywords to their logical topic categories"""
    return {
        # Technology & Programming
        "artificial intelligence": "technology",
        "AI": "technology", 
        "machine learning": "technology",
        "ML": "technology",
        "software development": "technology",
        "programming": "technology",
        "hardware": "technology",
        "robotics": "technology",
        "TPU": "technology",
        "tensor processing unit": "technology",
        "CUDA": "technology",
        "PyTorch": "technology",
        "TensorFlow": "technology",
        "computer vision": "technology",
        "neural networks": "technology",
        "deep learning": "technology",
        "NLP": "technology",
        "LLM": "technology",
        "transformer": "technology",
        "embedding": "technology",
        "optimization": "technology",
        "algorithm": "technology",
        "data science": "technology",
        
        # Business & Finance
        "startups": "business",
        "tech startups": "business",
        "business": "business",
        "finance": "business",
        "cryptocurrency": "business",
        
        # Science & Health
        "science": "science",
        "health": "science",
        "medicine": "science",
        "climate": "science",
        
        # General Interest
        "politics": "general",
        "education": "general",
        "books": "general",
        "music": "general"
    }

def migrate_user_interests():
    """Migrate all user interests to single priority system"""
    db = DatabaseManager("hn_scraper.db")
    category_mapping = get_topic_category_mapping()
    
    print("🔄 Starting migration to single priority system...")
    
    # Get all users
    users = db.get_all_users()
    total_interests_updated = 0
    
    for user in users:
        print(f"\n👤 Migrating user: {user.email} ({user.user_id})")
        
        # Get user's current interests
        current_interests = db.get_user_interest_weights(user.user_id)
        
        for interest in current_interests:
            # Determine new topic category
            new_category = category_mapping.get(interest.keyword.lower(), "general")
            
            # Update to weight 1.0 and new category
            db.update_user_interest_weight(
                user.user_id, 
                interest.keyword, 
                1.0,  # Always weight 1.0
                new_category  # Topic category instead of priority
            )
            
            print(f"  ✅ {interest.keyword}: {interest.category}({interest.weight}) → {new_category}(1.0)")
            total_interests_updated += 1
    
    print(f"\n✅ Migration complete!")
    print(f"📊 Total interests updated: {total_interests_updated}")
    print(f"👥 Users migrated: {len(users)}")

def verify_migration():
    """Verify the migration worked correctly"""
    db = DatabaseManager("hn_scraper.db")
    
    print("\n🔍 Verifying migration...")
    
    # Check weight distribution
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
    
    print(f"📊 Verification Results:")
    print(f"  Total interests: {total_interests}")
    print(f"  Interests with weight 1.0: {weight_1_0_count}")
    print(f"  Weight migration success rate: {(weight_1_0_count/total_interests)*100:.1f}%")
    
    print(f"\n📂 Category distribution:")
    for category, count in sorted(category_distribution.items()):
        print(f"  {category}: {count} interests")

if __name__ == "__main__":
    migrate_user_interests()
    verify_migration()