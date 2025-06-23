#!/usr/bin/env python3
"""
Fixed migration script that handles schema differences between SQLite and PostgreSQL
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3
import psycopg2
from datetime import datetime
import json

# Add the dashboard directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

# Load environment variables
load_dotenv()

def migrate_data():
    """Migrate all data from SQLite to PostgreSQL with schema fixes"""
    
    # Get database URLs
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url or not postgres_url.startswith('postgresql'):
        print("❌ Error: DATABASE_URL must be set to a PostgreSQL URL")
        return False
    
    if not os.path.exists(sqlite_path):
        print(f"❌ Error: SQLite database not found at {sqlite_path}")
        return False
    
    print(f"📊 Migrating from SQLite ({sqlite_path}) to PostgreSQL...")
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_url)
    
    try:
        # First, create the PostgreSQL database schema
        print("📝 Creating PostgreSQL schema...")
        from database import DatabaseManager
        pg_db = DatabaseManager(postgres_url)
        print("✅ Schema created")
        
        # Migrate data table by table with custom handling
        migrate_users(sqlite_conn, postgres_conn)
        migrate_interest_weights(sqlite_conn, postgres_conn)
        migrate_stories(sqlite_conn, postgres_conn)
        migrate_user_interest_weights(sqlite_conn, postgres_conn)
        migrate_user_story_relevance(sqlite_conn, postgres_conn)
        migrate_user_interactions(sqlite_conn, postgres_conn)
        migrate_story_notes(sqlite_conn, postgres_conn)
        
        # Commit all changes
        postgres_conn.commit()
        print("✅ Migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_stories(sqlite_conn, postgres_conn):
    """Migrate stories table with schema fixes"""
    print("📋 Migrating stories...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get all stories from SQLite
    sqlite_cursor.execute("SELECT * FROM stories")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print("   ⚠️  No data in stories")
        return
    
    count = 0
    for row in rows:
        row_dict = dict(row)
        
        # Skip the old is_relevant and relevance_score columns
        # PostgreSQL schema doesn't have these
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
            count += 1
        except Exception as e:
            print(f"   ⚠️  Error inserting story row: {e}")
    
    print(f"   ✅ Migrated {count} rows")

def migrate_users(sqlite_conn, postgres_conn):
    """Migrate users table"""
    print("📋 Migrating users...")
    
    sqlite_cursor = sqlite_conn.cursor() 
    postgres_cursor = postgres_conn.cursor()
    
    try:
        sqlite_cursor.execute("SELECT * FROM users")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print("   ⚠️  No data in users")
            return
        
        count = 0
        for row in rows:
            row_dict = dict(row)
            values = [
                row_dict.get('user_id'),
                row_dict.get('email'),
                row_dict.get('name'),
                row_dict.get('created_at'),
                row_dict.get('last_active_at')
            ]
            
            postgres_cursor.execute("""
                INSERT INTO users (user_id, email, name, created_at, last_active_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, values)
            count += 1
        
        print(f"   ✅ Migrated {count} rows")
    except Exception as e:
        print(f"   ⚠️  Table users doesn't exist in SQLite, skipping")

