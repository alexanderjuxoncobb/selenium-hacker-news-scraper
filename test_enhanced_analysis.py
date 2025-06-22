#!/usr/bin/env python3
"""
Test the enhanced community sentiment analysis
"""

from enhanced_scraper import EnhancedHackerNewsScraper
import json

def test_enhanced_analysis():
    """Test the enhanced comment analysis on a real story"""
    print("🧪 Testing enhanced community sentiment analysis...")
    
    scraper = EnhancedHackerNewsScraper(headless=True)
    
    try:
        # Get just the top story for testing
        stories = scraper.scrape_top_stories(1)
        
        if not stories:
            print("❌ No stories found")
            return
        
        story = stories[0]
        print(f"\n📰 Testing with story: {story['title']}")
        print(f"📊 Points: {story['points']}, Comments: {story['comments_count']}")
        
        # Analyze comments with enhanced system
        print("\n💬 Analyzing comments with enhanced system...")
        comments_analysis = scraper.analyze_comments(story['hn_discussion_url'], num_comments=5)
        
        # Display the enhanced analysis
        print("\n" + "="*80)
        print("ENHANCED COMMUNITY SENTIMENT ANALYSIS RESULTS")
        print("="*80)
        
        print(f"\n📊 Basic Info:")
        print(f"   Comments analyzed: {comments_analysis.get('total_comments_analyzed', 0)}")
        print(f"   Main themes: {comments_analysis.get('main_themes', [])}")
        
        # Display detailed technical analysis
        tech_details = comments_analysis.get('detailed_technical_analysis', {})
        if any(tech_details.values()):
            print(f"\n🔧 Technical Details:")
            for key, values in tech_details.items():
                if values:
                    print(f"   {key.replace('_', ' ').title()}: {values}")
        
        # Display cost analysis
        cost_analysis = comments_analysis.get('detailed_cost_analysis', {})
        if any(cost_analysis.values()):
            print(f"\n💰 Cost Analysis:")
            for key, values in cost_analysis.items():
                if values:
                    print(f"   {key.replace('_', ' ').title()}: {values}")
        
        # Display community consensus
        consensus = comments_analysis.get('detailed_consensus', {})
        if any(consensus.values()):
            print(f"\n🤝 Community Consensus:")
            for key, values in consensus.items():
                if values:
                    print(f"   {key.replace('_', ' ').title()}: {values}")
        
        # Display success stories
        stories_data = comments_analysis.get('detailed_success_stories', {})
        if any(stories_data.values()):
            print(f"\n✅ Success/Failure Stories:")
            for key, values in stories_data.items():
                if values:
                    print(f"   {key.replace('_', ' ').title()}: {values}")
        
        # Display recommendations
        recommendations = comments_analysis.get('detailed_recommendations', {})
        if any(recommendations.values()):
            print(f"\n💡 Recommendations:")
            for key, values in recommendations.items():
                if values:
                    print(f"   {key.replace('_', ' ').title()}: {values}")
        
        print(f"\n📝 Overall Sentiment:")
        print(f"   {comments_analysis.get('sentiment_summary', 'No sentiment available')}")
        
        # Save full analysis to file for inspection
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        test_filename = f"test_enhanced_analysis_{timestamp}.json"
        
        test_data = {
            "story": story,
            "enhanced_analysis": comments_analysis
        }
        
        with open(test_filename, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full analysis saved to: {test_filename}")
        print("\n" + "="*80)
        
        # Show cost report
        cost_report = scraper.ai.get_cost_report()
        print(f"\n💰 AI Cost Report:")
        print(f"   API calls made: {cost_report['api_calls_made']}")
        print(f"   API calls saved: {cost_report['api_calls_saved']}")
        print(f"   Cost savings: {cost_report['savings_percentage']}%")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    test_enhanced_analysis()