#!/usr/bin/env python3
"""
Multi-User Enhanced Hacker News Scraper
Processes stories for all users and sends personalized email digests
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Tuple

# Add dashboard directory to path to import database manager
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

from enhanced_scraper import EnhancedHackerNewsScraper
from email_sender import EmailNotifier
from database import DatabaseManager, User, UserInterestWeight

def get_all_users_with_interests(db: DatabaseManager) -> List[Tuple[User, List[UserInterestWeight]]]:
    """Get all users and their interest weights from the database"""
    all_users = db.get_all_users()
    users_with_interests = []
    
    for user in all_users:
        user_interests = db.get_user_interest_weights(user.user_id)
        users_with_interests.append((user, user_interests))
        print(f"👤 Found user: {user.name or user.email} with {len(user_interests)} interests")
    
    return users_with_interests

def store_multi_user_results(db: DatabaseManager, overall_summary: Dict):
    """Store processed stories in database for all users"""
    print("💾 Storing processed stories in database...")
    
    # Import stories to database (they're shared across users)
    scrape_date = overall_summary.get('scrape_date', datetime.now().isoformat())[:10]
    
    # Extract stories from first user's data (they're the same across users)
    if overall_summary.get('users_digest_data'):
        first_user_data = overall_summary['users_digest_data'][0]['digest_data']
        stories = first_user_data.get('stories', [])
        
        # Create a mock JSON structure for import
        mock_json_data = {
            "scrape_date": scrape_date,
            "stories": stories
        }
        
        # Save to temporary JSON and import
        import json
        temp_filename = f"temp_multi_user_import_{scrape_date}.json"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(mock_json_data, f, indent=2, ensure_ascii=False)
        
        db.import_json_data(temp_filename)
        
        # Clean up temp file
        os.remove(temp_filename)
        print(f"✅ Imported {len(stories)} stories for date {scrape_date}")

def main():
    """Main function for multi-user scraping and email sending"""
    print("🌟 Starting Multi-User Enhanced Hacker News Scraper")
    print("=" * 60)
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        db = DatabaseManager()
        scraper = EnhancedHackerNewsScraper()
        email_notifier = EmailNotifier()
        
        # Get all users and their interests
        print("\n👥 Loading users and interests...")
        users_with_interests = get_all_users_with_interests(db)
        
        if not users_with_interests:
            print("⚠️ No users found in database. Please set up users first via the web interface.")
            return
        
        print(f"✅ Found {len(users_with_interests)} users to process")
        
        # Process stories for all users
        print("\n📰 Processing stories for all users...")
        overall_summary = scraper.process_multi_user_daily_stories(users_with_interests)
        
        # Store results in database
        store_multi_user_results(db, overall_summary)
        
        # Send personalized emails
        print("\n📧 Sending personalized email digests...")
        users_digest_data = overall_summary.get('users_digest_data', [])
        
        if users_digest_data:
            email_results = email_notifier.send_multi_user_digests(users_digest_data)
            
            print(f"\n📊 Email Summary:")
            print(f"  ✅ Emails sent: {email_results['emails_sent']}")
            print(f"  ❌ Emails failed: {email_results['emails_failed']}")
            
            if email_results['failed_users']:
                print("  Failed users:")
                for failed_user in email_results['failed_users']:
                    print(f"    - {failed_user['name']} ({failed_user['email']}): {failed_user['reason']}")
        
        # Save overall summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"multi_user_summary_{timestamp}.json"
        import json
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Overall summary saved to: {summary_filename}")
        
        # Final summary
        print(f"\n🎉 Multi-User Processing Complete!")
        print(f"📊 Final Stats:")
        print(f"  • Total users: {overall_summary['total_users']}")
        print(f"  • Total stories processed: {overall_summary['total_stories']}")
        print(f"  • Average relevant per user: {overall_summary['avg_relevant_per_user']:.1f}")
        print(f"  • Cost savings: {overall_summary['cost_optimization'].get('savings_percentage', 0)}%")
        print(f"  • Emails sent: {email_results.get('emails_sent', 0)}")
        
    except Exception as e:
        print(f"❌ Error in multi-user processing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\n🔒 Cleaning up...")
        scraper.close()
        print("✅ Multi-user scraper finished")

if __name__ == "__main__":
    main()