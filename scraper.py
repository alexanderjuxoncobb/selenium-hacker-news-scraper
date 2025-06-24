#!/usr/bin/env python3
"""
Hacker News Web Scraper using Selenium
Daily scraper that extracts top 30 stories, analyzes relevance, and provides summaries
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

class HackerNewsScraper:
    def __init__(self, headless=True, openai_api_key=None):
        """Initialize the scraper with Chrome WebDriver and OpenAI client"""
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file or pass as parameter.")
        
        self.openai_client = OpenAI(api_key=api_key)
        
        # User interests for AI filtering
        self.user_interests = {
            "high_priority": [
                "artificial intelligence", "AI", "machine learning", "ML", "AI agents",
                "tech startups", "software development", "programming", "mathematics",
                "statistics", "behavioral economics", "behavioral finance"
            ],
            "medium_priority": [
                "robotics", "hardware", "politics", "Trump", "UK", "Europe", "United Kingdom",
                "health", "wellness", "running", "books", "reading"
            ],
            "low_priority": [
                "music"
            ]
        }
        
        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Initialize the Chrome driver with system ChromeDriver
        try:
            # Try to use system ChromeDriver first (installed via Homebrew)
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception:
            # Fallback to webdriver-manager if system ChromeDriver not found
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def scrape_top_stories(self, num_stories=30) -> List[Dict]:
        """Scrape the top N stories from Hacker News homepage"""
        try:
            print(f"Scraping top {num_stories} stories from Hacker News...")
            self.driver.get("https://news.ycombinator.com")
            
            # Wait for stories to load
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
            
            print(f"Successfully scraped {len(stories)} stories")
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
                points = 0  # Some stories don't have points (like job postings)
            
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
    
    def is_relevant_story(self, story_data: Dict) -> bool:
        """
        Determine if a story is relevant based on user interests using AI
        """
        try:
            title = story_data.get('title', '')
            url = story_data.get('url', '')
            
            # Create a prompt for the AI to evaluate relevance
            prompt = f"""
            Analyze if this Hacker News story is relevant to someone with these interests:

            HIGH PRIORITY INTERESTS:
            - Artificial Intelligence, Machine Learning, AI agents
            - Tech startups (especially software)
            - Software development, programming
            - Mathematics, statistics
            - Behavioral economics, behavioral finance

            MEDIUM PRIORITY INTERESTS:
            - Robotics, hardware
            - Politics (Trump, UK, Europe)
            - Health, wellness, running
            - Books, reading

            LOW PRIORITY INTERESTS:
            - Music technology

            STORY TO EVALUATE:
            Title: {title}
            URL: {url}

            Respond with only "RELEVANT" or "NOT_RELEVANT" and a brief 1-sentence explanation.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model for simple classification
                messages=[
                    {"role": "system", "content": "You are a content relevance classifier. Be concise and accurate."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            is_relevant = result.upper().startswith("RELEVANT")
            
            if is_relevant:
                print(f"✅ AI marked as relevant: {result}")
            else:
                print(f"❌ AI marked as not relevant: {result}")
                
            return is_relevant
            
        except Exception as e:
            print(f"❌ Error in AI relevance filtering: {str(e)}")
            # Fallback to True to avoid missing potentially relevant stories
            return True
    
    def get_article_summary(self, url: str) -> Optional[str]:
        """
        Get AI-powered summary of external article
        """
        try:
            # Basic web scraping to get article content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content with better selectors
            content = ""
            
            # Try common article content selectors first
            content_selectors = [
                'article', '[role="main"]', 'main', '.content', '.post-content', 
                '.article-content', '.entry-content', '.post-body'
            ]
            
            content_found = False
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = " ".join([elem.get_text() for elem in elements])
                    content_found = True
                    break
            
            # Fallback to paragraph extraction
            if not content_found:
                paragraphs = soup.find_all('p')
                content = " ".join([p.get_text() for p in paragraphs])
            
            # Clean up content
            content = ' '.join(content.split())  # Remove extra whitespace
            
            if len(content) < 100:
                return "Article content too short to summarize effectively."
            
            # Truncate content if too long (to stay within token limits)
            if len(content) > 8000:
                content = content[:8000] + "..."
            
            # Use AI to summarize
            prompt = f"""
            Create a detailed, specific summary of this article. Include concrete details, numbers, quotes, specific technologies, company names, and actionable insights. Avoid generic statements.

            Requirements:
            - Include specific technical details, metrics, or numbers mentioned
            - Quote key phrases or statements from the article
            - Mention specific tools, technologies, companies, or people by name
            - Highlight concrete examples or use cases
            - Focus on actionable insights or specific claims
            - CRITICAL: If the article mentions any of these key terms, you MUST include them exactly in your summary: "artificial intelligence", "AI", "machine learning", "ML", "programming", "software development", "tech startups", "startup", "robotics", "hardware", "mathematics", "statistics", "behavioral economics", "behavioral finance"
            - Preserve exact technical terminology and acronyms (e.g., "API" not "api", "PostgreSQL" not "postgres")
            - 3-4 sentences maximum but pack them with specifics

            Article content:
            {content}
            
            Specific summary with concrete details:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective for summarization
                messages=[
                    {"role": "system", "content": "You are a technical article summarizer. Create concise, informative summaries that capture the key insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content.strip()
            print(f"✅ AI generated summary: {summary[:100]}...")
            return summary
            
        except Exception as e:
            print(f"❌ Error getting AI article summary for {url}: {str(e)}")
            # Fallback to basic truncation
            try:
                if 'content' in locals() and content:
                    return content[:300].strip() + "..." if len(content) > 300 else content.strip()
            except:
                pass
            return None
    
    def analyze_comments(self, hn_discussion_url: str, num_comments=10) -> Dict:
        """
        Scrape and analyze comments from HN discussion page
        Enhanced with basic theme extraction (AI analysis placeholder)
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
            
            # Wait for comments to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comment")))
            
            # Get top-level comments (not replies)
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
            
            # Basic analysis (will be enhanced with AI later)
            analysis = self._analyze_comment_themes(comments_data)
            analysis["top_comments"] = comments_data
            
            print(f"  ✅ Analyzed {len(comments_data)} comments")
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
            
            # Get comment content
            comment_span = comment_elem.find_element(By.CLASS_NAME, "commtext")
            comment_text = comment_span.text.strip()
            
            # Get author and metadata
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
    
    def _analyze_comment_themes(self, comments_data: List[Dict]) -> Dict:
        """
        AI-powered comment theme analysis and sentiment extraction
        """
        if not comments_data:
            return {
                "total_comments_analyzed": 0,
                "main_themes": [],
                "agreement_points": [],
                "disagreement_points": [],
                "sentiment_summary": "No comments to analyze"
            }
        
        try:
            # Prepare comment text for analysis (limit to top comments to manage token usage)
            top_comments = comments_data[:8]  # Analyze top 8 comments to balance quality and cost
            comments_text = []
            
            for i, comment in enumerate(top_comments, 1):
                comment_preview = comment["text"][:500] + "..." if len(comment["text"]) > 500 else comment["text"]
                comments_text.append(f"Comment {i}: {comment_preview}")
            
            all_comments = "\n\n".join(comments_text)
            
            # AI analysis prompt
            prompt = f"""
            Analyze these Hacker News comments with specific details and quotes. You MUST respond with valid JSON only.

            IMPORTANT: You are analyzing ONLY THE TOP {len(top_comments)} COMMENTS from a larger discussion. 
            Do NOT mention the specific number of comments in your sentiment_summary.
            Focus on the content and themes, not the quantity.

            COMMENTS:
            {all_comments}

            Extract specific insights with concrete details:
            - main_themes: Specific topics discussed (include tools, technologies, companies mentioned)
            - agreement_points: What people specifically agree with (include short quotes in "quotes")
            - disagreement_points: Specific criticisms or counter-arguments (include short quotes)
            - sentiment_summary: Concrete description of the discussion themes and viewpoints WITHOUT mentioning comment count

            Respond with only this JSON structure (no other text):
            {{
                "main_themes": ["Specific topic 1 (e.g., 'Performance issues with React hooks')", "Specific topic 2"],
                "agreement_points": ["'Quote showing agreement' - specific point they agree with", "Another specific agreement"],
                "disagreement_points": ["'Quote showing disagreement' - specific criticism", "Another specific counter-argument"],
                "sentiment_summary": "Description of the main discussion points, concerns, and viewpoints (do NOT mention number of comments)"
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Good balance of quality and cost for analysis
                messages=[
                    {"role": "system", "content": "You are a discussion analyst who extracts specific quotes, concrete details, and technical specifics from discussions. You MUST respond with only valid JSON, no additional text or explanation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3,  # Lower temperature for more consistent JSON output
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                import json as json_module
                ai_analysis = json_module.loads(result)
                print(f"✅ AI comment analysis completed: {len(ai_analysis.get('main_themes', []))} themes found")
            except json_module.JSONDecodeError:
                # Fallback if JSON parsing fails
                print("⚠️ AI response wasn't valid JSON, using fallback parsing")
                ai_analysis = {
                    "main_themes": ["AI analysis parsing error - see raw response"],
                    "agreement_points": [result[:200] + "..." if len(result) > 200 else result],
                    "disagreement_points": [],
                    "sentiment_summary": "Analysis error occurred"
                }
            
            return {
                "total_comments_analyzed": len(comments_data),
                "main_themes": ai_analysis.get("main_themes", ["No themes identified"]),
                "agreement_points": ai_analysis.get("agreement_points", ["No agreement points identified"]),
                "disagreement_points": ai_analysis.get("disagreement_points", ["No disagreement points identified"]),
                "sentiment_summary": ai_analysis.get("sentiment_summary", "Sentiment analysis unavailable"),
                "comment_stats": {
                    "total_comments": len(comments_data),
                    "avg_comment_length": sum([c["length"] for c in comments_data]) // len(comments_data) if comments_data else 0,
                    "comments_with_scores": len([c for c in comments_data if c["score"] is not None]),
                    "top_comments_analyzed": len(top_comments)
                }
            }
            
        except Exception as e:
            print(f"❌ Error in AI comment analysis: {str(e)}")
            # Fallback to basic analysis
            all_text = " ".join([comment["text"].lower() for comment in comments_data])
            
            return {
                "total_comments_analyzed": len(comments_data),
                "main_themes": ["AI analysis failed - basic fallback used"],
                "agreement_points": ["Analysis error occurred"],
                "disagreement_points": ["Analysis error occurred"],
                "sentiment_summary": f"AI analysis failed, analyzed {len(comments_data)} comments",
                "comment_stats": {
                    "total_comments": len(comments_data),
                    "avg_comment_length": sum([c["length"] for c in comments_data]) // len(comments_data) if comments_data else 0,
                    "comments_with_scores": len([c for c in comments_data if c["score"] is not None])
                }
            }
    
    def generate_executive_summary(self, story_data: Dict) -> str:
        """
        Generate an executive summary combining article and comments analysis
        This will be enhanced with AI summarization later
        """
        title = story_data.get('title', 'Unknown Title')
        points = story_data.get('points', 0)
        comments_count = story_data.get('comments_count', 0)
        author = story_data.get('author', 'Unknown')
        time_posted = story_data.get('time_posted', 'Unknown')
        
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
        
        # Header
        summary_parts.append(f"## {title}")
        summary_parts.append(f"**Stats:** {points} points, {comments_count} comments by {author} ({time_posted})")
        summary_parts.append("")
        
        # Article summary
        summary_parts.append("### Article Summary")
        if article_summary and article_summary != "No article summary available":
            summary_parts.append(article_summary)
        else:
            summary_parts.append("*Article content not accessible or this is a discussion post*")
        summary_parts.append("")
        
        # Comments analysis
        if total_comments_analyzed > 0:
            summary_parts.append("### Discussion Analysis")
            summary_parts.append(f"**Analyzed {total_comments_analyzed} top comments**")
            
            if themes and themes != ["PLACEHOLDER: AI will identify themes here"]:
                summary_parts.append(f"**Main themes:** {', '.join(themes)}")
            
            summary_parts.append(f"**Community sentiment:** {sentiment}")
            
            # Show top comment if available
            top_comments = comments_analysis.get('top_comments', [])
            if top_comments:
                top_comment = top_comments[0]
                comment_preview = top_comment['text'][:200] + "..." if len(top_comment['text']) > 200 else top_comment['text']
                summary_parts.append(f"**Top comment by {top_comment['author']}:** {comment_preview}")
        else:
            summary_parts.append("### Discussion Analysis")
            summary_parts.append("*No comments available for analysis*")
        
        summary_parts.append("")
        summary_parts.append(f"**🔗 Read more:** {story_data.get('url', 'No URL')}")
        summary_parts.append(f"**💬 Join discussion:** {story_data.get('hn_discussion_url', 'No discussion URL')}")
        summary_parts.append("")
        summary_parts.append("---")
        
        return "\n".join(summary_parts)
    
    def generate_daily_email_content(self, daily_data: Dict) -> str:
        """
        Generate formatted email content from daily scraping results
        """
        scrape_date = daily_data.get('scrape_date', 'Unknown date')
        total_stories = daily_data.get('total_stories', 0)
        relevant_stories = daily_data.get('relevant_stories', 0)
        stories = daily_data.get('stories', [])
        
        # Filter only relevant stories
        relevant_story_data = [story for story in stories if story.get('is_relevant', False)]
        
        email_parts = []
        
        # Email header
        email_parts.append("# 📰 Your Daily Hacker News Digest")
        email_parts.append(f"*Generated on {scrape_date[:10]} at {scrape_date[11:19]}*")
        email_parts.append("")
        email_parts.append(f"**Summary:** Found {relevant_stories} relevant stories out of {total_stories} total stories")
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
        
        # Footer
        email_parts.append("---")
        email_parts.append("📧 *This digest was automatically generated by your Hacker News scraper*")
        email_parts.append(f"🤖 *Processed {sum([s.get('comments_analysis', {}).get('total_comments_analyzed', 0) for s in relevant_story_data])} comments across all stories*")
        
        return "\n".join(email_parts)
    
    def process_daily_stories(self) -> Dict:
        """Main function to process daily stories"""
        print("🚀 Starting daily Hacker News scraping...")
        
        # Scrape top 30 stories
        stories = self.scrape_top_stories(30)
        
        processed_stories = []
        relevant_count = 0
        
        for story in stories:
            print(f"\n📰 Processing: {story['title'][:50]}...")
            
            # Always get article summary and comment analysis for all stories
            # This ensures the web dashboard has rich AI content for every story
            
            # Get article summary if it's an external link
            article_summary = None
            if not story['url'].startswith('https://news.ycombinator.com'):
                print("📄 Getting article summary...")
                article_summary = self.get_article_summary(story['url'])
            
            # Analyze comments for all stories
            print("💬 Analyzing comments...")
            comments_analysis = self.analyze_comments(story['hn_discussion_url'])
            
            # Now check if story is relevant for email filtering
            is_relevant = self.is_relevant_story(story)
            if is_relevant:
                relevant_count += 1
                print(f"✅ Story marked as relevant ({relevant_count}/30)")
            else:
                print("❌ Story not relevant for email")
            
            # Add processed data to story
            story.update({
                "article_summary": article_summary,
                "comments_analysis": comments_analysis,
                "is_relevant": is_relevant
            })
            
            processed_stories.append(story)
            
            # Add small delay to be respectful to servers
            time.sleep(1)
        
        result = {
            "scrape_date": datetime.now().isoformat(),
            "total_stories": len(stories),
            "relevant_stories": relevant_count,
            "stories": processed_stories
        }
        
        print(f"\n✅ Daily scraping complete! Found {relevant_count} relevant stories out of {len(stories)} total.")
        return result
    
    def save_to_json(self, data: Dict, filename: str = None):
        """Save scraped data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hn_scrape_{timestamp}.json"
        
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
    """Main function to run daily scraping"""
    scraper = HackerNewsScraper()
    
    try:
        # Process daily stories
        daily_data = scraper.process_daily_stories()
        
        # Save to JSON
        json_filename = scraper.save_to_json(daily_data)
        
        # Generate email content
        email_content = scraper.generate_daily_email_content(daily_data)
        
        # Save email content
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        email_filename = f"daily_digest_{timestamp}.md"
        with open(email_filename, 'w', encoding='utf-8') as f:
            f.write(email_content)
        
        print(f"\n🎉 Daily scraping completed successfully!")
        print(f"📊 Results: {daily_data['relevant_stories']} relevant stories found")
        print(f"💾 Data saved to: {json_filename}")
        print(f"📧 Email content saved to: {email_filename}")
        
    except Exception as e:
        print(f"❌ Error during daily scraping: {str(e)}")
    finally:
        scraper.close()

def test_email_generation():
    """Test function to generate a sample email digest with just a few stories"""
    print("🧪 Testing email generation with 3 stories...")
    scraper = HackerNewsScraper()
    
    try:
        # Get top 3 stories with full processing
        stories = scraper.scrape_top_stories(3)
        
        processed_stories = []
        for story in stories:
            print(f"\n📰 Processing: {story['title'][:50]}...")
            
            # Process as if relevant
            if not story['url'].startswith('https://news.ycombinator.com'):
                article_summary = scraper.get_article_summary(story['url'])
            else:
                article_summary = None
            
            comments_analysis = scraper.analyze_comments(story['hn_discussion_url'], num_comments=3)
            
            story.update({
                "article_summary": article_summary,
                "comments_analysis": comments_analysis,
                "is_relevant": True
            })
            processed_stories.append(story)
        
        # Create test daily data
        test_data = {
            "scrape_date": datetime.now().isoformat(),
            "total_stories": 3,
            "relevant_stories": 3,
            "stories": processed_stories
        }
        
        # Generate email content
        email_content = scraper.generate_daily_email_content(test_data)
        
        # Save test email
        test_filename = f"test_digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write(email_content)
        
        print(f"\n✅ Test completed! Email preview saved to: {test_filename}")
        print("\n📧 Email preview (first 500 chars):")
        print("=" * 50)
        print(email_content[:500] + "...")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_email_generation()
    else:
        main()