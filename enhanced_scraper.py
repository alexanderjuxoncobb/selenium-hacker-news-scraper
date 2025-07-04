#!/usr/bin/env python3
"""
Enhanced Hacker News Scraper with Cost-Optimised AI Pipeline
Uses local embeddings for initial filtering, cached summaries, and targeted OpenAI usage
"""

import os
import sys
# Fix tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add dashboard directory to path for database import
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

from ai_pipeline import CostOptimisedAI
from email_sender import get_email_notifier
from actionable_insights import ActionableInsightsAnalyzer
from database import DatabaseManager

class EnhancedHackerNewsScraper:
    def __init__(self, headless=True, openai_api_key=None):
        """Initialize the enhanced scraper with cost-optimised AI"""
        # Load environment variables
        load_dotenv()
        
        # Initialize cost-optimised AI pipeline
        self.ai = CostOptimisedAI(openai_api_key)
        
        # Initialize actionable insights analyzer
        self.insights_analyzer = ActionableInsightsAnalyzer(openai_api_key)
        
        # Initialize database for deduplication checks
        self.db = DatabaseManager()
        
        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless=new")  # 2025 syntax for better performance
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Initialize Chrome driver - try Selenium Grid first, fallback to local
        import os
        selenium_grid_url = os.getenv('SELENIUM_GRID_URL')
        
        if selenium_grid_url:
            # Use Railway Selenium Grid (preferred for production)
            print("🌐 Using Railway Selenium Grid...")
            print(f"📍 Grid URL: {selenium_grid_url}")
            
            # Ensure proper WebDriver endpoint
            if not selenium_grid_url.endswith('/wd/hub'):
                selenium_grid_url = f"{selenium_grid_url}/wd/hub"
                print(f"🔧 Adjusted URL: {selenium_grid_url}")
            
            try:
                self.driver = webdriver.Remote(
                    command_executor=selenium_grid_url,
                    options=chrome_options
                )
                print("✅ Connected to Selenium Grid")
            except Exception as e:
                print(f"⚠️  Selenium Grid connection failed: {e}")
                print("🔄 Falling back to local Chrome...")
                self.driver = self._setup_local_chrome(chrome_options)
        else:
            # Fallback to local Chrome (development/local testing)
            print("🔧 Using local Chrome setup...")
            self.driver = self._setup_local_chrome(chrome_options)
    
    def _setup_local_chrome(self, chrome_options):
        """Fallback method for local Chrome setup"""
        import glob
        
        # Railway-specific: Set Chrome binary path if in production
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('DATABASE_URL', '').startswith('postgres'):
            # Try to find chromium binary in Railway
            chromium_paths = glob.glob("/nix/store/*/bin/chromium")
            if chromium_paths:
                chrome_options.binary_location = chromium_paths[0]
                print(f"Using Railway chromium: {chromium_paths[0]}")
            else:
                print("Warning: Could not find chromium binary in Railway")
        
        # Initialize Chrome driver
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=chrome_options)
    
    def scrape_top_stories(self, num_stories=30) -> List[Dict]:
        """Scrape the top N stories from Hacker News homepage"""
        try:
            print(f"🔍 Scraping top {num_stories} stories from Hacker News...")
            self.driver.get("https://news.ycombinator.com")
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "athing")))
            
            stories = []
            story_rows = self.driver.find_elements(By.CLASS_NAME, "athing")[:num_stories]
            
            for i, story_row in enumerate(story_rows, 1):
                try:
                    story_data = self._extract_story_data(story_row, i)
                    if story_data:
                        stories.append(story_data)
                        print(f"✅ Scraped story {i}: {story_data['title'][:50]}...")
                except Exception as e:
                    print(f"❌ Error scraping story {i}: {str(e)}")
                    continue
            
            print(f"✅ Successfully scraped {len(stories)} stories")
            return stories
            
        except TimeoutException:
            print("❌ Timeout waiting for stories to load")
            return []
        except Exception as e:
            print(f"❌ Error scraping stories: {str(e)}")
            return []
    
    def _extract_story_data(self, story_row, rank) -> Optional[Dict]:
        """Extract data from a single story row"""
        try:
            story_id = story_row.get_attribute("id")
            
            # Get title and URL
            title_cell = story_row.find_element(By.CLASS_NAME, "titleline")
            title_link = title_cell.find_element(By.TAG_NAME, "a")
            title = title_link.text.strip()
            url = title_link.get_attribute("href")
            
            # Get the subtext row (contains points, author, time, comments)
            subtext_row = self.driver.find_element(By.XPATH, f"//tr[@id='{story_id}']/following-sibling::tr[1]")
            subtext = subtext_row.find_element(By.CLASS_NAME, "subtext")
            
            # Extract points
            points = 0
            try:
                score_span = subtext.find_element(By.CLASS_NAME, "score")
                points = int(score_span.text.split()[0])
            except NoSuchElementException:
                points = 0
            
            # Extract author
            author = ""
            try:
                author_link = subtext.find_element(By.CLASS_NAME, "hnuser")
                author = author_link.text.strip()
            except NoSuchElementException:
                author = "Unknown"
            
            # Extract time
            time_posted = ""
            try:
                age_span = subtext.find_element(By.CLASS_NAME, "age")
                time_posted = age_span.text.strip()
            except NoSuchElementException:
                time_posted = "Unknown"
            
            # Extract comments count and HN discussion URL
            comments_count = 0
            hn_discussion_url = ""
            try:
                comments_links = subtext.find_elements(By.TAG_NAME, "a")
                for link in comments_links:
                    if "comment" in link.text.lower():
                        comments_count = int(link.text.split()[0]) if link.text.split()[0].isdigit() else 0
                        hn_discussion_url = link.get_attribute("href")
                        break
            except (NoSuchElementException, ValueError):
                comments_count = 0
            
            return {
                "rank": rank,
                "story_id": story_id,
                "title": title,
                "url": url,
                "points": points,
                "author": author,
                "time_posted": time_posted,
                "comments_count": comments_count,
                "hn_discussion_url": hn_discussion_url,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error extracting story data: {str(e)}")
            return None
    
    def is_relevant_story(self, story_data: Dict, user_interests: Optional[Dict] = None) -> bool:
        """
        Cost-optimised relevance filtering using local embeddings + AI refinement
        Now supports user-specific interests for multi-user filtering
        """
        # Use local embedding-based filtering first
        is_relevant_local, confidence_score, reasoning = self.ai.is_relevant_story_local(story_data, user_interests)
        
        # For uncertain cases, use AI refinement
        if 0.3 <= confidence_score <= 0.5:
            is_relevant = self.ai.is_relevant_story_ai_refined(story_data, confidence_score, user_interests)
        else:
            is_relevant = is_relevant_local
        
        # Store relevance metadata (convert numpy types to Python types for JSON serialization)
        story_data.update({
            "relevance_score": float(confidence_score),  # Convert numpy float32 to Python float
            "relevance_reasoning": reasoning,
            "ai_refined": bool(0.3 <= confidence_score <= 0.5),  # Ensure Python bool
            "is_relevant": bool(is_relevant)  # Convert numpy.bool_ to Python bool to prevent SQLite adapter errors
        })
        
        return is_relevant
    
    def get_article_summary(self, url: str) -> Optional[str]:
        """
        Get article summary using cached approach
        """
        return self.ai.get_article_summary_cached(url)
    
    def analyse_comments(self, hn_discussion_url: str, num_comments=10) -> Dict:
        """
        Scrape and analyse comments with cost optimisation
        """
        if not hn_discussion_url:
            return {
                "total_comments_analyzed": 0,
                "main_themes": ["No comments available"],
                "agreement_points": [],
                "disagreement_points": [],
                "sentiment_summary": "No discussion to analyze",
                "top_comments": []
            }
        
        try:
            print(f"  📖 Scraping comments from: {hn_discussion_url}")
            self.driver.get(hn_discussion_url)
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comment")))
            
            comment_elements = self.driver.find_elements(By.CSS_SELECTOR, ".athing.comtr")[:num_comments]
            
            comments_data = []
            for i, comment_elem in enumerate(comment_elements, 1):
                try:
                    comment_data = self._extract_comment_data(comment_elem, i)
                    if comment_data:
                        comments_data.append(comment_data)
                        print(f"    ✅ Extracted comment {i}: {comment_data['text'][:50]}...")
                except Exception as e:
                    print(f"    ❌ Error extracting comment {i}: {str(e)}")
                    continue
            
            # Use cost-optimised comment analysis
            analysis = self.ai.analyse_comments_efficient(comments_data)
            analysis["top_comments"] = comments_data
            
            print(f"  ✅ Analysed {len(comments_data)} comments")
            return analysis
            
        except TimeoutException:
            print("  ⏰ Timeout waiting for comments to load")
            return {
                "total_comments_analyzed": 0,
                "main_themes": ["Comments failed to load"],
                "agreement_points": [],
                "disagreement_points": [],
                "sentiment_summary": "Could not load comments",
                "top_comments": []
            }
        except Exception as e:
            print(f"  ❌ Error analyzing comments: {str(e)}")
            return {
                "total_comments_analyzed": 0,
                "main_themes": [f"Error: {str(e)}"],
                "agreement_points": [],
                "disagreement_points": [],
                "sentiment_summary": "Analysis failed",
                "top_comments": []
            }
    
    def _extract_comment_data(self, comment_elem, rank) -> Optional[Dict]:
        """Extract data from a single comment element"""
        try:
            comment_id = comment_elem.get_attribute("id")
            
            comment_span = comment_elem.find_element(By.CLASS_NAME, "commtext")
            comment_text = comment_span.text.strip()
            
            comhead = comment_elem.find_element(By.CLASS_NAME, "comhead")
            
            # Extract author
            author = "Unknown"
            try:
                author_link = comhead.find_element(By.CLASS_NAME, "hnuser")
                author = author_link.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract time
            time_posted = "Unknown"
            try:
                age_link = comhead.find_element(By.CLASS_NAME, "age")
                time_posted = age_link.text.strip()
            except NoSuchElementException:
                pass
            
            # Get comment score if available
            score = None
            try:
                score_span = comhead.find_element(By.CLASS_NAME, "score")
                score = int(score_span.text.split()[0])
            except (NoSuchElementException, ValueError):
                score = None
            
            return {
                "rank": rank,
                "comment_id": comment_id,
                "author": author,
                "time_posted": time_posted,
                "score": score,
                "text": comment_text,
                "length": len(comment_text.split())
            }
            
        except Exception as e:
            print(f"    ❌ Error extracting comment data: {str(e)}")
            return None
    
    def generate_executive_summary(self, story_data: Dict) -> str:
        """Generate executive summary for a story"""
        title = story_data.get('title', 'Unknown Title')
        points = story_data.get('points', 0)
        comments_count = story_data.get('comments_count', 0)
        author = story_data.get('author', 'Unknown')
        time_posted = story_data.get('time_posted', 'Unknown')
        relevance_score = story_data.get('relevance_score', 0.0)
        
        # Article summary
        article_summary = story_data.get('article_summary', 'No article summary available')
        if article_summary and len(article_summary) > 300:
            article_summary = article_summary[:297] + "..."
        
        # Comments analysis
        comments_analysis = story_data.get('comments_analysis', {})
        themes = comments_analysis.get('main_themes', [])
        sentiment = comments_analysis.get('sentiment_summary', 'No sentiment analysis')
        total_comments_analyzed = comments_analysis.get('total_comments_analyzed', 0)
        
        # Build executive summary
        summary_parts = []
        
        # Header with relevance score
        summary_parts.append(f"## {title}")
        summary_parts.append(f"**Stats:** {points} points, {comments_count} comments by {author} ({time_posted})")
        summary_parts.append(f"**Relevance:** {relevance_score:.2f}/1.0 {'🔥' if relevance_score > 0.7 else '⭐' if relevance_score > 0.5 else '🔍'}")
        summary_parts.append("")
        
        # Article summary
        summary_parts.append("### Article Summary")
        if article_summary and article_summary != "No article summary available":
            summary_parts.append(article_summary)
        else:
            summary_parts.append("*Article content not accessible or this is a discussion post*")
        summary_parts.append("")
        
        # Comments analysis with detailed insights
        if total_comments_analyzed > 0:
            summary_parts.append("### 💬 Community Discussion Analysis")
            summary_parts.append(f"**Analyzed {total_comments_analyzed} top comments**")
            
            # Technical details section
            tech_details = comments_analysis.get('detailed_technical_analysis', {})
            if tech_details.get('specific_numbers') or tech_details.get('tools_mentioned'):
                summary_parts.append("")
                summary_parts.append("**🔧 Technical Details:**")
                
                if tech_details.get('specific_numbers'):
                    numbers = tech_details['specific_numbers'][:3]  # Show top 3
                    summary_parts.append(f"• **Metrics:** {', '.join(numbers)}")
                
                if tech_details.get('tools_mentioned'):
                    tools = tech_details['tools_mentioned'][:4]  # Show top 4
                    summary_parts.append(f"• **Tools/Tech:** {', '.join(tools)}")
                
                if tech_details.get('performance_data'):
                    perf = tech_details['performance_data'][:2]  # Show top 2
                    summary_parts.append(f"• **Performance:** {', '.join(perf)}")
            
            # Cost analysis section
            cost_analysis = comments_analysis.get('detailed_cost_analysis', {})
            if cost_analysis.get('price_comparisons') or cost_analysis.get('efficiency_gains'):
                summary_parts.append("")
                summary_parts.append("**💰 Cost Analysis:**")
                
                if cost_analysis.get('price_comparisons'):
                    costs = cost_analysis['price_comparisons'][:2]
                    summary_parts.append(f"• **Pricing:** {', '.join(costs)}")
                
                if cost_analysis.get('efficiency_gains'):
                    gains = cost_analysis['efficiency_gains'][:2]
                    summary_parts.append(f"• **Efficiency:** {', '.join(gains)}")
            
            # Community consensus section
            consensus = comments_analysis.get('detailed_consensus', {})
            if consensus.get('strong_agreements') or consensus.get('major_disagreements'):
                summary_parts.append("")
                summary_parts.append("**🤝 Community Consensus:**")
                
                if consensus.get('strong_agreements'):
                    agreements = consensus['strong_agreements'][:2]
                    summary_parts.append(f"• **Agreements:** {', '.join(agreements)}")
                
                if consensus.get('major_disagreements'):
                    disagreements = consensus['major_disagreements'][:2]
                    summary_parts.append(f"• **Disagreements:** {', '.join(disagreements)}")
            
            # Success stories and recommendations
            stories = comments_analysis.get('detailed_success_stories', {})
            recommendations = comments_analysis.get('detailed_recommendations', {})
            
            if stories.get('working_setups') or recommendations.get('actionable_advice'):
                summary_parts.append("")
                summary_parts.append("**✅ Practical Insights:**")
                
                if stories.get('working_setups'):
                    setups = stories['working_setups'][:2]
                    summary_parts.append(f"• **Working Setups:** {', '.join(setups)}")
                
                if recommendations.get('actionable_advice'):
                    advice = recommendations['actionable_advice'][:2]
                    summary_parts.append(f"• **Recommendations:** {', '.join(advice)}")
            
            # Overall sentiment
            summary_parts.append("")
            summary_parts.append(f"**Overall Sentiment:** {sentiment}")
            
        else:
            summary_parts.append("### Discussion Analysis")
            summary_parts.append("*No comments available for analysis*")
        
        # Actionable insights section
        insights = story_data.get('actionable_insights', {})
        if insights.get('has_insights'):
            summary_parts.append("")
            summary_parts.append("### 💡 Actionable Insights")
            
            # Market signals
            market_signals = insights.get('market_signals', {})
            if market_signals.get('description'):
                summary_parts.append(f"**Market Signal:** {market_signals['description']}")
            
            # Business opportunities
            business_ops = insights.get('business_opportunities', {})
            if business_ops.get('description'):
                summary_parts.append(f"**Opportunity:** {business_ops['description']}")
            
            # Key takeaways
            takeaways = insights.get('actionable_takeaways', [])
            if takeaways:
                summary_parts.append(f"**Action Items:** {', '.join(takeaways[:2])}")
            
            # Priority indicator
            priority_score = insights.get('priority_score', 0)
            if priority_score >= 0.7:
                summary_parts.append(f"**Priority:** 🔥 High ({priority_score:.2f})")
            elif priority_score >= 0.4:
                summary_parts.append(f"**Priority:** ⭐ Medium ({priority_score:.2f})")
        
        summary_parts.append("")
        summary_parts.append(f"**🔗 Read more:** {story_data.get('url', 'No URL')}")
        summary_parts.append(f"**💬 Join discussion:** {story_data.get('hn_discussion_url', 'No discussion URL')}")
        summary_parts.append("")
        summary_parts.append("---")
        
        return "\n".join(summary_parts)
    
    def generate_daily_email_content(self, daily_data: Dict) -> str:
        """Generate formatted email content with cost report"""
        scrape_date = daily_data.get('scrape_date', 'Unknown date')
        total_stories = daily_data.get('total_stories', 0)  # Non-cached stories
        total_scraped = daily_data.get('total_scraped', total_stories)  # Backward compatibility
        relevant_stories = daily_data.get('relevant_stories', 0)
        stories = daily_data.get('stories', [])
        
        # Get cost optimisation report and insights summary
        cost_report = self.ai.get_cost_report()
        insights_summary = daily_data.get('actionable_insights_summary', {})
        
        relevant_story_data = [story for story in stories if story.get('is_relevant', False)]
        
        email_parts = []
        
        # Email header with cost savings
        email_parts.append("# 📰 Your Daily Hacker News Digest")
        email_parts.append(f"*Generated on {scrape_date[:10]} at {scrape_date[11:19]}*")
        email_parts.append("")
        cached_stories = total_scraped - total_stories
        email_parts.append(f"**Summary:** Found {relevant_stories} relevant stories out of {total_stories} newly processed stories")
        if cached_stories > 0:
            email_parts.append(f"**📋 Cache Usage:** {cached_stories} stories served from cache (out of {total_scraped} total scraped)")
        
        # Add insights summary if available
        if insights_summary.get('total_insights', 0) > 0:
            email_parts.append(f"**🔍 Actionable Insights:** {insights_summary['total_insights']} insights found")
            email_parts.append(f"**📊 Key Intelligence:** {insights_summary.get('summary', 'Business intelligence extracted')}")
        
        email_parts.append("")
        
        if not relevant_story_data:
            email_parts.append("*No relevant stories found today based on your interests.*")
            return "\n".join(email_parts)
        
        # Add executive summary for each relevant story
        for i, story in enumerate(relevant_story_data, 1):
            email_parts.append(f"# Story {i} of {len(relevant_story_data)}")
            email_parts.append("")
            executive_summary = self.generate_executive_summary(story)
            email_parts.append(executive_summary)
            email_parts.append("")
        
        # Footer with detailed cost report
        email_parts.append("---")
        email_parts.append("📧 *This digest was automatically generated by your Enhanced Hacker News scraper*")
        email_parts.append(f"🤖 *Processed {sum([s.get('comments_analysis', {}).get('total_comments_analyzed', 0) for s in relevant_story_data])} comments across all stories*")
        
        return "\n".join(email_parts)
    
    def extract_story_tags(self, story_data: Dict) -> List[str]:
        """
        Extract semantic tags from story title and content for better categorization
        """
        title = story_data.get('title', '').lower()
        
        # Common tech/business categories for HN stories
        category_keywords = {
            'ai': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 'gpt', 'llm', 'chatgpt', 'openai'],
            'startup': ['startup', 'ycombinator', 'yc', 'funding', 'series a', 'series b', 'ipo', 'acquisition'],
            'programming': ['programming', 'code', 'software', 'development', 'python', 'javascript', 'rust', 'go', 'java'],
            'web': ['web', 'browser', 'frontend', 'backend', 'api', 'http', 'css', 'html'],
            'mobile': ['mobile', 'ios', 'android', 'app', 'iphone', 'smartphone'],
            'security': ['security', 'hacking', 'vulnerability', 'breach', 'crypto', 'encryption'],
            'hardware': ['hardware', 'chip', 'processor', 'cpu', 'gpu', 'semiconductor'],
            'science': ['research', 'study', 'paper', 'university', 'science', 'physics', 'biology'],
            'business': ['business', 'market', 'revenue', 'profit', 'economics', 'finance'],
            'politics': ['politics', 'government', 'policy', 'regulation', 'law', 'legal'],
            'climate': ['climate', 'environment', 'energy', 'solar', 'renewable', 'carbon'],
            'space': ['space', 'nasa', 'spacex', 'satellite', 'mars', 'rocket']
        }
        
        tags = []
        for category, keywords in category_keywords.items():
            if any(keyword in title for keyword in keywords):
                tags.append(category)
        
        # If no specific tags found, try to infer from common patterns
        if not tags:
            if any(word in title for word in ['show hn', 'ask hn']):
                tags.append('community')
            elif any(word in title for word in ['new', 'launch', 'release', 'introduce']):
                tags.append('product')
            elif any(word in title for word in ['why', 'how', 'what', 'guide', 'tutorial']):
                tags.append('educational')
        
        return tags or ['general']  # Always have at least one tag
    
    def process_daily_stories(self, user_interests: Optional[Dict] = None) -> Dict:
        """
        Main function to process daily stories with cost optimisation
        Now supports user-specific interests for multi-user filtering
        """
        user_desc = "personalised" if user_interests else "default"
        print(f"🚀 Starting enhanced daily Hacker News scraping with {user_desc} interests...")
        
        # Print initial cost report
        initial_report = self.ai.get_cost_report()
        print(f"💰 Starting with {initial_report['cache_size']} cached summaries")
        
        # Scrape top 30 stories
        stories = self.scrape_top_stories(30)
        
        processed_stories = []
        relevant_count = 0
        non_cached_count = 0  # Track stories that weren't served from cache
        
        for story in stories:
            print(f"\n📰 Processing: {story['title'][:50]}...")
            
            # Track initial API call count to detect cache usage
            initial_api_calls = self.ai.api_calls_made
            
            # Extract story tags for better categorization
            story_tags = self.extract_story_tags(story)
            story['tags'] = story_tags
            print(f"🏷️ Story tags: {', '.join(story_tags)}")
            
            # Check if story is relevant using cost-optimised filtering (with user-specific interests)
            if self.is_relevant_story(story, user_interests):
                relevant_count += 1
                print(f"✅ Story marked as relevant ({relevant_count}/30)")
                
                # Get article summary if it's an external link
                article_summary = None
                if not story['url'].startswith('https://news.ycombinator.com'):
                    print("📄 Getting article summary...")
                    article_summary = self.get_article_summary(story['url'])
                
                # Analyse comments
                print("💬 Analysing comments...")
                comments_analysis = self.analyse_comments(story['hn_discussion_url'])
                
                # Analyse for actionable insights
                print("🔍 Analysing actionable insights...")
                actionable_insights = self.insights_analyzer.analyse_story_for_insights({
                    **story,
                    "article_summary": article_summary,
                    "comments_analysis": comments_analysis
                })
                
                # Add processed data to story
                story.update({
                    "article_summary": article_summary,
                    "comments_analysis": comments_analysis,
                    "actionable_insights": actionable_insights,
                    "is_relevant": True,
                    "tags": story_tags  # Ensure tags are included
                })
            else:
                story["is_relevant"] = False
                # Still include tags for filtered stories for potential user-specific filtering
                story["tags"] = story_tags
            
            # Check if this story required any new API calls (not cached)
            was_cached = self.ai.api_calls_made == initial_api_calls
            if not was_cached:
                non_cached_count += 1
                print(f"📊 Non-cached story count: {non_cached_count}")
            
            # Add cache status to story data
            story["was_cached"] = was_cached
            
            processed_stories.append(story)
            
            # Add small delay to be respectful to servers
            time.sleep(0.5)  # Reduced delay since we're making fewer API calls
        
        # Final cost report
        final_report = self.ai.get_cost_report()
        
        # Generate insights summary for relevant stories
        print("\n🔍 Generating actionable insights summary...")
        relevant_insights = []
        for story in processed_stories:
            if story.get('is_relevant') and story.get('actionable_insights'):
                relevant_insights.append(story['actionable_insights'])
        
        insights_summary = self.insights_analyzer.generate_insights_summary(relevant_insights)
        
        result = {
            "scrape_date": datetime.now().isoformat(),
            "total_stories": non_cached_count,  # Only count non-cached stories
            "total_scraped": len(stories),  # Keep track of actual scraped stories
            "relevant_stories": relevant_count,
            "stories": processed_stories,
            "cost_optimization": final_report,
            "actionable_insights_summary": insights_summary
        }
        
        print(f"\n✅ Enhanced scraping complete! Found {relevant_count} relevant stories out of {non_cached_count} newly processed stories.")
        print(f"📊 Total scraped: {len(stories)}, Newly processed: {non_cached_count}, Cached: {len(stories) - non_cached_count}")
        print(f"💰 Cost savings: {final_report['savings_percentage']}% (${final_report['estimated_money_saved']} saved)")
        print(f"🔄 API calls: {final_report['api_calls_made']} made, {final_report['api_calls_saved']} saved")
        
        return result
    
    def process_multi_user_daily_stories(self, users_with_interests: list) -> Dict:
        """
        Process daily stories for multiple users with personalized filtering
        
        Args:
            users_with_interests: List of tuples (user, user_interests)
            
        Returns:
            Dict with overall stats and per-user digest data
        """
        print(f"🚀 Starting multi-user enhanced HN scraping for {len(users_with_interests)} users...")
        
        # Get initial cost report
        initial_report = self.ai.get_cost_report()
        print(f"💰 Starting with {initial_report['cache_size']} cached summaries")
        
        # Scrape top 30 stories once (shared across all users)
        print("📰 Scraping top 30 stories...")
        all_stories = self.scrape_top_stories(30)
        
        # Filter out stories that have already been processed (deduplication)
        print("🔍 Filtering out previously processed stories...")
        new_stories = []
        skipped_count = 0
        
        for story in all_stories:
            if self.db.story_exists_by_hn_id(story['story_id']):
                skipped_count += 1
                print(f"  ⏭️ Skipping already processed story: {story['title'][:50]}...")
            else:
                new_stories.append(story)
        
        print(f"✅ Found {len(new_stories)} new stories, skipped {skipped_count} already processed")
        
        # Process new stories for global analysis
        print("🔍 Processing new stories for global analysis...")
        processed_stories = []
        
        for story in new_stories:
            print(f"  📰 Processing: {story['title'][:50]}...")
            
            # Extract story tags for better categorization
            story_tags = self.extract_story_tags(story)
            story['tags'] = story_tags
            
            # Get article summary if it's an external link
            article_summary = None
            if not story['url'].startswith('https://news.ycombinator.com'):
                print("    📄 Getting article summary...")
                article_summary = self.get_article_summary(story['url'])
            
            # Analyze comments (shared analysis)
            print("    💬 Analyzing comments...")
            comments_analysis = self.analyse_comments(story['hn_discussion_url'])
            
            # Analyze for actionable insights
            print("    🔍 Analyzing actionable insights...")
            actionable_insights = self.insights_analyzer.analyse_story_for_insights({
                **story,
                "article_summary": article_summary,
                "comments_analysis": comments_analysis
            })
            
            # Add processed data to story
            story.update({
                "article_summary": article_summary,
                "comments_analysis": comments_analysis,
                "actionable_insights": actionable_insights,
                "tags": story_tags
            })
            
            processed_stories.append(story)
        
        # Generate personalised digests for each user
        print(f"👥 Generating personalised digests for {len(users_with_interests)} users...")
        users_digest_data = []
        
        for user, user_interests in users_with_interests:
            print(f"  🎯 Processing for user: {user.name or user.email}")
            
            # Filter stories for this user's interests
            user_stories = []
            user_relevant_count = 0
            for story in processed_stories:
                story_copy = story.copy()
                if self.is_relevant_story(story, user_interests):
                    story_copy['is_relevant'] = True
                    user_relevant_count += 1
                else:
                    story_copy['is_relevant'] = False
                user_stories.append(story_copy)
            
            # Create user-specific digest data
            user_digest_data = {
                "scrape_date": datetime.now().isoformat(),
                "total_stories": len(processed_stories),
                "total_scraped": len(processed_stories),
                "relevant_stories": user_relevant_count,
                "stories": user_stories,
                "cost_optimization": self.ai.get_cost_report(),
                "user_id": user.user_id,
                "user_name": user.name,
                "user_email": user.email
            }
            
            users_digest_data.append({
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "name": user.name
                },
                "digest_data": user_digest_data,
                "user_email": user.email
            })
            
            print(f"    ✅ Found {user_relevant_count} relevant stories for {user.name or user.email}")
        
        # Generate overall summary
        total_relevant_across_users = sum(len([s for s in data["digest_data"]["stories"] if s.get("is_relevant", False)]) 
                                        for data in users_digest_data)
        
        final_cost_report = self.ai.get_cost_report()
        processing_time = "N/A"  # Could implement timing if needed
        
        overall_summary = {
            "scrape_date": datetime.now().isoformat(),
            "total_stories": len(processed_stories),
            "total_scraped": len(all_stories),
            "stories_skipped": skipped_count,
            "total_users": len(users_with_interests),
            "total_relevant_across_all_users": total_relevant_across_users,
            "avg_relevant_per_user": total_relevant_across_users / len(users_with_interests) if users_with_interests else 0,
            "processing_time": processing_time,
            "cost_optimization": final_cost_report,
            "users_digest_data": users_digest_data
        }
        
        print(f"✅ Multi-user processing complete!")
        print(f"📊 Summary: {len(processed_stories)} new stories processed (skipped {skipped_count} duplicates), avg {overall_summary['avg_relevant_per_user']:.1f} relevant per user")
        print(f"💰 Cost optimisation: {final_cost_report.get('savings_percentage', 0)}% saved")
        
        return overall_summary
    
    def save_to_json(self, data: Dict, filename: str = None):
        """Save scraped data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_hn_scrape_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Data saved to {filename}")
        return filename
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("🔒 Browser closed.")

def main():
    """Main function to run enhanced daily scraping with email notification"""
    scraper = None
    
    try:
        scraper = EnhancedHackerNewsScraper()
        # Process daily stories
        daily_data = scraper.process_daily_stories()
        
        # Save to JSON
        json_filename = scraper.save_to_json(daily_data)
        
        # Generate email content
        email_content = scraper.generate_daily_email_content(daily_data)
        
        # Save email content
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        email_filename = f"enhanced_digest_{timestamp}.md"
        with open(email_filename, 'w', encoding='utf-8') as f:
            f.write(email_content)
        
        # Send email notification
        try:
            print("\n📧 Sending email notification...")
            notifier = get_email_notifier()
            email_success = notifier.send_daily_digest(daily_data)
            
            if email_success:
                print("✅ Daily digest email sent successfully!")
            else:
                print("⚠️ Email sending failed, but digest was generated")
                
        except ValueError as e:
            print(f"⚠️ Email not configured: {e}")
            print("💡 Run 'python email_sender.py' to set up email notifications")
        except Exception as e:
            print(f"⚠️ Email error: {e}")
        
        print(f"\n🎉 Enhanced scraping completed successfully!")
        print(f"📊 Results: {daily_data['relevant_stories']} relevant stories found")
        print(f"💾 Data saved to: {json_filename}")
        print(f"📧 Email content saved to: {email_filename}")
        print(f"💰 Total cost savings: {daily_data['cost_optimization']['savings_percentage']}%")
        
    except Exception as e:
        print(f"❌ Error during enhanced scraping: {str(e)}")
    finally:
        if scraper is not None:
            scraper.close()

def test_enhanced_scraper():
    """Test function with 3 stories"""
    print("🧪 Testing enhanced scraper with 3 stories...")
    scraper = None
    
    try:
        scraper = EnhancedHackerNewsScraper()
        stories = scraper.scrape_top_stories(3)
        
        processed_stories = []
        for story in stories:
            print(f"\n📰 Processing: {story['title'][:50]}...")
            
            if scraper.is_relevant_story(story):
                if not story['url'].startswith('https://news.ycombinator.com'):
                    article_summary = scraper.get_article_summary(story['url'])
                else:
                    article_summary = None
                
                comments_analysis = scraper.analyse_comments(story['hn_discussion_url'], num_comments=3)
                
                story.update({
                    "article_summary": article_summary,
                    "comments_analysis": comments_analysis,
                    "is_relevant": True
                })
            else:
                story["is_relevant"] = False
                
            processed_stories.append(story)
        
        # Show cost report
        cost_report = scraper.ai.get_cost_report()
        print(f"\n💰 Cost Report:")
        print(f"   Savings: {cost_report['savings_percentage']}%")
        print(f"   Money saved: ${cost_report['estimated_money_saved']}")
        print(f"   API calls made: {cost_report['api_calls_made']}")
        print(f"   API calls saved: {cost_report['api_calls_saved']}")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
    finally:
        if scraper is not None:
            scraper.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_enhanced_scraper()
    else:
        main()