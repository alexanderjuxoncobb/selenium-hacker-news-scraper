#!/usr/bin/env python3
"""
Easy migration script - Run this locally to migrate your SQLite data to Railway PostgreSQL
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("🚀 Easy Railway Migration Tool")
    print("=" * 50)
    
    # Check for local SQLite database
    if not os.path.exists('hn_scraper.db'):
        print("❌ Error: hn_scraper.db not found in current directory")
        return
    
    # Get Railway PostgreSQL URL
    print("\n📋 Instructions:")
    print("1. Go to your Railway project dashboard")
    print("2. Click on the PostgreSQL database service")
    print("3. Go to 'Variables' tab")
    print("4. Copy the DATABASE_URL value")
    print("5. Paste it below")
    print()
    
    postgres_url = input("Enter your Railway PostgreSQL DATABASE_URL: ").strip()
    
    if not postgres_url.startswith('postgresql://'):
        print("❌ Error: Invalid PostgreSQL URL")
        return
    
    # Set the environment variable temporarily
    os.environ['DATABASE_URL'] = postgres_url
    
    # Import and run migration
    print("\n🔄 Starting migration...")
    try:
        from migrate_to_postgresql import migrate_data, verify_migration
        
        if migrate_data():
            print("\n✅ Migration completed!")
            print("\n🔍 Verifying migration...")
            verify_migration()
        else:
            print("\n❌ Migration failed")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure you have psycopg2-binary installed:")
        print("pip install psycopg2-binary")

if __name__ == "__main__":
    main()