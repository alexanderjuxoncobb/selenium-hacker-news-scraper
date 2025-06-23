#!/usr/bin/env python3
"""
Fix the ID mapping issue between SQLite and PostgreSQL
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3
import psycopg2

# Load environment variables
load_dotenv()

def create_id_mapping():
    """Create a mapping between SQLite IDs and PostgreSQL IDs"""
    
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    print("🔄 Creating ID mapping between SQLite and PostgreSQL...")
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_url)
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Get all stories from SQLite with their original IDs
        sqlite_cursor.execute("SELECT id, title, url, date, rank FROM stories ORDER BY id")
        sqlite_stories = sqlite_cursor.fetchall()
        
        # Create a mapping from SQLite ID to PostgreSQL ID
        id_mapping = {}
        
        print("📋 Building ID mapping...")
        for sqlite_story in sqlite_stories:
            sqlite_id = sqlite_story['id']
            title = sqlite_story['title']
            url = sqlite_story['url']
            date = sqlite_story['date']
            rank = sqlite_story['rank']
            
            # Find the corresponding story in PostgreSQL
            postgres_cursor.execute("""
                SELECT id FROM stories 
                WHERE title = %s AND url = %s AND date = %s AND rank = %s
                LIMIT 1
            """, (title, url, date, rank))
            
            pg_result = postgres_cursor.fetchone()
            if pg_result:
                postgres_id = pg_result[0]
                id_mapping[sqlite_id] = postgres_id
                if len(id_mapping) % 50 == 0:
                    print(f"   Mapped {len(id_mapping)} stories...")
            else:
                print(f"   ⚠️  Could not find PostgreSQL match for SQLite story {sqlite_id}: {title[:50]}...")
        
        print(f"✅ Created mapping for {len(id_mapping)} stories")
        
        # Now migrate user_story_relevance with corrected IDs
        print("📋 Migrating user_story_relevance with corrected IDs...")
        
        sqlite_cursor.execute("SELECT * FROM user_story_relevance")
        relevance_rows = sqlite_cursor.fetchall()
        
        count = 0
        skipped = 0
        for row in relevance_rows:
            row_dict = dict(row)
            sqlite_story_id = row_dict.get('story_id')
            
            # Map to PostgreSQL ID
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                values = [
                    row_dict.get('user_id'),
                    postgres_story_id,  # Use mapped PostgreSQL ID
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
                    print(f"   ⚠️  Error inserting relevance: {e}")
                    break
            else:
                skipped += 1
        
        print(f"   ✅ Migrated {count} relevance records (skipped {skipped} with missing stories)")
        
        # Migrate user_interactions with corrected IDs
        print("📋 Migrating user_interactions with corrected IDs...")
        
        sqlite_cursor.execute("SELECT * FROM user_interactions")
        interaction_rows = sqlite_cursor.fetchall()
        
        count = 0
        skipped = 0
        for row in interaction_rows:
            row_dict = dict(row)
            sqlite_story_id = row_dict.get('story_id')
            
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                values = [
                    row_dict.get('user_id'),
                    postgres_story_id,  # Use mapped PostgreSQL ID
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
                    print(f"   ⚠️  Error inserting interaction: {e}")
                    break
            else:
                skipped += 1
        
        print(f"   ✅ Migrated {count} interaction records (skipped {skipped} with missing stories)")
        
        # Migrate story_notes with corrected IDs
        print("📋 Migrating story_notes with corrected IDs...")
        
        sqlite_cursor.execute("SELECT * FROM story_notes")
        notes_rows = sqlite_cursor.fetchall()
        
        count = 0
        skipped = 0
        for row in notes_rows:
            row_dict = dict(row)
            sqlite_story_id = row_dict.get('story_id')
            
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                values = [
                    row_dict.get('user_id'),
                    postgres_story_id,  # Use mapped PostgreSQL ID
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
                    print(f"   ⚠️  Error inserting note: {e}")
                    break
            else:
                skipped += 1
        
        print(f"   ✅ Migrated {count} story notes (skipped {skipped} with missing stories)")
        
        # Commit all changes
        postgres_conn.commit()
        print("✅ ID mapping migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during ID mapping migration: {str(e)}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def main():
    print("🚀 ID Mapping Fix Tool")
    print("=" * 50)
    
    if create_id_mapping():
        print("\n✅ All data migrated with correct ID mapping!")
    else:
        print("\n❌ Migration failed")

if __name__ == "__main__":
    main()