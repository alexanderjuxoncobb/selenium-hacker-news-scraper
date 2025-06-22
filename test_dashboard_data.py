#!/usr/bin/env python3
"""
Generate test data for dashboard with enhanced analysis
"""

from enhanced_scraper import EnhancedHackerNewsScraper
import json

def create_dashboard_test_data():
    """Create enhanced analysis data for dashboard testing"""
    print("🧪 Creating enhanced test data for dashboard...")
    
    scraper = EnhancedHackerNewsScraper(headless=True)
    
    try:
        # Get just 5 stories for testing
        stories = scraper.scrape_top_stories(5)
        
        processed_stories = []
        relevant_count = 0
        
        for story in stories:
            print(f"\n📰 Processing: {story['title'][:50]}...")
            
            # Force relevance for testing
            if scraper.is_relevant_story(story) or relevant_count < 3:  # Ensure at least 3 relevant
                relevant_count += 1
                print(f"✅ Story marked as relevant ({relevant_count}/5)")
                
                # Get article summary if it's an external link
                article_summary = None
                if not story['url'].startswith('https://news.ycombinator.com'):
                    print("📄 Getting article summary...")
                    article_summary = scraper.get_article_summary(story['url'])
                
                # Analyze comments with enhanced system
                print("💬 Analyzing comments...")
                comments_analysis = scraper.analyze_comments(story['hn_discussion_url'], num_comments=8)
                
                # Force relevance for testing
                story.update({
                    "article_summary": article_summary,
                    "comments_analysis": comments_analysis,
                    "is_relevant": True
                })
            else:
                story["is_relevant"] = False
            
            processed_stories.append(story)
        
        # Create test data structure
        test_data = {
            "scrape_date": __import__('datetime').datetime.now().isoformat(),
            "total_stories": len(stories),
            "relevant_stories": relevant_count,
            "stories": processed_stories,
            "cost_optimization": scraper.ai.get_cost_report()
        }
        
        # Save to JSON for dashboard import
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_hn_scrape_{timestamp}.json"
        
        # Fix JSON serialization issues
        def fix_json_serialization(obj):
            """Convert numpy types to Python types"""
            if hasattr(obj, 'dtype'):
                return obj.item()
            return obj
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False, default=fix_json_serialization)
        
        print(f"\n✅ Enhanced test data saved to: {filename}")
        print(f"📊 Relevant stories: {relevant_count}")
        print(f"💰 API calls made: {scraper.ai.get_cost_report()['api_calls_made']}")
        
        # Show sample of enhanced analysis
        if relevant_count > 0:
            sample_story = next(s for s in processed_stories if s.get('is_relevant'))
            comments = sample_story.get('comments_analysis', {})
            tech_details = comments.get('detailed_technical_analysis', {})
            
            print(f"\n📋 Sample Enhanced Analysis for: {sample_story['title'][:50]}...")
            if tech_details.get('specific_numbers'):
                print(f"   Numbers: {tech_details['specific_numbers'][:2]}")
            if tech_details.get('tools_mentioned'):
                print(f"   Tools: {tech_details['tools_mentioned'][:3]}")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        scraper.close()

if __name__ == "__main__":
    create_dashboard_test_data()