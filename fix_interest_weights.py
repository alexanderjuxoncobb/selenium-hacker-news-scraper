#!/usr/bin/env python3
import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Quick interest_weights migration
sqlite_conn = sqlite3.connect('hn_scraper.db')
postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

sqlite_cursor = sqlite_conn.cursor()
postgres_cursor = postgres_conn.cursor()

print("Checking interest_weights...")
sqlite_cursor.execute('SELECT keyword, weight, category, updated_at FROM interest_weights')
rows = sqlite_cursor.fetchall()
print(f"Found {len(rows)} interest weights in SQLite")

for row in rows:
    postgres_cursor.execute('''
        INSERT INTO interest_weights (keyword, weight, category, updated_at) 
        VALUES (%s, %s, %s, %s) 
        ON CONFLICT (keyword) DO NOTHING
    ''', row)

postgres_conn.commit()
print('✅ Interest weights migrated')

sqlite_conn.close()
postgres_conn.close()