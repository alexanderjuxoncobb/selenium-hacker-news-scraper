#!/usr/bin/env python3
"""
Railway Cron Job Runner for Daily Scraping
Runs the multi-user scraper and sends emails
"""

import os
import sys
from datetime import datetime
import pytz

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_daily_scrape():
    """Run the daily scraping and email process"""
    london_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(london_tz)
    
    print(f"🚀 Starting daily scrape at {current_time.strftime('%Y-%m-%d %H:%M:%S')} London time")
    
    try:
        # Import and run the multi-user scraper
        from multi_user_scraper import main
        
        # Run the scraper
        print("📊 Running multi-user scraper...")
        main()
        
        print("✅ Daily scrape completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during daily scrape: {str(e)}")
        raise

if __name__ == "__main__":
    run_daily_scrape()