#!/usr/bin/env python3
"""
Robust migration script that handles foreign key constraints properly
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3
import psycopg2

# Load environment variables
load_dotenv()

def check_missing_users(sqlite_conn, postgres_conn):
    """Check for users that exist in SQLite but not in PostgreSQL"""
    print("🔍 Checking for missing users...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get all user_ids from SQLite that are referenced in relevance table
    sqlite_cursor.execute("""
        SELECT DISTINCT r.user_id, u.email, u.name, u.created_at, u.last_active_at
        FROM user_story_relevance r 
        JOIN users u ON r.user_id = u.user_id
    """)
    sqlite_users = sqlite_cursor.fetchall()
    
    # Check which ones are missing in PostgreSQL
    missing_users = []
    for user_row in sqlite_users:
        user_id = user_row[0]
        postgres_cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not postgres_cursor.fetchone():
            missing_users.append(user_row)
    
    if missing_users:
        print(f"   ⚠️  Found {len(missing_users)} missing users, adding them...")
        for user_row in missing_users:
            values = list(user_row)  # user_id, email, name, created_at, last_active_at
            try:
                postgres_cursor.execute("""
                    INSERT INTO users (user_id, email, name, created_at, last_active_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, values)
                print(f"   ✅ Added user: {values[1]}")
            except Exception as e:
                print(f"   ❌ Error adding user {values[0]}: {e}")
        
        postgres_conn.commit()
    else:
        print("   ✅ All users already exist")

def check_missing_stories(sqlite_conn, postgres_conn):
    """Check for stories that exist in SQLite but not in PostgreSQL"""
    print("🔍 Checking for missing stories...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get all story_ids from SQLite that are referenced in relevance table
    sqlite_cursor.execute("""
        SELECT DISTINCT r.story_id 
        FROM user_story_relevance r
    """)
    referenced_story_ids = [row[0] for row in sqlite_cursor.fetchall()]
    
    missing_stories = []
    for story_id in referenced_story_ids:
        postgres_cursor.execute("SELECT id FROM stories WHERE id = %s", (story_id,))
        if not postgres_cursor.fetchone():
            # Get the full story data from SQLite
            sqlite_cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
            story_row = sqlite_cursor.fetchone()
            if story_row:
                missing_stories.append(story_row)
    
    if missing_stories:
        print(f"   ⚠️  Found {len(missing_stories)} missing stories, adding them...")
        for story_row in missing_stories:
            row_dict = dict(story_row)
            values = [
                row_dict.get('date'),
                row_dict.get('rank'),
                row_dict.get('story_id'),
                row_dict.get('title'),
                row_dict.get('url'),
                row_dict.get('points'),
                row_dict.get('author'),
                row_dict.get('comments_count'),
                row_dict.get('hn_discussion_url'),
                row_dict.get('article_summary'),
                row_dict.get('comments_analysis'),
                row_dict.get('scraped_at'),
                bool(row_dict.get('was_cached', False)),
                row_dict.get('tags')
            ]
            
            try:
                postgres_cursor.execute("""
                    INSERT INTO stories (
                        date, rank, story_id, title, url, points, author, 
                        comments_count, hn_discussion_url, article_summary, 
                        comments_analysis, scraped_at, was_cached, tags
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, rank) DO NOTHING
                """, values)
                print(f"   ✅ Added story: {row_dict.get('title', 'Unknown')[:50]}...")
            except Exception as e:
                print(f"   ❌ Error adding story {story_id}: {e}")
        
        postgres_conn.commit()
    else:
        print("   ✅ All referenced stories already exist")

def migrate_missing_data():
    """Migrate the missing user interactions, relevance, and notes with FK handling"""
    
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url:
        print("❌ Error: DATABASE_URL not set")
        return False
    
    print("🔄 Migrating missing interaction data with FK handling...")
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_url)
    
    try:
        # First, ensure all referenced users and stories exist
        check_missing_users(sqlite_conn, postgres_conn)
        check_missing_stories(sqlite_conn, postgres_conn)
        
        # Now migrate user_story_relevance
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
                break  # Stop on first error to avoid spam
        
        print(f"   ✅ Migrated {count} relevance records")
        
        # Migrate user_interactions
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
                break
        
        print(f"   ✅ Migrated {count} interaction records")
        
        # Migrate story_notes
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
                break
        
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
    print("🚀 Robust Missing Data Migration Tool")
    print("=" * 50)
    
    if migrate_missing_data():
        print("\n✅ All missing data migrated successfully!")
    else:
        print("\n❌ Migration failed")

if __name__ == "__main__":
    main()