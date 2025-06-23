#!/usr/bin/env python3
"""
Fix the notes migration with correct column name mapping
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3
import psycopg2

# Load environment variables
load_dotenv()

def migrate_notes_with_correct_mapping():
    """Migrate story notes with SQLite 'note' -> PostgreSQL 'notes' mapping"""
    
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    print("🔄 Migrating story notes with correct column mapping...")
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_url)
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # First, get the story ID mapping (like before)
        print("📋 Building story ID mapping...")
        sqlite_cursor.execute("SELECT id, title, url, date, rank FROM stories ORDER BY id")
        sqlite_stories = sqlite_cursor.fetchall()
        
        id_mapping = {}
        for sqlite_story in sqlite_stories:
            sqlite_id = sqlite_story['id']
            title = sqlite_story['title']
            url = sqlite_story['url']
            date = sqlite_story['date']
            rank = sqlite_story['rank']
            
            postgres_cursor.execute("""
                SELECT id FROM stories 
                WHERE title = %s AND url = %s AND date = %s AND rank = %s
                LIMIT 1
            """, (title, url, date, rank))
            
            pg_result = postgres_cursor.fetchone()
            if pg_result:
                postgres_id = pg_result[0]
                id_mapping[sqlite_id] = postgres_id
        
        print(f"✅ Story ID mapping ready ({len(id_mapping)} stories)")
        
        # Now migrate story notes with correct column mapping
        print("📋 Migrating story notes with corrected column mapping...")
        
        sqlite_cursor.execute("SELECT * FROM story_notes")
        notes_rows = sqlite_cursor.fetchall()
        
        print(f"Found {len(notes_rows)} notes to migrate")
        
        count = 0
        skipped = 0
        for row in notes_rows:
            row_dict = dict(row)
            sqlite_story_id = row_dict.get('story_id')
            
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                # Map SQLite 'note' column to PostgreSQL 'notes' column
                values = [
                    row_dict.get('user_id'),
                    postgres_story_id,
                    row_dict.get('note'),  # SQLite column is 'note'
                    row_dict.get('created_at'),
                    row_dict.get('updated_at')
                ]
                
                try:
                    postgres_cursor.execute("""
                        INSERT INTO story_notes (user_id, story_id, notes, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, story_id) DO UPDATE SET
                        notes = EXCLUDED.notes,
                        updated_at = EXCLUDED.updated_at
                    """, values)
                    count += 1
                    print(f"   ✅ Migrated note for story {postgres_story_id}: {row_dict.get('note', '')[:50]}...")
                except Exception as e:
                    print(f"   ⚠️  Error inserting note: {e}")
                    break
            else:
                skipped += 1
                print(f"   ⚠️  Skipped note for missing story {sqlite_story_id}")
        
        print(f"   ✅ Migrated {count} story notes (skipped {skipped} with missing stories)")
        
        # Commit changes
        postgres_conn.commit()
        print("✅ Notes migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during notes migration: {str(e)}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def main():
    print("🚀 Story Notes Migration Fix")
    print("=" * 50)
    
    if migrate_notes_with_correct_mapping():
        print("\n✅ All story notes migrated successfully!")
    else:
        print("\n❌ Notes migration failed")

if __name__ == "__main__":
    main()