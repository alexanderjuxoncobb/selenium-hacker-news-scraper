#!/usr/bin/env python3
"""Quick test script to verify the scraper works"""

from scraper import HackerNewsScraper

def quick_test():
    print("🧪 Quick test - scraping just 1 story without comments...")
    scraper = HackerNewsScraper()
    
    try:
        # Test basic scraping
        stories = scraper.scrape_top_stories(1)
        if stories:
            story = stories[0]
            print(f"✅ Successfully scraped: {story['title']}")
            print(f"   📊 {story['points']} points, {story['comments_count']} comments")
            print(f"   👤 By {story['author']} ({story['time_posted']})")
            print(f"   🔗 {story['url']}")
        else:
            print("❌ No stories scraped")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    quick_test()