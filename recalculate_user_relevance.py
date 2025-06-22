#!/usr/bin/env python3
"""
Manual script to recalculate relevance scores for existing users.
This is useful when:
- A user updates their interests
- You want to reprocess stories with updated AI models
- A new user was created but stories weren't processed
"""

import argparse
import sys
from datetime import datetime
from dashboard.database import DatabaseManager

def main():
    parser = argparse.ArgumentParser(
        description='Recalculate story relevance for users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all stories for a specific user (last 30 days)
  python recalculate_user_relevance.py --user-id 7c742a24-5825-4fe2-9a7e-6a21a8442bc1
  
  # Process only last 7 days for a user
  python recalculate_user_relevance.py --user-id 7c742a24-5825-4fe2-9a7e-6a21a8442bc1 --days 7
  
  # Process all users (last 7 days)
  python recalculate_user_relevance.py --all-users --days 7
  
  # List all users
  python recalculate_user_relevance.py --list-users
        """
    )
    
    parser.add_argument('--user-id', help='User ID to process')
    parser.add_argument('--all-users', action='store_true', help='Process all users')
    parser.add_argument('--days', type=int, default=30, help='Number of days to process (default: 30)')
    parser.add_argument('--list-users', action='store_true', help='List all users and exit')
    parser.add_argument('--force', action='store_true', help='Force recalculation even if already processed')
    
    args = parser.parse_args()
    
    # Initialize database
    db = DatabaseManager()
    
    # List users if requested
    if args.list_users:
        users = db.get_all_users()
        print(f"\n📋 Found {len(users)} users:\n")
        for user in users:
            interests = db.get_user_interests_by_category(user.user_id)
            interest_count = sum(len(items) for items in interests.values())
            print(f"  • {user.name or 'No name'} ({user.email})")
            print(f"    ID: {user.user_id}")
            print(f"    Interests: {interest_count} topics")
            print(f"    Created: {user.created_at}")
            print()
        return
    
    # Validate arguments
    if not args.user_id and not args.all_users:
        parser.error("Please specify either --user-id or --all-users")
    
    # Process users
    users_to_process = []
    
    if args.all_users:
        users_to_process = db.get_all_users()
        print(f"🔄 Processing all {len(users_to_process)} users...")
    else:
        user = db.get_user(args.user_id)
        if not user:
            print(f"❌ User {args.user_id} not found!")
            sys.exit(1)
        users_to_process = [user]
    
    # Process each user
    total_stats = {
        'users_processed': 0,
        'total_stories_processed': 0,
        'total_relevant_found': 0
    }
    
    for user in users_to_process:
        print(f"\n👤 Processing user: {user.name or user.email} ({user.user_id})")
        
        # Check if user has interests
        interests = db.get_user_interests_by_category(user.user_id)
        if not any(interests.values()):
            print(f"  ⚠️  User has no interests configured, skipping...")
            continue
        
        interest_count = sum(len(items) for items in interests.values())
        print(f"  📌 Found {interest_count} interests")
        
        # Process stories
        print(f"  🔄 Processing last {args.days} days of stories...")
        start_time = datetime.now()
        
        try:
            stats = db.batch_process_user_relevance(user.user_id, limit_days=args.days)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  ✅ Completed in {elapsed:.1f} seconds")
            print(f"     - Total stories: {stats['total_stories']}")
            print(f"     - Processed: {stats['processed_stories']}")
            print(f"     - Cached: {stats['cached_stories']}")
            print(f"     - Relevant: {stats['relevant_stories']}")
            
            # Update totals
            total_stats['users_processed'] += 1
            total_stats['total_stories_processed'] += stats['processed_stories']
            total_stats['total_relevant_found'] += stats['relevant_stories']
            
        except Exception as e:
            print(f"  ❌ Error processing user: {e}")
            continue
    
    # Print summary
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    print(f"Users processed: {total_stats['users_processed']}")
    print(f"Stories processed: {total_stats['total_stories_processed']}")
    print(f"Relevant stories found: {total_stats['total_relevant_found']}")
    
    if total_stats['total_stories_processed'] > 0:
        relevance_rate = (total_stats['total_relevant_found'] / total_stats['total_stories_processed']) * 100
        print(f"Average relevance rate: {relevance_rate:.1f}%")

if __name__ == "__main__":
    main()