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
        
        # Clear any proxy environment variables that might interfere with OpenAI client
        import httpx
        try:
            self.openai_client = OpenAI(
                api_key=api_key,
                http_client=httpx.Client(proxies=None)  # Explicitly disable proxies
            )
        except Exception as e:
            # Fallback to basic initialization if httpx approach fails
            print(f"⚠️  Falling back to basic OpenAI client due to: {e}")
            self.openai_client = OpenAI(api_key=api_key)
        
        # Initialize local embedding model (lightweight and fast)
        print("🔄 Loading local embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 22MB model, very fast
        print("✅ Local embedding model loaded")
        
        # Set up caching
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load user interests from database (fallback to defaults if database not available)
        self.user_interests = self._load_interests_from_database()
        
        # Pre-compute interest embeddings for fast comparison
        self._compute_interest_embeddings()
        
        # Load cached article summaries
        self.article_cache = self._load_article_cache()
        
        # Cost tracking
        self.api_calls_saved = 0
        self.api_calls_made = 0
    
    def _load_interests_from_database(self) -> Dict:
        """Load user interests from database, fallback to defaults if not available"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))
            from database import DatabaseManager
            
            # Try to load from database
            db = DatabaseManager()
            interest_weights = db.get_interest_weights()
            
            if not interest_weights:
                print("⚠️ No global interests found in database, using defaults")
                print("   (User-specific interests may still be provided during filtering)")
                return self._get_default_interests()
            
            # Group interests by category
            user_interests = {"high_priority": [], "medium_priority": [], "low_priority": []}
            for interest in interest_weights:
                category_key = f"{interest.category}_priority"
                if category_key in user_interests:
                    user_interests[category_key].append(interest.keyword)
            
            print(f"✅ Loaded {len(interest_weights)} interests from database")
            return user_interests
            
        except Exception as e:
            print(f"⚠️ Could not load interests from database: {e}")
            print("   Using default interests")
            return self._get_default_interests()
    
    def _get_default_interests(self) -> Dict:
        """Get default interests as fallback"""
        return {
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
    
    def _compute_interest_embeddings(self):
        """Pre-compute embeddings for user interests"""
        print("🔄 Computing interest embeddings...")
        
        self.interest_embeddings = {}
        # Single weight for all interests - no priority system
        self.single_weight = 1.0
        
        for category, keywords in self.user_interests.items():
            embeddings = self.embedding_model.encode(keywords)
            self.interest_embeddings[category] = {
                'embeddings': embeddings,
                'keywords': keywords,
                'weight': self.single_weight  # Always 1.0
            }
        
        print("✅ Interest embeddings computed")
    
    def refresh_interests(self):
        """Reload interests from database and recompute embeddings"""
        print("🔄 Refreshing interests from database...")
        self.user_interests = self._load_interests_from_database()
        self._compute_interest_embeddings()
        print("✅ Interests refreshed successfully")
    
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
    
    def is_relevant_story_local(self, story_data: Dict, user_interests: Optional[Dict] = None) -> Tuple[bool, float, str]:
        """
        Fast local relevance filtering using embeddings
        Now supports user-specific interests for multi-user filtering
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
        
        # Use user-specific interests if provided, otherwise fall back to defaults
        interests_to_use = self.interest_embeddings
        if user_interests:
            # Recompute embeddings for user-specific interests
            print(f"🔍 Using user-specific interests: {user_interests}")
            interests_to_use = self._compute_user_interest_embeddings(user_interests)
            print(f"✅ Computed embeddings for {len(interests_to_use)} categories")
        else:
            print(f"⚠️ Using default interests (no user interests provided)")
        
        # Compare against all interest categories
        for category, data in interests_to_use.items():
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
        relevance_threshold = 0.25  # Balanced threshold for technical content
        is_relevant = max_similarity > relevance_threshold
        
        reasoning = f"Best match: '{best_match}' ({best_category}) - similarity: {max_similarity:.3f}"
        
        if is_relevant:
            print(f"✅ Local filter: RELEVANT - {reasoning}")
        else:
            print(f"❌ Local filter: NOT RELEVANT - {reasoning}")
            self.api_calls_saved += 1  # Saved an OpenAI call
        
        return is_relevant, max_similarity, reasoning
    
    def is_relevant_story_ai_refined(self, story_data: Dict, local_score: float, user_interests: Optional[Dict] = None) -> bool:
        """
        Use OpenAI for edge cases where local filtering is uncertain
        Only called for stories with medium confidence scores
        """
        title = story_data.get('title', '')
        url = story_data.get('url', '')
        
        # Only use AI for uncertain cases (0.3-0.5 similarity range)
        if local_score < 0.3 or local_score > 0.5:
            return local_score > 0.25  # Use local decision with correct threshold
        
        try:
            # Build interest description from user interests or defaults
            if user_interests:
                interest_desc = self._build_interest_description(user_interests)
            else:
                interest_desc = "AI/ML, tech startups, software development, mathematics, behavioral economics"
            
            prompt = f"""
            Quick relevance check for someone interested in: {interest_desc}.
            
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
            - CRITICAL: If the article mentions any of these key terms, you MUST include them exactly in your summary: "artificial intelligence", "AI", "machine learning", "ML", "programming", "software development", "tech startups", "startup", "robotics", "hardware", "mathematics", "statistics", "behavioral economics", "behavioral finance"
            - Preserve exact technical terminology and acronyms (e.g., "API" not "api", "PostgreSQL" not "postgres")
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
            Extract detailed, specific, quantitative insights from these {len(top_comments)} Hacker News comments. Focus on concrete information with CONTEXT explaining why it matters.

            CRITICAL: Every piece of data must include context explaining its significance.

            EXAMPLES OF GOOD VS BAD EXTRACTION:

            GOOD (with context):
            - "One developer mentioned maintaining 700k line legacy ERP systems, highlighting how technical debt becomes overwhelming in enterprise software"
            - "Users report RTX 4090 GPUs ($1500) can run 70B models with 4-bit quantization, but inference drops to 5 tokens/sec compared to 50 tokens/sec on H100 ($30k), showing the performance vs cost tradeoff"
            - "Multiple teams switched from OpenAI API to local models, saving $5k-10k monthly but requiring 32GB+ RAM and accepting 3x slower response times"

            BAD (random numbers without context):
            - "700k lines of code"
            - "RTX 4090" 
            - "$5k monthly"
            - "32GB RAM"

            COMMENTS:
            {all_comments}

            Return this exact JSON structure with detailed, contextual information:
            {{
                "technical_details": {{
                    "specific_numbers": ["Include context: Why do these numbers matter? What do they represent?"],
                    "tools_mentioned": ["Tool name + why it's being discussed + any performance/cost context"],
                    "performance_data": ["Performance metric + comparison + what this means for users"],
                    "hardware_specs": ["Hardware requirement + use case + cost/benefit context"]
                }},
                "cost_analysis": {{
                    "price_comparisons": ["Cost comparison + what you get for the price difference"],
                    "resource_requirements": ["Resource needed + for what purpose + impact if you don't have it"],
                    "efficiency_gains": ["Efficiency improvement + method used + real-world impact"]
                }},
                "implementation_insights": {{
                    "setup_instructions": ["Setup step + why it's needed + what happens if skipped"],
                    "configuration_details": ["Config setting + optimal value + impact on performance/quality"],
                    "compatibility_issues": ["What breaks + under what conditions + how to avoid/fix"]
                }},
                "community_consensus": {{
                    "strong_agreements": ["What community agrees on + why + supporting evidence"],
                    "major_disagreements": ["What people debate + different positions + reasoning behind each"],
                    "expert_opinions": ["Expert view + their credentials/experience + why this matters"]
                }},
                "business_intelligence": {{
                    "market_trends": ["Trend description + supporting evidence + business implications"],
                    "company_strategies": ["Company approach + reasoning + competitive advantage/risk"],
                    "competitive_landscape": ["Competition dynamic + market forces + opportunities/threats"]
                }},
                "success_failure_stories": {{
                    "working_setups": ["Successful implementation + specific setup + results achieved"],
                    "failed_attempts": ["What failed + why it failed + lessons learned"],
                    "performance_reports": ["Performance achieved + setup used + comparison to alternatives"]
                }},
                "specific_recommendations": {{
                    "actionable_advice": ["Recommendation + reasoning + expected outcome"],
                    "what_to_avoid": ["What not to do + why + consequences of doing it anyway"],
                    "optimization_tips": ["Optimization technique + implementation + performance gain"]
                }},
                "sentiment_summary": "Detailed multi-sentence summary capturing the nuanced discussion with specific examples and concrete details mentioned by the community"
            }}
            
            CRITICAL REQUIREMENTS:
            - NEVER include standalone numbers/names without explaining their significance
            - Each item must answer: What is it? Why does it matter? What's the impact?
            - Focus on insights that save readers 30+ minutes of research
            - Include 2-3 detailed, contextual items per section when content exists
            - Use empty array [] only when genuinely no relevant content exists
            - NO quotes inside strings, NO line breaks inside strings
            - Extract maximum concrete information with full context
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a discussion analyst. Respond with only valid JSON, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,  # Increased to ensure 2-3 items per section minimum
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean up common JSON issues
            if result.startswith('```json'):
                result = result.replace('```json', '').replace('```', '').strip()
            
            # Additional cleanup for common issues
            result = result.replace('\n', ' ').replace('\r', ' ')  # Remove line breaks
            result = result.replace('""', '"').replace('\\', '')   # Fix double quotes and escapes
            
            try:
                ai_analysis = json.loads(result)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing error: {e}")
                print(f"Raw response (first 300 chars): {result[:300]}...")
                
                # Return fallback structure for parsing errors
                ai_analysis = {
                    "technical_details": {
                        "specific_numbers": ["Parsing error - see raw response"],
                        "tools_mentioned": [],
                        "performance_data": [],
                        "hardware_specs": []
                    },
                    "cost_analysis": {
                        "price_comparisons": [],
                        "resource_requirements": [],
                        "efficiency_gains": []
                    },
                    "implementation_insights": {
                        "setup_instructions": [],
                        "configuration_details": [],
                        "compatibility_issues": []
                    },
                    "community_consensus": {
                        "strong_agreements": [],
                        "major_disagreements": [],
                        "expert_opinions": []
                    },
                    "business_intelligence": {
                        "market_trends": [],
                        "company_strategies": [],
                        "competitive_landscape": []
                    },
                    "success_failure_stories": {
                        "working_setups": [],
                        "failed_attempts": [],
                        "performance_reports": []
                    },
                    "specific_recommendations": {
                        "actionable_advice": [],
                        "what_to_avoid": [],
                        "optimization_tips": []
                    },
                    "sentiment_summary": "Analysis failed due to JSON parsing error"
                }
            
            self.api_calls_made += 1
            
            # Convert detailed analysis to backward-compatible format while preserving rich data
            technical_details = ai_analysis.get("technical_details", {})
            cost_analysis = ai_analysis.get("cost_analysis", {})
            implementation = ai_analysis.get("implementation_insights", {})
            consensus = ai_analysis.get("community_consensus", {})
            business = ai_analysis.get("business_intelligence", {})
            stories = ai_analysis.get("success_failure_stories", {})
            recommendations = ai_analysis.get("specific_recommendations", {})
            
            # Create short, concise main themes (keywords/phrases only)
            main_themes = []
            
            # Extract short keywords from tools mentioned
            for tool_desc in technical_details.get("tools_mentioned", [])[:3]:
                # Extract just the tool/tech name from the description
                words = tool_desc.split()[:3]  # Take first few words only
                for word in words:
                    if word.lower() in ['claude', 'gemini', 'gpt', 'openai', 'anthropic', 'llama', 'pytorch', 'tensorflow', 'redis', 'postgres', 'docker', 'kubernetes', 'react', 'vue', 'angular', 'python', 'javascript', 'rust', 'go', 'java', 'ai', 'ml', 'exif']:
                        main_themes.append(word.capitalize())
                        break
                    elif len(word) > 3 and word.isalpha():  # Generic tech term
                        main_themes.append(word.capitalize())
                        break
            
            # Add short business themes
            for trend_desc in business.get("market_trends", [])[:2]:
                # Extract key business terms
                words = trend_desc.lower().split()
                business_keywords = ['ai', 'automation', 'productivity', 'enterprise', 'startup', 'funding', 'growth', 'market', 'adoption', 'integration']
                for keyword in business_keywords:
                    if keyword in words:
                        main_themes.append(keyword.capitalize())
                        break
            
            # Remove duplicates and limit to 4 items
            main_themes = list(dict.fromkeys(main_themes))[:4]
            
            if not main_themes:
                main_themes = ["AI tools", "Business adoption"]
            
            # Combine agreement and disagreement points
            agreement_points = consensus.get("strong_agreements", [])
            disagreement_points = consensus.get("major_disagreements", [])
            
            # IMPORTANT: Generate top comment summary if we have comments
            # NOTE TO SELF: User specifically requested this feature - DO NOT REMOVE!
            # This provides AI-generated summaries of the top comment on each story
            top_comment_summary = None
            if comments_data and len(comments_data) > 0:
                top_comment = comments_data[0]
                if len(top_comment['text']) > 100:  # Only summarize substantial comments
                    try:
                        summary_prompt = f"""
                        Summarize this top Hacker News comment in 1-2 concise sentences. Focus on the key point or insight the commenter is making.
                        
                        IMPORTANT: If the comment mentions any of these key terms, you MUST include them exactly in your summary: "artificial intelligence", "AI", "machine learning", "ML", "programming", "software development", "tech startups", "startup", "robotics", "hardware", "mathematics", "statistics", "behavioral economics", "behavioral finance". Preserve exact technical terminology and acronyms.
                        
                        Comment by {top_comment['author']}:
                        {top_comment['text'][:500]}
                        
                        Summary (1-2 sentences, focus on main insight):
                        """
                        
                        summary_response = self.openai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a comment summarizer. Create brief, insightful summaries of comments."},
                                {"role": "user", "content": summary_prompt}
                            ],
                            max_tokens=100,
                            temperature=0.3
                        )
                        
                        top_comment_summary = summary_response.choices[0].message.content.strip()
                        self.api_calls_made += 1
                        print(f"✅ Generated top comment summary: {top_comment_summary[:50]}...")
                        
                    except Exception as e:
                        print(f"⚠️ Error generating top comment summary: {e}")
                        top_comment_summary = None

            return {
                "total_comments_analyzed": len(comments_data),
                "main_themes": main_themes,
                "agreement_points": agreement_points,
                "disagreement_points": disagreement_points,
                "sentiment_summary": ai_analysis.get("sentiment_summary", "Analysis completed with detailed insights"),
                "top_comment_summary": top_comment_summary,
                
                # Preserve all detailed analysis in new fields
                "detailed_technical_analysis": technical_details,
                "detailed_cost_analysis": cost_analysis,
                "detailed_implementation": implementation,
                "detailed_consensus": consensus,
                "detailed_business_intelligence": business,
                "detailed_success_stories": stories,
                "detailed_recommendations": recommendations,
                
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
                "sentiment_summary": f"Analysis error, processed {len(comments_data)} comments",
                "top_comment_summary": "Summary not available due to analysis error",
                "structured_sentiment": {}
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
    
    def _compute_user_interest_embeddings(self, user_interests: Dict) -> Dict:
        """
        Compute embeddings for user-specific interests
        Expected format: {'high_priority': ['keyword1', 'keyword2'], 'medium_priority': [...], ...}
        Or database format: [UserInterestWeight objects]
        """
        interest_embeddings = {}
        
        # Handle both dict format and database object format
        if isinstance(user_interests, dict) and user_interests and isinstance(list(user_interests.values())[0], list):
            # Dictionary format from form data
            # Always use weight 1.0 regardless of category
            
            for category, keywords in user_interests.items():
                if keywords:  # Only process non-empty categories
                    embeddings = self.embedding_model.encode(keywords)
                    interest_embeddings[category] = {
                        'embeddings': embeddings,
                        'keywords': keywords,
                        'weight': 1.0  # Single weight for all interests
                    }
        else:
            # Database UserInterestWeight objects format
            categories = {}
            for interest in user_interests:
                if interest.category not in categories:
                    categories[interest.category] = {
                        'keywords': [],
                        'weights': []
                    }
                categories[interest.category]['keywords'].append(interest.keyword)
                categories[interest.category]['weights'].append(interest.weight)
            
            for category, data in categories.items():
                embeddings = self.embedding_model.encode(data['keywords'])
                # Always use weight 1.0, ignore stored weights from database
                interest_embeddings[category] = {
                    'embeddings': embeddings,
                    'keywords': data['keywords'],
                    'weight': 1.0  # Single weight for all interests
                }
        
        return interest_embeddings
    
    def _build_interest_description(self, user_interests: Dict) -> str:
        """Build a natural language description of user interests for AI prompts"""
        if isinstance(list(user_interests.values())[0], list):
            # Dictionary format
            all_interests = []
            for category, keywords in user_interests.items():
                if keywords:
                    all_interests.extend(keywords)
            return ", ".join(all_interests[:10])  # Limit to first 10 for prompt length
        else:
            # Database objects format
            keywords = [interest.keyword for interest in user_interests[:10]]
            return ", ".join(keywords)

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