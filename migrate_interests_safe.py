#!/usr/bin/env python3
"""
Migrate interests with safe user handling
"""

import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_interests_safe():
    sqlite_conn = sqlite3.connect("hn_scraper.db")
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # First, check for missing users and add them
        print("🔍 Checking for missing users...")
        sqlite_cursor.execute("""
            SELECT DISTINCT uiw.user_id, u.email, u.name, u.created_at, u.last_active_at
            FROM user_interest_weights uiw
            LEFT JOIN users u ON uiw.user_id = u.user_id
        """)
        
        interest_users = sqlite_cursor.fetchall()
        
        for user_row in interest_users:
            user_id = user_row[0]
            email = user_row[1] or f"user-{user_id[:8]}@example.com"
            name = user_row[2] or f"User {user_id[:8]}"
            created_at = user_row[3] or "2024-01-01T00:00:00"
            last_active_at = user_row[4]
            
            # Check if user exists in PostgreSQL
            postgres_cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not postgres_cursor.fetchone():
                print(f"   ➕ Adding missing user: {email}")
                postgres_cursor.execute("""
                    INSERT INTO users (user_id, email, name, created_at, last_active_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id, email, name, created_at, last_active_at))
        
        postgres_conn.commit()
        
        # Now migrate user_interest_weights safely
        print("📋 Migrating user_interest_weights...")
        sqlite_cursor.execute("SELECT * FROM user_interest_weights")
        user_interest_rows = sqlite_cursor.fetchall()
        print(f"Found {len(user_interest_rows)} user interest records")
        
        count = 0
        for row in user_interest_rows:
            postgres_cursor.execute("""
                INSERT INTO user_interest_weights (user_id, keyword, weight, category, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, keyword) DO NOTHING
            """, (row['user_id'], row['keyword'], row['weight'], row['category'], row['updated_at']))
            count += 1
        
        print(f"✅ Migrated {count} user interest weights")
        
        postgres_conn.commit()
        print("🎉 Safe interest migration completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        postgres_conn.rollback()
    finally:
        sqlite_conn.close()
        postgres_conn.close()

if __name__ == "__main__":
    migrate_interests_safe()