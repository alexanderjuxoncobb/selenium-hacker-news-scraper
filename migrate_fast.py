#!/usr/bin/env python3
"""
Fast migration with progress updates
"""

import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_fast():
    sqlite_conn = sqlite3.connect("hn_scraper.db")
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Quick story ID mapping
        print("📋 Quick story mapping...")
        sqlite_cursor.execute("SELECT id, title, url, date, rank FROM stories")
        id_mapping = {}
        
        for row in sqlite_cursor.fetchall():
            sqlite_id = row['id']
            postgres_cursor.execute("SELECT id FROM stories WHERE title = %s LIMIT 1", (row['title'],))
            pg_result = postgres_cursor.fetchone()
            if pg_result:
                id_mapping[sqlite_id] = pg_result[0]
        
        print(f"✅ Mapped {len(id_mapping)} stories")
        
        # Fast relevance migration with progress
        print("📋 Fast relevance migration...")
        sqlite_cursor.execute("SELECT * FROM user_story_relevance")
        
        batch = []
        total = 0
        
        for i, row in enumerate(sqlite_cursor.fetchall()):
            if row['story_id'] in id_mapping:
                postgres_story_id = id_mapping[row['story_id']]
                batch.append((row['user_id'], postgres_story_id, bool(row['is_relevant']), 
                             row['relevance_score'], row['relevance_reasoning'], row['calculated_at']))
                total += 1
                
                # Process in batches of 100
                if len(batch) >= 100:
                    postgres_cursor.executemany("""
                        INSERT INTO user_story_relevance (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, story_id) DO NOTHING
                    """, batch)
                    print(f"   Processed {total} relevance records...")
                    batch = []
        
        # Process remaining batch
        if batch:
            postgres_cursor.executemany("""
                INSERT INTO user_story_relevance (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, story_id) DO NOTHING
            """, batch)
        
        print(f"✅ Migrated {total} relevance records")
        
        # Fast interactions migration
        print("📋 Fast interactions migration...")
        sqlite_cursor.execute("SELECT * FROM user_interactions")
        
        batch = []
        total = 0
        
        for row in sqlite_cursor.fetchall():
            if row['story_id'] in id_mapping:
                postgres_story_id = id_mapping[row['story_id']]
                batch.append((row['user_id'], postgres_story_id, row['interaction_type'], 
                             row['timestamp'], row['duration_seconds']))
                total += 1
        
        if batch:
            postgres_cursor.executemany("""
                INSERT INTO user_interactions (user_id, story_id, interaction_type, timestamp, duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
            """, batch)
        
        print(f"✅ Migrated {total} interaction records")
        
        postgres_conn.commit()
        print("🎉 Fast migration completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        postgres_conn.rollback()
    finally:
        sqlite_conn.close()
        postgres_conn.close()

if __name__ == "__main__":
    migrate_fast()