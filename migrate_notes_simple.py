#!/usr/bin/env python3
"""
Simple, correct notes migration
"""

import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_notes():
    sqlite_conn = sqlite3.connect("hn_scraper.db")
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Get story ID mapping
        print("Building story mapping...")
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
        
        print(f"Mapped {len(id_mapping)} stories")
        
        # Migrate notes with CORRECT column name
        sqlite_cursor.execute("SELECT user_id, story_id, notes, created_at, updated_at FROM story_notes")
        notes = sqlite_cursor.fetchall()
        
        count = 0
        for note in notes:
            sqlite_story_id = note['story_id']
            if sqlite_story_id in id_mapping:
                postgres_story_id = id_mapping[sqlite_story_id]
                
                # Check if user exists in PostgreSQL
                postgres_cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (note['user_id'],))
                if not postgres_cursor.fetchone():
                    # Add missing user
                    postgres_cursor.execute("""
                        INSERT INTO users (user_id, email, name, created_at, last_active_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (note['user_id'], f"user-{note['user_id'][:8]}@example.com", f"User {note['user_id'][:8]}", note['created_at'], note['updated_at']))
                
                # Insert note with correct column names
                postgres_cursor.execute("""
                    INSERT INTO story_notes (user_id, story_id, notes, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, story_id) DO UPDATE SET
                    notes = EXCLUDED.notes, updated_at = EXCLUDED.updated_at
                """, (note['user_id'], postgres_story_id, note['notes'], note['created_at'], note['updated_at']))
                
                count += 1
                print(f"✅ Migrated note: {note['notes'][:30]}...")
        
        postgres_conn.commit()
        print(f"✅ Successfully migrated {count} notes")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

if __name__ == "__main__":
    print("🔧 Simple Notes Migration")
    migrate_notes()