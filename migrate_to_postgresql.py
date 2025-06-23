#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL
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
    """Migrate all data from SQLite to PostgreSQL"""
    
    # Get database URLs
    sqlite_path = "hn_scraper.db"
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url or not postgres_url.startswith('postgresql'):
        print("❌ Error: DATABASE_URL must be set to a PostgreSQL URL")
        print("Example: postgresql://user:password@localhost:5432/hn_scraper")
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
        
        # Migrate data table by table
        tables = [
            'users',
            'interest_weights',
            'stories',
            'user_interest_weights',
            'user_story_relevance',
            'user_interactions',
            'story_notes'
        ]
        
        for table in tables:
            print(f"📋 Migrating {table}...")
            migrate_table(sqlite_conn, postgres_conn, table)
        
        # Commit all changes
        postgres_conn.commit()
        print("✅ Migration completed successfully!")
        
        # Show statistics
        show_migration_stats(postgres_conn)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_table(sqlite_conn, postgres_conn, table_name):
    """Migrate a single table from SQLite to PostgreSQL"""
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️  No data in {table_name}")
        return
    
    # Get column names
    columns = [description[0] for description in sqlite_cursor.description]
    
    # Skip the 'id' column for PostgreSQL (uses SERIAL)
    insert_columns = [col for col in columns if col != 'id']
    
    # Create placeholder string for PostgreSQL
    placeholders = ', '.join(['%s'] * len(insert_columns))
    column_names = ', '.join(insert_columns)
    
    # Insert data into PostgreSQL
    count = 0
    for row in rows:
        # Convert row to dict for easier handling
        row_dict = dict(zip(columns, row))
        
        # Prepare values (skip id)
        values = [row_dict[col] for col in insert_columns]
        
        # Handle boolean conversion
        for i, col in enumerate(insert_columns):
            if col in ['is_relevant', 'was_cached'] and values[i] is not None:
                values[i] = bool(values[i])
        
        try:
            # Insert with conflict handling for unique constraints
            if table_name == 'users':
                postgres_cursor.execute(f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                    ON CONFLICT (user_id) DO NOTHING
                """, values)
            elif table_name == 'interest_weights':
                postgres_cursor.execute(f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                    ON CONFLICT (keyword) DO NOTHING
                """, values)
            elif table_name == 'stories':
                postgres_cursor.execute(f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                    ON CONFLICT (date, rank) DO NOTHING
                """, values)
            elif table_name in ['user_interest_weights', 'user_story_relevance', 'story_notes']:
                # These have composite unique constraints
                postgres_cursor.execute(f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """, values)
            else:
                postgres_cursor.execute(f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                """, values)
            
            count += 1
        except Exception as e:
            print(f"   ⚠️  Error inserting row in {table_name}: {str(e)}")
            continue
    
    print(f"   ✅ Migrated {count} rows")

def show_migration_stats(postgres_conn):
    """Show statistics after migration"""
    cursor = postgres_conn.cursor()
    
    print("\n📊 Migration Statistics:")
    
    tables = [
        ('users', 'Users'),
        ('stories', 'Stories'),
        ('user_story_relevance', 'User Story Relevance'),
        ('user_interactions', 'User Interactions'),
        ('interest_weights', 'Interest Weights'),
        ('user_interest_weights', 'User Interest Weights'),
        ('story_notes', 'Story Notes')
    ]
    
    for table, display_name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {display_name}: {count:,} records")

def verify_migration():
    """Verify that the migration was successful"""
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url or not postgres_url.startswith('postgresql'):
        print("❌ Error: DATABASE_URL must be set to a PostgreSQL URL")
        return False
    
    try:
        # Test PostgreSQL connection and basic queries
        from database import DatabaseManager
        db = DatabaseManager(postgres_url)
        
        # Get some basic stats
        dates = db.get_available_dates()
        users = db.get_all_users()
        
        print(f"\n✅ PostgreSQL database is working!")
        print(f"   Available dates: {len(dates)}")
        print(f"   Total users: {len(users)}")
        
        if dates:
            latest_date = dates[0]
            stats = db.get_stats_by_date(latest_date)
            print(f"   Latest date ({latest_date}): {stats['total_stories']} stories")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying migration: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 SQLite to PostgreSQL Migration Tool")
    print("=" * 50)
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("❌ Error: DATABASE_URL environment variable not set")
        print("Please set it in your .env file:")
        print("DATABASE_URL=postgresql://user:password@localhost:5432/hn_scraper")
        sys.exit(1)
    
    # Run migration
    if migrate_data():
        print("\n🎉 Migration completed successfully!")
        
        # Verify the migration
        print("\n🔍 Verifying migration...")
        verify_migration()
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)