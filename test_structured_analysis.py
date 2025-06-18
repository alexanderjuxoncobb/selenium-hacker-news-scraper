#!/usr/bin/env python3
"""
Test script for structured comment analysis - processes only first 3 relevant stories
"""

import os
import sys
import json
from datetime import datetime
from enhanced_scraper import EnhancedHackerNewsScraper
from dashboard.database import DatabaseManager

def test_structured_analysis():
    """Test the new structured analysis with only 3 relevant stories"""
    print("🧪 Testing structured comment analysis with first 3 relevant stories...")
    
    scraper = EnhancedHackerNewsScraper()
    db = DatabaseManager()
    
    try:
        # Scrape top 15 stories (to find at least 3 relevant ones)
        print("🔍 Scraping top 15 stories to find 3 relevant ones...")
        stories = scraper.scrape_top_stories(15)
        
        processed_stories = []
        relevant_count = 0
        target_relevant = 3
        
        for story in stories:
            print(f"\n📰 Processing: {story['title'][:50]}...")
            
            # Check if story is relevant
            if scraper.is_relevant_story(story):
                relevant_count += 1
                print(f"✅ Story {relevant_count} marked as relevant")
                
                # Get article summary if it's an external link
                article_summary = None
                if not story['url'].startswith('https://news.ycombinator.com'):
                    print("📄 Getting article summary...")
                    article_summary = scraper.get_article_summary(story['url'])
                
                # Analyze comments with new structured approach
                print("💬 Analyzing comments with structured analysis...")
                comments_analysis = scraper.analyze_comments(story['hn_discussion_url'], num_comments=5)
                
                # Print the new structured analysis for debugging
                print(f"🔍 Structured Analysis Results:")
                if comments_analysis.get('top_comment_summary'):
                    print(f"   📝 Top Comment Summary: {comments_analysis['top_comment_summary']}")
                
                if comments_analysis.get('structured_sentiment'):
                    struct_sent = comments_analysis['structured_sentiment']
                    print(f"   🎭 Overall Sentiment: {struct_sent.get('overall_description', 'N/A')}")
                    
                    for category, data in struct_sent.items():
                        if category != 'overall_description' and isinstance(data, dict):
                            points = data.get('points', [])
                            if points:
                                print(f"   📊 {data.get('title', category)}: {len(points)} points")
                                for point in points[:2]:  # Show first 2 points
                                    print(f"      • {point}")
                
                # Add processed data to story
                story.update({
                    "article_summary": article_summary,
                    "comments_analysis": comments_analysis,
                    "is_relevant": True
                })
                
                # Stop after finding 3 relevant stories
                if relevant_count >= target_relevant:
                    print(f"\n✅ Found {target_relevant} relevant stories, stopping...")
                    break
            else:
                story["is_relevant"] = False
            
            processed_stories.append(story)
        
        # Create test data structure
        test_data = {
            "scrape_date": datetime.now().isoformat(),
            "total_stories": len(processed_stories),
            "relevant_stories": relevant_count,
            "stories": processed_stories
        }
        
        # Save to JSON first, then import to database
        print(f"\n💾 Saving {relevant_count} relevant stories to database...")
        
        # Convert numpy types to Python types for JSON serialization
        def convert_for_json(obj):
            """Convert numpy types to Python types recursively"""
            if hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {key: convert_for_json(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            elif hasattr(obj, 'tolist'):  # numpy array
                return obj.tolist()
            else:
                return obj
        
        # Clean the data for JSON serialization
        clean_data = convert_for_json(test_data)
        
        # Save to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"test_structured_{timestamp}.json"
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, indent=2, ensure_ascii=False)
        
        # Import to database
        db.import_json_data(json_filename)
        print(f"✅ Saved to {json_filename} and imported to database")
        
        # Show cost report
        cost_report = scraper.ai.get_cost_report()
        print(f"\n💰 Cost Report:")
        print(f"   API calls made: {cost_report['api_calls_made']}")
        print(f"   API calls saved: {cost_report['api_calls_saved']}")
        print(f"   Savings: {cost_report['savings_percentage']}%")
        print(f"   Money spent: ${cost_report['estimated_money_spent']}")
        print(f"   Money saved: ${cost_report['estimated_money_saved']}")
        
        print(f"\n🎉 Test completed successfully!")
        print(f"📊 Results: {relevant_count} relevant stories with structured analysis")
        print(f"🌐 View results at: http://localhost:8000/dashboard/{datetime.now().strftime('%Y-%m-%d')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        scraper.close()

def main():
    """Main function"""
    print("🚀 Starting structured analysis test...")
    
    success = test_structured_analysis()
    
    if success:
        print("\n✅ Test successful! Check the dashboard to see the new structured format.")
        print("💡 If you're happy with the results, run the full scraper with: python enhanced_scraper.py")
    else:
        print("\n❌ Test failed. Check the error messages above.")
    
    print(f"\n📋 Next steps:")
    print(f"   1. Start the dashboard: cd dashboard && python app.py")
    print(f"   2. Visit: http://localhost:8000")
    print(f"   3. Look for the new structured sentiment sections")

if __name__ == "__main__":
    main()