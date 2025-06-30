#!/usr/bin/env python3
"""
Daily Scheduler for Hacker News Scraper
Runs the multi-user scraper at 7:11 PM London time every day
Processes stories for all registered users and sends personalised email digests
"""

import schedule
import time
import subprocess
import os
from datetime import datetime
import pytz

def run_daily_scraper():
    """Run the daily scraping job"""
    london_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(london_tz)
    
    print(f"🕰️  Starting daily scraper job at {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    try:
        # Run the multi-user scraper to process and send emails to all users
        result = subprocess.run(['python', 'multi_user_scraper.py'], 
                              capture_output=True, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("✅ Daily scraping and email sending completed successfully!")
            print("📊 Scraper output:")
            print(result.stdout)
        else:
            print("❌ Error during daily scraping:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Failed to run scraper: {str(e)}")

def main():
    """Main scheduler function"""
    print("🤖 Hacker News Daily Scraper Scheduler Starting...")
    print("⏰ Scheduled to run at 7:11 PM London time every day")
    
    # Schedule the job for 7:11 PM London time (18:11 UTC)
    schedule.every().day.at("18:11").do(run_daily_scraper)
    
    # For testing - uncomment to run every minute
    # schedule.every().minute.do(run_daily_scraper)
    
    print("📅 Scheduler is running. Press Ctrl+C to stop.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n⏹️  Scheduler stopped by user.")

if __name__ == "__main__":
    main()