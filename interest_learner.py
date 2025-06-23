#!/usr/bin/env python3
"""
Interest Learning System for HN Scraper
Automatically adjusts interest weights based on user feedback
"""

import re
import sqlite3
from typing import Dict, List, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import math

class InterestLearner:
    def __init__(self, db_path: str = "hn_scraper.db"):
        self.db_path = db_path
        
        # Learning parameters (tunable)
        self.learning_rate = 0.10  # How much to adjust weights (10% change per feedback)
        self.min_weight = 0.1      # Minimum weight (never go below)
        self.max_weight = 1.0      # Maximum weight
        self.decay_factor = 0.98   # Slight decay for old feedback (2% less impact over time)
        self.min_feedback_count = 3  # Minimum feedback needed before adjusting weights
        
    def analyze_user_feedback(self, days_back: int = 30) -> Dict:
        """
        Analyze user feedback patterns over the last N days
        Returns analysis of what keywords correlate with positive/negative feedback
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all interactions with story details from last N days
            # Note: relevance_score now comes from user_story_relevance table in multi-user schema
            cursor.execute("""
                SELECT 
                    ui.interaction_type,
                    ui.timestamp,
                    s.title,
                    s.url,
                    COALESCE(usr.relevance_score, 0.0) as relevance_score
                FROM user_interactions ui
                JOIN stories s ON ui.story_id = s.id
                LEFT JOIN user_story_relevance usr ON s.id = usr.story_id AND ui.user_id = usr.user_id
                WHERE ui.interaction_type IN ('thumbs_up', 'thumbs_down')
                AND ui.timestamp > datetime('now', '-{} days')
                ORDER BY ui.timestamp DESC
            """.format(days_back))
            
            interactions = cursor.fetchall()
            
        if not interactions:
            return {"status": "no_feedback", "message": "No feedback data found"}
        
        # Analyze feedback patterns
        positive_feedback = []  # Stories user liked
        negative_feedback = []  # Stories user disliked
        
        for interaction_type, timestamp, title, url, relevance_score in interactions:
            story_data = {
                "title": title,
                "url": url,
                "relevance_score": relevance_score,
                "timestamp": timestamp
            }
            
            if interaction_type == "thumbs_up":
                positive_feedback.append(story_data)
            elif interaction_type == "thumbs_down":
                negative_feedback.append(story_data)
        
        # Extract keywords from titles
        positive_keywords = self._extract_keywords_from_stories(positive_feedback)
        negative_keywords = self._extract_keywords_from_stories(negative_feedback)
        
        return {
            "status": "success",
            "positive_count": len(positive_feedback),
            "negative_count": len(negative_feedback),
            "positive_keywords": positive_keywords,
            "negative_keywords": negative_keywords,
            "total_interactions": len(interactions)
        }
    
    def _extract_keywords_from_stories(self, stories: List[Dict]) -> Counter:
        """Extract and count keywords from story titles"""
        keyword_counter = Counter()
        
        for story in stories:
            title = story["title"].lower()
            
            # Extract meaningful keywords (filter out common words)
            words = re.findall(r'\b[a-zA-Z]{3,}\b', title)  # Words with 3+ characters
            
            # Filter out common stop words
            stop_words = {
                'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
                'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
                'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
                'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'why', 'with',
                'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time',
                'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many',
                'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what', 'your'
            }
            
            meaningful_words = [word for word in words if word not in stop_words and len(word) > 3]
            keyword_counter.update(meaningful_words)
        
        return keyword_counter
    
    def calculate_weight_adjustments(self, feedback_analysis: Dict) -> Dict[str, float]:
        """
        Calculate how much to adjust each interest weight based on feedback
        Returns dict of {keyword: adjustment_value} where positive = increase, negative = decrease
        """
        if feedback_analysis["status"] != "success":
            return {}
        
        adjustments = {}
        total_feedback = feedback_analysis["positive_count"] + feedback_analysis["negative_count"]
        
        if total_feedback < self.min_feedback_count:
            print(f"⚠️ Not enough feedback ({total_feedback} < {self.min_feedback_count}), skipping weight adjustments")
            return {}
        
        # Get current interests from database
        current_interests = self._get_current_interests()
        
        # Calculate adjustments for keywords that appear in feedback
        positive_keywords = feedback_analysis["positive_keywords"]
        negative_keywords = feedback_analysis["negative_keywords"]
        
        # Process positive feedback (increase weights)
        for keyword, count in positive_keywords.most_common(10):  # Top 10 positive keywords
            # Check if this keyword matches any existing interests
            matching_interests = self._find_matching_interests(keyword, current_interests)
            
            for interest_keyword in matching_interests:
                # Calculate adjustment based on frequency and total feedback
                adjustment = (count / total_feedback) * self.learning_rate
                adjustments[interest_keyword] = adjustments.get(interest_keyword, 0) + adjustment
                
        # Process negative feedback (decrease weights)
        for keyword, count in negative_keywords.most_common(10):  # Top 10 negative keywords
            matching_interests = self._find_matching_interests(keyword, current_interests)
            
            for interest_keyword in matching_interests:
                # Negative adjustment
                adjustment = -(count / total_feedback) * self.learning_rate
                adjustments[interest_keyword] = adjustments.get(interest_keyword, 0) + adjustment
        
        # Also look for new keywords that might be interests
        self._suggest_new_interests(positive_keywords, negative_keywords, current_interests)
        
        return adjustments
    
    def _get_current_interests(self) -> Dict[str, Dict]:
        """Get current interest weights from database"""
        interests = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT keyword, weight, category FROM interest_weights
            """)
            
            for keyword, weight, category in cursor.fetchall():
                interests[keyword.lower()] = {
                    "keyword": keyword,
                    "weight": weight,
                    "category": category
                }
        
        return interests
    
    def _find_matching_interests(self, feedback_keyword: str, current_interests: Dict) -> List[str]:
        """Find existing interests that match a keyword from feedback"""
        matches = []
        feedback_keyword = feedback_keyword.lower()
        
        for interest_key, interest_data in current_interests.items():
            interest_keyword = interest_data["keyword"].lower()
            
            # Direct match
            if feedback_keyword == interest_keyword:
                matches.append(interest_data["keyword"])
            # Partial match (e.g., "machine" matches "machine learning")
            elif feedback_keyword in interest_keyword or interest_keyword in feedback_keyword:
                matches.append(interest_data["keyword"])
            # Handle abbreviations (e.g., "ai" matches "artificial intelligence")
            elif self._is_abbreviation_match(feedback_keyword, interest_keyword):
                matches.append(interest_data["keyword"])
            # Handle common variations and related terms
            elif self._is_related_term(feedback_keyword, interest_keyword):
                matches.append(interest_data["keyword"])
        
        return matches
    
    def _is_abbreviation_match(self, short_word: str, long_phrase: str) -> bool:
        """Check if short_word could be an abbreviation of long_phrase"""
        if len(short_word) > 4:  # Only check very short words as potential abbreviations
            return False
        
        abbreviation_maps = {
            "ai": ["artificial intelligence"],
            "ml": ["machine learning"],
            "uk": ["united kingdom"],
            "us": ["united states"],
            "js": ["javascript"],
            "py": ["python"],
            "db": ["database"],
            "api": ["application programming interface"]
        }
        
        return long_phrase in abbreviation_maps.get(short_word, [])
    
    def _is_related_term(self, feedback_keyword: str, interest_keyword: str) -> bool:
        """Check if feedback keyword is related to an interest"""
        # Define related terms that should affect certain interests
        related_terms = {
            "artificial intelligence": ["neural", "deep", "learning", "model", "training", "inference", "llm", "gpt", "claude", "openai", "anthropic"],
            "machine learning": ["neural", "deep", "model", "training", "algorithm", "prediction", "classification", "regression"],
            "programming": ["code", "coding", "developer", "software", "bug", "debug", "github", "commit", "function", "variable"],
            "tech startups": ["funding", "seed", "series", "venture", "capital", "investors", "ipo", "unicorn", "valuation"],
            "mathematics": ["algorithm", "equation", "formula", "calculation", "statistics", "probability", "theorem"],
            "statistics": ["data", "analysis", "probability", "distribution", "correlation", "regression", "variance"],
            "robotics": ["robot", "automation", "mechanical", "sensor", "actuator", "autonomous"],
            "hardware": ["chip", "processor", "memory", "storage", "semiconductor", "silicon", "gpu", "cpu"]
        }
        
        interest_lower = interest_keyword.lower()
        feedback_lower = feedback_keyword.lower()
        
        # Check if feedback keyword is in the related terms for this interest
        for interest_key, related_list in related_terms.items():
            if interest_key in interest_lower:
                if feedback_lower in related_list:
                    return True
        
        return False
    
    def _suggest_new_interests(self, positive_keywords: Counter, negative_keywords: Counter, current_interests: Dict):
        """Suggest new interests based on frequently liked keywords"""
        # Find keywords that appear frequently in positive feedback but aren't in current interests
        suggestions = []
        
        for keyword, count in positive_keywords.most_common(5):
            if count >= 3:  # Appeared in at least 3 positive stories
                # Check if it's already covered by existing interests
                if not self._find_matching_interests(keyword, current_interests):
                    suggestions.append({
                        "keyword": keyword,
                        "positive_count": count,
                        "suggested_weight": min(0.6, count * 0.1),  # Weight based on frequency
                        "suggested_category": "medium"  # Start with medium priority
                    })
        
        if suggestions:
            print(f"💡 Suggested new interests based on your feedback: {[s['keyword'] for s in suggestions]}")
            # Store suggestions in database for future review
            self._store_interest_suggestions(suggestions)
    
    def _store_interest_suggestions(self, suggestions: List[Dict]):
        """Store interest suggestions in database for user review"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create suggestions table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interest_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    suggested_weight REAL NOT NULL,
                    suggested_category TEXT NOT NULL,
                    positive_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            # Insert suggestions
            for suggestion in suggestions:
                cursor.execute("""
                    INSERT OR IGNORE INTO interest_suggestions
                    (keyword, suggested_weight, suggested_category, positive_count, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    suggestion["keyword"],
                    suggestion["suggested_weight"],
                    suggestion["suggested_category"],
                    suggestion["positive_count"],
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    def apply_weight_adjustments(self, adjustments: Dict[str, float]) -> Dict:
        """Apply calculated weight adjustments to the database"""
        if not adjustments:
            return {"status": "no_changes", "message": "No weight adjustments to apply"}
        
        applied_changes = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for keyword, adjustment in adjustments.items():
                # Get current weight
                cursor.execute("""
                    SELECT keyword, weight, category FROM interest_weights
                    WHERE LOWER(keyword) = LOWER(?)
                """, (keyword,))
                
                result = cursor.fetchone()
                if not result:
                    continue
                
                actual_keyword, current_weight, category = result
                new_weight = current_weight + adjustment
                
                # Apply bounds
                new_weight = max(self.min_weight, min(self.max_weight, new_weight))
                
                # Only update if change is significant (>0.5%)
                if abs(new_weight - current_weight) > 0.005:
                    cursor.execute("""
                        UPDATE interest_weights 
                        SET weight = ?, updated_at = ?
                        WHERE LOWER(keyword) = LOWER(?)
                    """, (new_weight, datetime.now().isoformat(), keyword))
                    
                    applied_changes[actual_keyword] = {
                        "old_weight": round(current_weight, 3),
                        "new_weight": round(new_weight, 3),
                        "change": round(adjustment, 3)
                    }
            
            conn.commit()
        
        return {
            "status": "success",
            "changes_applied": len(applied_changes),
            "changes": applied_changes
        }
    
    def run_learning_cycle(self, days_back: int = 30) -> Dict:
        """
        Run a complete learning cycle: analyze feedback → calculate adjustments → apply changes
        """
        print(f"🧠 Running interest learning cycle (analyzing last {days_back} days)...")
        
        # Step 1: Analyze feedback
        feedback_analysis = self.analyze_user_feedback(days_back)
        if feedback_analysis["status"] != "success":
            return feedback_analysis
        
        print(f"📊 Found {feedback_analysis['total_interactions']} interactions:")
        print(f"   👍 {feedback_analysis['positive_count']} positive")
        print(f"   👎 {feedback_analysis['negative_count']} negative")
        
        # Step 2: Calculate adjustments
        adjustments = self.calculate_weight_adjustments(feedback_analysis)
        if not adjustments:
            return {"status": "no_changes", "message": "No weight adjustments calculated"}
        
        print(f"🔧 Calculated {len(adjustments)} weight adjustments")
        
        # Step 3: Apply changes
        results = self.apply_weight_adjustments(adjustments)
        
        if results["status"] == "success":
            print(f"✅ Applied {results['changes_applied']} weight changes:")
            for keyword, change_data in results["changes"].items():
                direction = "↗️" if change_data["change"] > 0 else "↘️"
                print(f"   {direction} {keyword}: {change_data['old_weight']} → {change_data['new_weight']}")
            
            # Refresh AI pipeline embeddings if there were changes
            if results['changes_applied'] > 0:
                self._refresh_ai_pipeline()
        
        return results
    
    def _refresh_ai_pipeline(self):
        """Refresh the AI pipeline to use updated interest weights"""
        try:
            from ai_pipeline import CostOptimizedAI
            
            # The AI pipeline will automatically load updated interests from database
            # when initialized, so we just need to signal that embeddings should be refreshed
            print("🔄 Interest weights updated - AI pipeline will use new weights on next run")
            
        except ImportError:
            print("⚠️ AI pipeline not available for refresh")
        except Exception as e:
            print(f"⚠️ Error refreshing AI pipeline: {e}")
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about the learning system"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total interactions
            cursor.execute("""
                SELECT COUNT(*) FROM user_interactions 
                WHERE interaction_type IN ('thumbs_up', 'thumbs_down')
            """)
            total_feedback = cursor.fetchone()[0]
            
            # Get positive feedback count
            cursor.execute("""
                SELECT COUNT(*) FROM user_interactions 
                WHERE interaction_type = 'thumbs_up'
            """)
            positive_feedback = cursor.fetchone()[0]
            
            # Get negative feedback count
            cursor.execute("""
                SELECT COUNT(*) FROM user_interactions 
                WHERE interaction_type = 'thumbs_down'
            """)
            negative_feedback = cursor.fetchone()[0]
            
            # Get unique stories with feedback
            cursor.execute("""
                SELECT COUNT(DISTINCT story_id) FROM user_interactions 
                WHERE interaction_type IN ('thumbs_up', 'thumbs_down')
            """)
            unique_stories_with_feedback = cursor.fetchone()[0]
            
            # Get users with feedback
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM user_interactions 
                WHERE interaction_type IN ('thumbs_up', 'thumbs_down')
            """)
            users_with_feedback = cursor.fetchone()[0]
            
            # Get recent interactions (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) FROM user_interactions 
                WHERE interaction_type IN ('thumbs_up', 'thumbs_down')
                AND timestamp > datetime('now', '-7 days')
            """)
            recent_feedback = cursor.fetchone()[0]
            
            # Get interest update count
            cursor.execute("""
                SELECT COUNT(*) FROM interest_weights
                WHERE updated_at > datetime('now', '-30 days')
            """)
            recent_updates = cursor.fetchone()[0]
            
            # Get suggestions count (create table if not exists)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interest_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    suggested_weight REAL NOT NULL,
                    suggested_category TEXT NOT NULL,
                    positive_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """)
            cursor.execute("""
                SELECT COUNT(*) FROM interest_suggestions
                WHERE status = 'pending'
            """)
            pending_suggestions = cursor.fetchone()[0]
        
        return {
            "total_feedback": total_feedback,
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "unique_stories_with_feedback": unique_stories_with_feedback,
            "users_with_feedback": users_with_feedback,
            "recent_feedback": recent_feedback,
            "recent_updates": recent_updates,
            "pending_suggestions": pending_suggestions,
            "learning_enabled": total_feedback >= self.min_feedback_count
        }

def test_interest_learner():
    """Test the interest learning system"""
    learner = InterestLearner()
    
    print("🧪 Testing Interest Learning System...")
    
    # Get stats
    stats = learner.get_learning_stats()
    print(f"📊 Learning Stats: {stats}")
    
    # Run learning cycle
    results = learner.run_learning_cycle(days_back=30)
    print(f"🔄 Learning Results: {results}")

if __name__ == "__main__":
    test_interest_learner()