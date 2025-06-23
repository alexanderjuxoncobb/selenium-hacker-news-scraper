#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

print('📊 FINAL PostgreSQL Migration Results:')
print('=' * 45)

tables = [
    ('users', 50),
    ('stories', 145),
    ('interest_weights', 25),
    ('user_interest_weights', 407),
    ('user_story_relevance', 1435),
    ('user_interactions', 8),
    ('story_notes', 5)
]

total_migrated = 0
for table, expected in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    actual = cursor.fetchone()[0]
    status = '✅' if actual == expected else '⚠️ '
    print(f'{table:20}: {actual:4} / {expected} {status}')
    total_migrated += actual

print('=' * 45)
print(f'TOTAL RECORDS MIGRATED: {total_migrated}')
conn.close()