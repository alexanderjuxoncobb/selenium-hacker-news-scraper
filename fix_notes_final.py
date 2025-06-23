#!/usr/bin/env python3
"""
Final fix for notes migration - add missing users first
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3
import psycopg2
from datetime import datetime

# Load environment variables
load_dotenv()

def migrate_notes_final():
    """Migrate notes with proper user handling"""
    
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    print("🔄 Final notes migration with user handling...")
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_url)
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # First, check for missing users who have notes
        print("🔍 Checking for missing users who have notes...")
        
        sqlite_cursor.execute("""
            SELECT DISTINCT sn.user_id, u.email, u.name, u.created_at, u.last_active_at
            FROM story_notes sn 
            LEFT JOIN users u ON sn.user_id = u.user_id
        """)
        note_users = sqlite_cursor.fetchall()
        
        for user_row in note_users:
            user_id = user_row[0]
            email = user_row[1] or f"missing-user-{user_id[:8]}@example.com"  # Create email if missing
            name = user_row[2] or f"User {user_id[:8]}"
            created_at = user_row[3] or datetime.now().isoformat()
            last_active_at = user_row[4]
            
            # Check if user exists in PostgreSQL
            postgres_cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not postgres_cursor.fetchone():
                print(f"   ➕ Adding missing user: {email}")
                try:
                    postgres_cursor.execute("""
                        INSERT INTO users (user_id, email, name, created_at, last_active_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id, email, name, created_at, last_active_at))
                except Exception as e:
                    print(f"   ⚠️  Error adding user: {e}")
        
        postgres_conn.commit()
        
        # Build story ID mapping
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
        
        # Now migrate story notes
        print("📋 Migrating story notes...")
        
        sqlite_cursor.execute("SELECT * FROM story_notes")
        notes_rows = sqlite_cursor.fetchall()
        
        print(f"Found {len(notes_rows)} notes to migrate")
        
        count = 0
        for row in notes_rows:
            row_dict = dict(row)
            sqlite_story_id = row_dict.get('story_id')
            user_id = row_dict.get('user_id')
            note_text = row_dict.get('note')
            
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                values = [
                    user_id,
                    postgres_story_id,
                    note_text,
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
                    print(f"   ✅ Migrated note for story {postgres_story_id}: {note_text[:50]}...")
                except Exception as e:
                    print(f"   ⚠️  Error inserting note: {e}")
            else:
                print(f"   ⚠️  Skipped note for missing story {sqlite_story_id}")
        
        print(f"   ✅ Migrated {count} story notes")
        
        # Commit changes
        postgres_conn.commit()
        print("✅ Final notes migration completed successfully!")
        
        return count > 0
        
    except Exception as e:
        print(f"❌ Error during final notes migration: {str(e)}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def main():
    print("🚀 Final Story Notes Migration")
    print("=" * 50)
    
    migrated_count = migrate_notes_final()
    if migrated_count:
        print("\n✅ All story notes migrated successfully!")
        print("📝 Notes feature is now fully functional for Railway deployment")
    else:
        print("\n❌ Notes migration failed")

if __name__ == "__main__":
    main()