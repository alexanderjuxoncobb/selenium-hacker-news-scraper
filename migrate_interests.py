#!/usr/bin/env python3
"""
Migrate the missing interest tables
"""

import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_interests():
    sqlite_conn = sqlite3.connect("hn_scraper.db")
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Migrate interest_weights
        print("📋 Migrating interest_weights...")
        sqlite_cursor.execute("SELECT * FROM interest_weights")
        interest_rows = sqlite_cursor.fetchall()
        print(f"Found {len(interest_rows)} interest weight records")
        
        count = 0
        for row in interest_rows:
            postgres_cursor.execute("""
                INSERT INTO interest_weights (keyword, weight, category, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (keyword) DO NOTHING
            """, (row['keyword'], row['weight'], row['category'], row['updated_at']))
            count += 1
        
        print(f"✅ Migrated {count} interest weights")
        
        # Migrate user_interest_weights
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
        print("🎉 Interest migration completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        postgres_conn.rollback()
    finally:
        sqlite_conn.close()
        postgres_conn.close()

if __name__ == "__main__":
    migrate_interests()