def migrate_interest_weights(sqlite_conn, postgres_conn):
    """Migrate interest_weights table"""
    print("📋 Migrating interest_weights...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    try:
        sqlite_cursor.execute("SELECT * FROM interest_weights")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print("   ⚠️  No data in interest_weights")
            return
        
        count = 0
        for row in rows:
            row_dict = dict(row)
            values = [
                row_dict.get('keyword'),
                row_dict.get('weight'),
                row_dict.get('category'),
                row_dict.get('updated_at')
            ]
            
            postgres_cursor.execute("""
                INSERT INTO interest_weights (keyword, weight, category, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (keyword) DO NOTHING  
            """, values)
            count += 1
        
        print(f"   ✅ Migrated {count} rows")
    except Exception as e:
        print(f"   ⚠️  Table interest_weights doesn't exist in SQLite, skipping")

def migrate_user_interest_weights(sqlite_conn, postgres_conn):
    """Migrate user_interest_weights table"""
    print("📋 Migrating user_interest_weights...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    try:
        sqlite_cursor.execute("SELECT * FROM user_interest_weights")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print("   ⚠️  No data in user_interest_weights")
            return
        
        count = 0
        for row in rows:
            row_dict = dict(row)
            values = [
                row_dict.get('user_id'),
                row_dict.get('keyword'),
                row_dict.get('weight'),
                row_dict.get('category'),
                row_dict.get('updated_at')
            ]
            
            postgres_cursor.execute("""
                INSERT INTO user_interest_weights (user_id, keyword, weight, category, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, keyword) DO NOTHING
            """, values)
            count += 1
        
        print(f"   ✅ Migrated {count} rows")
    except Exception as e:
        print(f"   ⚠️  Table user_interest_weights doesn't exist in SQLite, skipping")

def migrate_user_story_relevance(sqlite_conn, postgres_conn):
    """Migrate user_story_relevance table"""
    print("📋 Migrating user_story_relevance...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    try:
        sqlite_cursor.execute("SELECT * FROM user_story_relevance")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print("   ⚠️  No data in user_story_relevance")
            return
        
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
            
            postgres_cursor.execute("""
                INSERT INTO user_story_relevance (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, story_id) DO NOTHING
            """, values)
            count += 1
        
        print(f"   ✅ Migrated {count} rows")
    except Exception as e:
        print(f"   ⚠️  Table user_story_relevance doesn't exist in SQLite, skipping")

def migrate_user_interactions(sqlite_conn, postgres_conn):
    """Migrate user_interactions table"""
    print("📋 Migrating user_interactions...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    try:
        sqlite_cursor.execute("SELECT * FROM user_interactions")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print("   ⚠️  No data in user_interactions")
            return
        
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
            
            postgres_cursor.execute("""
                INSERT INTO user_interactions (user_id, story_id, interaction_type, timestamp, duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
            """, values)
            count += 1
        
        print(f"   ✅ Migrated {count} rows")
    except Exception as e:
        print(f"   ⚠️  Table user_interactions doesn't exist in SQLite, skipping")

def migrate_story_notes(sqlite_conn, postgres_conn):
    """Migrate story_notes table"""
    print("📋 Migrating story_notes...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    try:
        sqlite_cursor.execute("SELECT * FROM story_notes")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print("   ⚠️  No data in story_notes")
            return
        
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
            
            postgres_cursor.execute("""
                INSERT INTO story_notes (user_id, story_id, note, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, story_id) DO NOTHING
            """, values)
            count += 1
        
        print(f"   ✅ Migrated {count} rows")
    except Exception as e:
        print(f"   ⚠️  Table story_notes doesn't exist in SQLite, skipping")

def main():
    """Easy migration with fixed schema handling"""
    print("🚀 Fixed Railway Migration Tool")
    print("=" * 50)
    
    # Check for environment variable first
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url:
        print("\n📋 Instructions:")
        print("1. Go to your Railway project dashboard")
        print("2. Click on the PostgreSQL database service")
        print("3. Go to 'Connect' tab (not Variables)")
        print("4. Copy the external DATABASE_URL")
        print("5. Paste it below")
        print()
        
        postgres_url = input("Enter your Railway PostgreSQL DATABASE_URL: ").strip()
    
    if not postgres_url.startswith('postgresql://'):
        print("❌ Error: Invalid PostgreSQL URL")
        return
    
    # Set the environment variable
    os.environ['DATABASE_URL'] = postgres_url
    
    # Check for local SQLite database
    if not os.path.exists('hn_scraper.db'):
        print("❌ Error: hn_scraper.db not found in current directory")
        return
    
    print("\n🔄 Starting fixed migration...")
    if migrate_data():
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed")

if __name__ == "__main__":
    main()