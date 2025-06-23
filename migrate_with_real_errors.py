#!/usr/bin/env python3
"""
Migration script that shows REAL errors instead of hiding them
"""

import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_remaining_data():
    """Migrate the missing data with proper error reporting"""
    
    sqlite_conn = sqlite3.connect("hn_scraper.db")
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Build story ID mapping first
        print("📋 Building story ID mapping...")
        sqlite_cursor.execute("SELECT id, title, url, date, rank FROM stories")
        id_mapping = {}
        
        for row in sqlite_cursor.fetchall():
            sqlite_id = row['id']
            postgres_cursor.execute("""
                SELECT id FROM stories WHERE title = %s AND url = %s AND date = %s AND rank = %s LIMIT 1
            """, (row['title'], row['url'], row['date'], row['rank']))
            
            pg_result = postgres_cursor.fetchone()
            if pg_result:
                id_mapping[sqlite_id] = pg_result[0]
        
        print(f"✅ Mapped {len(id_mapping)} stories")
        
        # Migrate user_story_relevance
        print("📋 Migrating user_story_relevance...")
        sqlite_cursor.execute("SELECT * FROM user_story_relevance")
        relevance_rows = sqlite_cursor.fetchall()
        print(f"Found {len(relevance_rows)} relevance records in SQLite")
        
        count = 0
        for row in relevance_rows:
            sqlite_story_id = row['story_id']
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                postgres_cursor.execute("""
                    INSERT INTO user_story_relevance (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, story_id) DO NOTHING
                """, (row['user_id'], postgres_story_id, bool(row['is_relevant']), row['relevance_score'], row['relevance_reasoning'], row['calculated_at']))
                count += 1
        
        print(f"✅ Migrated {count} relevance records")
        
        # Migrate user_interactions
        print("📋 Migrating user_interactions...")
        sqlite_cursor.execute("SELECT * FROM user_interactions")
        interaction_rows = sqlite_cursor.fetchall()
        print(f"Found {len(interaction_rows)} interaction records in SQLite")
        
        count = 0
        for row in interaction_rows:
            sqlite_story_id = row['story_id']
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                postgres_cursor.execute("""
                    INSERT INTO user_interactions (user_id, story_id, interaction_type, timestamp, duration_seconds)
                    VALUES (%s, %s, %s, %s, %s)
                """, (row['user_id'], postgres_story_id, row['interaction_type'], row['timestamp'], row['duration_seconds']))
                count += 1
        
        print(f"✅ Migrated {count} interaction records")
        
        postgres_conn.commit()
        print("✅ All remaining data migrated successfully!")
        
    except Exception as e:
        print(f"❌ REAL ERROR: {str(e)}")
        print(f"❌ ERROR TYPE: {type(e).__name__}")
        postgres_conn.rollback()
        raise  # Re-raise to see full traceback
    finally:
        sqlite_conn.close()
        postgres_conn.close()

if __name__ == "__main__":
    print("🔧 Migration with Real Error Reporting")
    migrate_remaining_data()