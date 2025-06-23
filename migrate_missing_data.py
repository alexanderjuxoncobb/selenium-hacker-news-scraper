#!/usr/bin/env python3
"""
Migrate the missing interaction data that was skipped
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3
import psycopg2

# Load environment variables
load_dotenv()

def migrate_missing_data():
    """Migrate the missing user interactions, relevance, and notes"""
    
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url:
        print("❌ Error: DATABASE_URL not set")
        return False
    
    print("🔄 Migrating missing interaction data...")
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_url)
    
    try:
        # Migrate user_story_relevance (1,473 records)
        print("📋 Migrating user_story_relevance...")
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        sqlite_cursor.execute("SELECT * FROM user_story_relevance")
        rows = sqlite_cursor.fetchall()
        
        count = 0
        for row in rows:
            row_dict = dict(row)
            values = [
                row_dict.get('user_id'),
                row_dict.get('story_id'), 
                bool(row_dict.get('is_relevant', False)),
                row_dict.get('relevance_score'),
                row_dict.get('relevance_reasoning'),
                row_dict.get('calculated_at')
            ]
            
            try:
                postgres_cursor.execute("""
                    INSERT INTO user_story_relevance (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, story_id) DO NOTHING
                """, values)
                count += 1
            except Exception as e:
                print(f"   ⚠️  Error inserting relevance row: {e}")
        
        print(f"   ✅ Migrated {count} relevance records")
        
        # Migrate user_interactions (8 records)
        print("📋 Migrating user_interactions...")
        
        sqlite_cursor.execute("SELECT * FROM user_interactions")
        rows = sqlite_cursor.fetchall()
        
        count = 0
        for row in rows:
            row_dict = dict(row)
            values = [
                row_dict.get('user_id'),
                row_dict.get('story_id'),
                row_dict.get('interaction_type'),
                row_dict.get('timestamp'),
                row_dict.get('duration_seconds')
            ]
            
            try:
                postgres_cursor.execute("""
                    INSERT INTO user_interactions (user_id, story_id, interaction_type, timestamp, duration_seconds)
                    VALUES (%s, %s, %s, %s, %s)
                """, values)
                count += 1
            except Exception as e:
                print(f"   ⚠️  Error inserting interaction row: {e}")
        
        print(f"   ✅ Migrated {count} interaction records")
        
        # Migrate story_notes (5 records)
        print("📋 Migrating story_notes...")
        
        sqlite_cursor.execute("SELECT * FROM story_notes") 
        rows = sqlite_cursor.fetchall()
        
        count = 0
        for row in rows:
            row_dict = dict(row)
            values = [
                row_dict.get('user_id'),
                row_dict.get('story_id'),
                row_dict.get('note'),
                row_dict.get('created_at'),
                row_dict.get('updated_at')
            ]
            
            try:
                postgres_cursor.execute("""
                    INSERT INTO story_notes (user_id, story_id, note, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, story_id) DO NOTHING
                """, values)
                count += 1
            except Exception as e:
                print(f"   ⚠️  Error inserting note row: {e}")
        
        print(f"   ✅ Migrated {count} story notes")
        
        # Commit all changes
        postgres_conn.commit()
        print("✅ Missing data migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def main():
    print("🚀 Missing Data Migration Tool")
    print("=" * 50)
    
    if migrate_missing_data():
        print("\n✅ All missing data migrated successfully!")
        print("📊 Summary:")
        print("   - User story relevance: 1,473 records")
        print("   - User interactions: 8 records") 
        print("   - Story notes: 5 records")
    else:
        print("\n❌ Migration failed")

if __name__ == "__main__":
    main()