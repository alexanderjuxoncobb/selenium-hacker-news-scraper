#!/usr/bin/env python3
"""
Railway Background Scheduler for Daily Scraping
Runs alongside the web app
"""

import os
import sys
import time
import schedule
from datetime import datetime
import pytz
import threading

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_daily_scrape():
    """Run the daily scraping and email process"""
    london_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(london_tz)
    
    print(f"🚀 Starting daily scrape at {current_time.strftime('%Y-%m-%d %H:%M:%S')} London time")
    
    try:
        # Import and run the multi-user scraper
        from multi_user_scraper import main as run_multi_user_scraper
        
        # Run the multi-user scraper
        print("📊 Running multi-user scraper...")
        run_multi_user_scraper()
        
        print("✅ Daily scrape completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during daily scrape: {str(e)}")
        import traceback
        traceback.print_exc()

def run_scheduler():
    """Run the scheduler in a separate thread"""
    # Schedule the job for 2:40 PM London time (13:40 UTC) - TESTING
    schedule.every().day.at("13:40").do(run_daily_scrape)
    
    print("📅 Scheduler started - Daily scrape at 2:40 PM London time (13:40 UTC) - TESTING")
    print(f"Current time: {datetime.now(pytz.timezone('Europe/London')).strftime('%Y-%m-%d %H:%M:%S')} London")
    
    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def start_background_scheduler():
    """Start the scheduler in a background thread"""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ Background scheduler started")

if __name__ == "__main__":
    # If run directly, just start the scheduler
    run_scheduler()