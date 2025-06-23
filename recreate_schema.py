#!/usr/bin/env python3
"""
Force recreate the complete PostgreSQL schema
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Add the dashboard directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

# Load environment variables
load_dotenv()

def recreate_schema():
    """Force recreate the complete PostgreSQL schema"""
    
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url:
        print("❌ Error: DATABASE_URL not set")
        return False
    
    print("🔄 Force recreating PostgreSQL schema...")
    
    try:
        from database import DatabaseManager
        
        # Initialize database manager which should create all tables
        print("📝 Creating database schema...")
        db = DatabaseManager(postgres_url)
        
        # Test that all tables were created
        conn = psycopg2.connect(postgres_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print("✅ Created tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        conn.close()
        
        expected_tables = ['users', 'stories', 'interest_weights', 'user_interest_weights', 
                          'user_story_relevance', 'user_interactions', 'story_notes']
        
        actual_tables = [table[0] for table in tables]
        missing_tables = [t for t in expected_tables if t not in actual_tables]
        
        if missing_tables:
            print(f"⚠️  Missing tables: {missing_tables}")
            return False
        else:
            print("✅ All required tables created successfully!")
            return True
        
    except Exception as e:
        print(f"❌ Error recreating schema: {str(e)}")
        return False

def main():
    print("🚀 PostgreSQL Schema Recreation")
    print("=" * 50)
    
    if recreate_schema():
        print("\n✅ Schema recreation completed!")
        print("🔄 Now you can re-run the migration scripts")
    else:
        print("\n❌ Schema recreation failed")

if __name__ == "__main__":
    main()