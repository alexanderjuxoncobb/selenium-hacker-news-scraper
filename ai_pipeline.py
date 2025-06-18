#!/usr/bin/env python3
"""
Cost-Optimized AI Pipeline for HN Scraper
Uses local embeddings for initial filtering, OpenAI only for final analysis
"""

import os
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from dotenv import load_dotenv

class CostOptimizedAI:
    def __init__(self, openai_api_key: Optional[str] = None, cache_dir: str = ".ai_cache"):
        """Initialize the cost-optimized AI pipeline"""
        load_dotenv()
        
        # Initialize OpenAI client
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.openai_client = OpenAI(api_key=api_key)
        
        # Initialize local embedding model (lightweight and fast)
        print("🔄 Loading local embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 22MB model, very fast
        print("✅ Local embedding model loaded")
        
        # Set up caching
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # User interests for local filtering
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
        
        # Pre-compute interest embeddings for fast comparison
        self._compute_interest_embeddings()
        
        # Load cached article summaries
        self.article_cache = self._load_article_cache()
        
        # Cost tracking
        self.api_calls_saved = 0
        self.api_calls_made = 0
    
    def _compute_interest_embeddings(self):
        """Pre-compute embeddings for user interests"""
        print("🔄 Computing interest embeddings...")
        
        self.interest_embeddings = {}
        self.interest_weights = {
            "high_priority": 1.0,
            "medium_priority": 0.6,
            "low_priority": 0.3
        }
        
        for category, keywords in self.user_interests.items():
            embeddings = self.embedding_model.encode(keywords)
            self.interest_embeddings[category] = {
                'embeddings': embeddings,
                'keywords': keywords,
                'weight': self.interest_weights[category]
            }
        
        print("✅ Interest embeddings computed")
    
    def _load_article_cache(self) -> Dict:
        """Load cached article summaries"""
        cache_file = os.path.join(self.cache_dir, "article_summaries.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cache = pickle.load(f)
                print(f"✅ Loaded {len(cache)} cached article summaries")
                return cache
            except Exception as e:
                print(f"⚠️ Error loading article cache: {e}")
        return {}
    
    def _save_article_cache(self):
        """Save article summaries to cache"""
        cache_file = os.path.join(self.cache_dir, "article_summaries.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.article_cache, f)
        except Exception as e:
            print(f"⚠️ Error saving article cache: {e}")
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content to enable caching"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def is_relevant_story_local(self, story_data: Dict) -> Tuple[bool, float, str]:
        """
        Fast local relevance filtering using embeddings
        Returns (is_relevant, confidence_score, reasoning)
        """
        title = story_data.get('title', '')
        url = story_data.get('url', '')
        
        # Combine title and URL domain for analysis
        domain = url.split('//')[1].split('/')[0] if '//' in url else ''
        text_to_analyze = f"{title} {domain}"
        
        # Get embedding for the story
        story_embedding = self.embedding_model.encode([text_to_analyze])
        
        max_similarity = 0.0
        best_match = ""
        best_category = ""
        
        # Compare against all interest categories
        for category, data in self.interest_embeddings.items():
            similarities = cosine_similarity(story_embedding, data['embeddings'])[0]
            max_sim_in_category = np.max(similarities)
            
            # Weight the similarity by category importance
            weighted_similarity = max_sim_in_category * data['weight']
            
            if weighted_similarity > max_similarity:
                max_similarity = weighted_similarity
                best_match_idx = np.argmax(similarities)
                best_match = data['keywords'][best_match_idx]
                best_category = category
        
        # Threshold for relevance (tunable)
        relevance_threshold = 0.35  # Lowered threshold for broader matching
        is_relevant = max_similarity > relevance_threshold
        
        reasoning = f"Best match: '{best_match}' ({best_category}) - similarity: {max_similarity:.3f}"
        
        if is_relevant:
            print(f"✅ Local filter: RELEVANT - {reasoning}")
        else:
            print(f"❌ Local filter: NOT RELEVANT - {reasoning}")
            self.api_calls_saved += 1  # Saved an OpenAI call
        
        return is_relevant, max_similarity, reasoning
    
    def is_relevant_story_ai_refined(self, story_data: Dict, local_score: float) -> bool:
        """
        Use OpenAI for edge cases where local filtering is uncertain
        Only called for stories with medium confidence scores
        """
        title = story_data.get('title', '')
        url = story_data.get('url', '')
        
        # Only use AI for uncertain cases (0.3-0.5 similarity range)
        if local_score < 0.3 or local_score > 0.5:
            return local_score > 0.35  # Use local decision
        
        try:
            prompt = f"""
            Quick relevance check for someone interested in: AI/ML, tech startups, software development, mathematics, behavioral economics.
            
            Story: "{title}"
            URL: {url}
            
            Respond with only "YES" or "NO" - is this relevant?
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a relevance classifier. Respond only with YES or NO."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip().upper()
            is_relevant = result == "YES"
            
            self.api_calls_made += 1
            print(f"🤖 AI refinement: {'RELEVANT' if is_relevant else 'NOT RELEVANT'} (local score: {local_score:.3f})")
            
            return is_relevant
            
        except Exception as e:
            print(f"❌ Error in AI refinement: {e}")
            # Fallback to local decision
            return local_score > 0.35
    
    def get_article_summary_cached(self, url: str, force_refresh: bool = False) -> Optional[str]:
        """
        Get article summary with intelligent caching
        """
        # Generate cache key from URL
        url_hash = self._get_content_hash(url)
        
        # Check cache first (unless forced refresh)
        if not force_refresh and url_hash in self.article_cache:
            cached_entry = self.article_cache[url_hash]
            cache_date = datetime.fromisoformat(cached_entry['cached_at'])
            
            # Use cache if less than 7 days old
            if datetime.now() - cache_date < timedelta(days=7):
                print(f"📋 Using cached summary for {url[:50]}...")
                self.api_calls_saved += 1
                return cached_entry['summary']
        
        # Get fresh summary using existing logic from scraper
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content
            content = ""
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
            
            if not content_found:
                paragraphs = soup.find_all('p')
                content = " ".join([p.get_text() for p in paragraphs])
            
            content = ' '.join(content.split())
            
            if len(content) < 100:
                return "Article content too short to summarize effectively."
            
            # Truncate for token limits
            if len(content) > 8000:
                content = content[:8000] + "..."
            
            # Use OpenAI for summary
            prompt = f"""
            Create a detailed, specific summary of this article. Include concrete details, numbers, quotes, specific technologies, company names, and actionable insights.

            Requirements:
            - Include specific technical details, metrics, or numbers mentioned
            - Quote key phrases or statements from the article
            - Mention specific tools, technologies, companies, or people by name
            - Highlight concrete examples or use cases
            - Focus on actionable insights or specific claims
            - 3-4 sentences maximum but pack them with specifics

            Article content:
            {content}
            
            Specific summary with concrete details:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a technical article summarizer. Create concise, informative summaries that capture key insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content.strip()
            self.api_calls_made += 1
            
            # Cache the result
            self.article_cache[url_hash] = {
                'url': url,
                'summary': summary,
                'cached_at': datetime.now().isoformat()
            }
            self._save_article_cache()
            
            print(f"✅ AI generated fresh summary: {summary[:100]}...")
            return summary
            
        except Exception as e:
            print(f"❌ Error getting article summary for {url}: {e}")
            return None
    
    def analyze_comments_efficient(self, comments_data: List[Dict]) -> Dict:
        """
        Efficient comment analysis using local processing + targeted AI
        """
        if not comments_data:
            return {
                "total_comments_analyzed": 0,
                "main_themes": [],
                "agreement_points": [],
                "disagreement_points": [],
                "sentiment_summary": "No comments to analyze"
            }
        
        # Quick local analysis first
        all_text = " ".join([comment["text"].lower() for comment in comments_data])
        comment_count = len(comments_data)
        avg_length = sum([len(comment["text"]) for comment in comments_data]) // comment_count
        
        # Only use AI for substantial discussions (5+ comments)
        if comment_count < 5:
            return {
                "total_comments_analyzed": comment_count,
                "main_themes": ["Limited discussion"],
                "agreement_points": [f"Only {comment_count} comments available"],
                "disagreement_points": [],
                "sentiment_summary": f"Brief discussion with {comment_count} comments"
            }
        
        # Use AI for detailed analysis on substantial discussions
        try:
            top_comments = comments_data[:6]  # Analyze fewer comments to save tokens
            comments_text = []
            
            for i, comment in enumerate(top_comments, 1):
                comment_preview = comment["text"][:400] + "..." if len(comment["text"]) > 400 else comment["text"]
                comments_text.append(f"Comment {i}: {comment_preview}")
            
            all_comments = "\n\n".join(comments_text)
            
            prompt = f"""
            Analyze these {len(top_comments)} Hacker News comments. You MUST respond with valid JSON only.

            COMMENTS:
            {all_comments}

            Extract specific insights with concrete details:
            {{
                "main_themes": ["Specific topic 1", "Specific topic 2"],
                "agreement_points": ["Specific agreement with quote", "Another agreement"],
                "disagreement_points": ["Specific criticism with quote", "Counter-argument"],
                "sentiment_summary": "Concrete description mentioning specific concerns or tools discussed"
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a discussion analyst. Respond with only valid JSON, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,  # Reduced token usage
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content.strip()
            ai_analysis = json.loads(result)
            self.api_calls_made += 1
            
            return {
                "total_comments_analyzed": len(comments_data),
                "main_themes": ai_analysis.get("main_themes", ["Analysis failed"]),
                "agreement_points": ai_analysis.get("agreement_points", []),
                "disagreement_points": ai_analysis.get("disagreement_points", []),
                "sentiment_summary": ai_analysis.get("sentiment_summary", "Analysis completed"),
                "comment_stats": {
                    "total_comments": len(comments_data),
                    "avg_comment_length": avg_length,
                    "comments_with_scores": len([c for c in comments_data if c.get("score") is not None])
                }
            }
            
        except Exception as e:
            print(f"❌ Error in AI comment analysis: {e}")
            # Fallback to simple analysis
            return {
                "total_comments_analyzed": len(comments_data),
                "main_themes": ["AI analysis failed - basic fallback used"],
                "agreement_points": [f"Discussion with {len(comments_data)} comments"],
                "disagreement_points": [],
                "sentiment_summary": f"Analysis error, processed {len(comments_data)} comments"
            }
    
    def get_cost_report(self) -> Dict:
        """Get cost optimization report"""
        total_potential_calls = self.api_calls_made + self.api_calls_saved
        if total_potential_calls == 0:
            savings_percentage = 0
        else:
            savings_percentage = (self.api_calls_saved / total_potential_calls) * 100
        
        # Rough cost calculation (gpt-4o-mini pricing)
        cost_per_call = 0.002  # Rough estimate for typical summarization call
        money_saved = self.api_calls_saved * cost_per_call
        money_spent = self.api_calls_made * cost_per_call
        
        return {
            "api_calls_made": self.api_calls_made,
            "api_calls_saved": self.api_calls_saved,
            "savings_percentage": round(savings_percentage, 1),
            "estimated_money_saved": round(money_saved, 3),
            "estimated_money_spent": round(money_spent, 3),
            "cache_size": len(self.article_cache)
        }

def test_cost_optimization():
    """Test the cost-optimized pipeline"""
    ai = CostOptimizedAI()
    
    # Test stories
    test_stories = [
        {"title": "New Machine Learning Framework Beats PyTorch", "url": "https://example.com/ml"},
        {"title": "Celebrity Gossip Update", "url": "https://tmz.com/celebrity"},
        {"title": "Startup Raises $50M for AI Assistant", "url": "https://techcrunch.com/startup"},
        {"title": "Music Festival Lineup Announced", "url": "https://music.com/festival"},
    ]
    
    print("🧪 Testing cost-optimized relevance filtering...")
    
    for story in test_stories:
        is_relevant, score, reasoning = ai.is_relevant_story_local(story)
        print(f"📊 {story['title'][:40]}... -> {'✅' if is_relevant else '❌'} ({score:.3f})")
    
    # Print cost report
    report = ai.get_cost_report()
    print(f"\n💰 Cost Report:")
    print(f"   API calls saved: {report['api_calls_saved']}")
    print(f"   API calls made: {report['api_calls_made']}")
    print(f"   Savings: {report['savings_percentage']}%")
    print(f"   Estimated money saved: ${report['estimated_money_saved']}")

if __name__ == "__main__":
    test_cost_optimization()