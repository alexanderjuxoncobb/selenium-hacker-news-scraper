#!/usr/bin/env python3
"""
Database models and operations for HN Scraper Dashboard
"""

import sqlite3
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import os
import uuid

@dataclass
class Story:
    id: Optional[int]
    date: str
    rank: int
    story_id: str  # HN story ID for deduplication
    title: str
    url: str
    points: int
    author: str
    comments_count: int
    hn_discussion_url: str
    article_summary: Optional[str]
    scraped_at: str
    was_cached: bool = False
    comments_analysis: Optional[Dict] = None
    tags: Optional[List[str]] = None

@dataclass
class UserStoryRelevance:
    id: Optional[int]
    user_id: str
    story_id: int  # References stories.id
    is_relevant: bool
    relevance_score: float
    relevance_reasoning: Optional[str]
    calculated_at: str

@dataclass
class UserInteraction:
    id: Optional[int]
    user_id: str  # UUID to identify which user
    story_id: int
    interaction_type: str  # 'click', 'read', 'save', 'share', 'thumbs_up', 'thumbs_down'
    timestamp: str
    duration_seconds: Optional[int] = None

@dataclass
class User:
    id: Optional[int]
    user_id: str  # UUID
    email: str
    name: Optional[str]
    created_at: str
    last_active_at: Optional[str]

@dataclass
class UserInterestWeight:
    id: Optional[int]
    user_id: str  # UUID
    keyword: str
    weight: float
    category: str  # 'high', 'medium', 'low'
    updated_at: str

@dataclass
class InterestWeight:
    id: Optional[int]
    keyword: str
    weight: float
    category: str  # 'high', 'medium', 'low'
    updated_at: str

class DatabaseManager:
    def __init__(self, db_path: str = "hn_scraper.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables and handle migrations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if we need to migrate existing database
            self._migrate_to_multi_user(cursor)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,  -- UUID
                    email TEXT NOT NULL,
                    name TEXT,
                    created_at TEXT NOT NULL,
                    last_active_at TEXT
                )
            """)
            
            # Stories table (shared across users with tags for better categorization)
            # Note: is_relevant and relevance_score moved to user_story_relevance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    story_id TEXT,  -- HN story ID for deduplication
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    points INTEGER DEFAULT 0,
                    author TEXT,
                    comments_count INTEGER DEFAULT 0,
                    hn_discussion_url TEXT,
                    article_summary TEXT,
                    comments_analysis TEXT,  -- JSON string
                    scraped_at TEXT NOT NULL,
                    was_cached BOOLEAN DEFAULT FALSE,  -- Track if story was served from cache
                    tags TEXT,  -- JSON array of semantic tags for categorization
                    UNIQUE(date, rank)
                )
            """)
            
            # Add story_id column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE stories ADD COLUMN story_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            # Note: For existing databases, is_relevant and relevance_score columns will still exist
            # but won't be used. New relevance data goes in user_story_relevance table.
            
            # User interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    story_id INTEGER NOT NULL,
                    interaction_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_seconds INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (story_id) REFERENCES stories (id)
                )
            """)
            
            # User-specific interest weights table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interest_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    weight REAL NOT NULL,
                    category TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, keyword)
                )
            """)
            
            # Global interest weights table (for default templates)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interest_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    weight REAL NOT NULL,
                    category TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # User-specific story relevance table (replaces is_relevant in stories table)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_story_relevance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    story_id INTEGER NOT NULL,
                    is_relevant BOOLEAN NOT NULL,
                    relevance_score REAL NOT NULL,
                    relevance_reasoning TEXT,
                    calculated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (story_id) REFERENCES stories (id),
                    UNIQUE(user_id, story_id)
                )
            """)
            
            # User-specific story notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS story_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    story_id INTEGER NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (story_id) REFERENCES stories (id),
                    UNIQUE(user_id, story_id)
                )
            """)
            
            conn.commit()
            
            # Create indexes for better performance (after tables are created)
            self._create_indexes(cursor)
    
    def _create_indexes(self, cursor):
        """Create database indexes"""
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_date ON stories (date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_story_id ON stories (story_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_interactions (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_story ON user_interactions (story_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions (interaction_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_interests_user ON user_interest_weights (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relevance_user_story ON user_story_relevance (user_id, story_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relevance_user ON user_story_relevance (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_story ON story_notes (user_id, story_id)")
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    def import_json_data(self, json_file_path: str):
        """Import data from existing JSON scraping files"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            scrape_date = data.get('scrape_date', '')[:10]  # Get YYYY-MM-DD part
            stories = data.get('stories', [])
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for story in stories:
                    # Convert comments_analysis to JSON string if it exists
                    comments_analysis_json = None
                    if story.get('comments_analysis'):
                        comments_analysis_json = json.dumps(story['comments_analysis'])
                    
                    # Convert tags to JSON string if it exists
                    tags_json = None
                    if story.get('tags'):
                        tags_json = json.dumps(story['tags'])
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO stories 
                        (date, rank, story_id, title, url, points, author, comments_count, 
                         hn_discussion_url, article_summary, comments_analysis, 
                         scraped_at, was_cached, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        scrape_date,
                        story.get('rank', 0),
                        story.get('story_id', ''),
                        story.get('title', ''),
                        story.get('url', ''),
                        story.get('points', 0),
                        story.get('author', ''),
                        story.get('comments_count', 0),
                        story.get('hn_discussion_url', ''),
                        story.get('article_summary'),
                        comments_analysis_json,
                        story.get('scraped_at', data.get('scrape_date', '')),
                        story.get('was_cached', False),
                        tags_json
                    ))
                
                conn.commit()
                print(f"✅ Imported {len(stories)} stories from {json_file_path}")
                
        except Exception as e:
            print(f"❌ Error importing JSON data: {str(e)}")
    
    def import_multi_user_json_data(self, json_file_path: str, user_id: str = None) -> None:
        """Import multi-user JSON data with user-specific relevance"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            scrape_date = data.get('scrape_date', '')[:10]  # Get YYYY-MM-DD part
            stories = data.get('stories', [])
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for story in stories:
                    # Convert comments_analysis to JSON string if it exists
                    comments_analysis_json = None
                    if story.get('comments_analysis'):
                        comments_analysis_json = json.dumps(story['comments_analysis'])
                    
                    # Convert tags to JSON string if it exists
                    tags_json = None
                    if story.get('tags'):
                        tags_json = json.dumps(story['tags'])
                    
                    # Insert story (without relevance fields)
                    cursor.execute("""
                        INSERT OR REPLACE INTO stories 
                        (date, rank, story_id, title, url, points, author, comments_count, 
                         hn_discussion_url, article_summary, comments_analysis, 
                         scraped_at, was_cached, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        scrape_date,
                        story.get('rank', 0),
                        story.get('story_id', ''),
                        story.get('title', ''),
                        story.get('url', ''),
                        story.get('points', 0),
                        story.get('author', ''),
                        story.get('comments_count', 0),
                        story.get('hn_discussion_url', ''),
                        story.get('article_summary'),
                        comments_analysis_json,
                        story.get('scraped_at', data.get('scrape_date', '')),
                        story.get('was_cached', False),
                        tags_json
                    ))
                    
                    # Get the story ID for relevance storage
                    story_db_id = cursor.lastrowid
                    
                    # Store user-specific relevance if user_id provided and relevance data exists
                    if user_id and 'is_relevant' in story:
                        cursor.execute("""
                            INSERT OR REPLACE INTO user_story_relevance 
                            (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            story_db_id,
                            story.get('is_relevant', False),
                            story.get('relevance_score', 0.0),
                            story.get('relevance_reasoning'),
                            datetime.now().isoformat()
                        ))
                
                conn.commit()
                print(f"✅ Imported {len(stories)} stories from {json_file_path}")
                if user_id:
                    print(f"✅ Stored relevance data for user {user_id}")
                
        except Exception as e:
            print(f"❌ Error importing multi-user JSON data: {str(e)}")
    
    def get_stories_by_date(self, target_date: str) -> List[Story]:
        """Get all stories for a specific date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, date, rank, story_id, title, url, points, author, comments_count,
                       hn_discussion_url, article_summary, comments_analysis,
                       scraped_at, COALESCE(was_cached, 0) as was_cached, tags
                FROM stories 
                WHERE date = ? 
                ORDER BY rank
            """, (target_date,))
            
            rows = cursor.fetchall()
            stories = []
            
            for row in rows:
                comments_analysis = None
                if row[11]:  # comments_analysis column
                    try:
                        comments_analysis = json.loads(row[11])
                    except json.JSONDecodeError:
                        pass
                
                tags = None
                if row[14]:  # tags column
                    try:
                        tags = json.loads(row[14])
                    except json.JSONDecodeError:
                        pass
                
                story = Story(
                    id=row[0], date=row[1], rank=row[2], story_id=row[3], title=row[4], url=row[5],
                    points=row[6], author=row[7], comments_count=row[8],
                    hn_discussion_url=row[9], article_summary=row[10],
                    scraped_at=row[12], was_cached=bool(row[13]), 
                    comments_analysis=comments_analysis, tags=tags
                )
                stories.append(story)
            
            return stories
    
    def story_exists_by_hn_id(self, story_id: str) -> bool:
        """Check if a story with the given HN story ID already exists in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stories WHERE story_id = ?", (story_id,))
            return cursor.fetchone()[0] > 0
    
    def store_user_story_relevance(self, user_id: str, story_db_id: int, is_relevant: bool, 
                                 relevance_score: float, relevance_reasoning: str = None) -> None:
        """Store user-specific relevance data for a story"""
        # Ensure relevance_score is a proper float
        try:
            relevance_score = float(relevance_score)
        except (ValueError, TypeError):
            relevance_score = 0.0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Debug what we're storing
            print(f"🔍 Storing relevance: user_id={user_id}, story_id={story_db_id}, is_relevant={is_relevant} (type: {type(is_relevant)}), score={relevance_score}")
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_story_relevance 
                (user_id, story_id, is_relevant, relevance_score, relevance_reasoning, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, story_db_id, int(is_relevant), relevance_score, 
                relevance_reasoning, datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_user_story_relevance(self, user_id: str, story_db_id: int) -> Optional[UserStoryRelevance]:
        """Get user-specific relevance for a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, story_id, is_relevant, relevance_score, 
                       relevance_reasoning, calculated_at
                FROM user_story_relevance 
                WHERE user_id = ? AND story_id = ?
            """, (user_id, story_db_id))
            
            row = cursor.fetchone()
            if row:
                return UserStoryRelevance(
                    id=row[0], user_id=row[1], story_id=row[2],
                    is_relevant=bool(row[3]), relevance_score=row[4],
                    relevance_reasoning=row[5], calculated_at=row[6]
                )
            return None
    
    def get_stories_with_user_relevance(self, user_id: str, target_date: str) -> List[Tuple[Story, Optional[UserStoryRelevance]]]:
        """Get stories for a date with user-specific relevance data"""
        # Check if user can access this date
        user = self.get_user(user_id)
        if user:
            signup_date = user.created_at.split('T')[0]  # Get YYYY-MM-DD from ISO format
            if target_date < signup_date:
                return []  # User cannot access stories before their signup date
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.date, s.rank, s.story_id, s.title, s.url, s.points, s.author, 
                       s.comments_count, s.hn_discussion_url, s.article_summary, s.comments_analysis,
                       s.scraped_at, COALESCE(s.was_cached, 0) as was_cached, s.tags,
                       r.id as rel_id, r.is_relevant, r.relevance_score, r.relevance_reasoning, r.calculated_at
                FROM stories s
                LEFT JOIN user_story_relevance r ON s.id = r.story_id AND r.user_id = ?
                WHERE s.date = ? AND s.date >= (SELECT date(created_at) FROM users WHERE user_id = ?)
                ORDER BY s.rank
            """, (user_id, target_date, user_id))
            
            rows = cursor.fetchall()
            results = []
            
            for row in rows:
                # Parse comments_analysis
                comments_analysis = None
                if row[11]:
                    try:
                        comments_analysis = json.loads(row[11])
                    except json.JSONDecodeError:
                        pass
                
                # Parse tags
                tags = None
                if row[14]:
                    try:
                        tags = json.loads(row[14])
                    except json.JSONDecodeError:
                        pass
                
                # Create Story object
                story = Story(
                    id=row[0], date=row[1], rank=row[2], story_id=row[3], title=row[4], url=row[5],
                    points=row[6], author=row[7], comments_count=row[8],
                    hn_discussion_url=row[9], article_summary=row[10],
                    scraped_at=row[12], was_cached=bool(row[13]), 
                    comments_analysis=comments_analysis, tags=tags
                )
                
                # Create UserStoryRelevance object if relevance data exists
                relevance = None
                if row[15] is not None:  # rel_id
                    # Handle potential data type issues with relevance_score
                    try:
                        score = float(row[17]) if row[17] is not None else 0.0
                    except (ValueError, TypeError):
                        # If score is corrupted (e.g., blob data), default to 0.0
                        print(f"⚠️ Corrupted relevance score for story {row[0]}, user {user_id}")
                        score = 0.0
                    
                    relevance = UserStoryRelevance(
                        id=row[15], user_id=user_id, story_id=row[0],
                        is_relevant=bool(row[16]), relevance_score=score,
                        relevance_reasoning=row[18], calculated_at=row[19]
                    )
                
                results.append((story, relevance))
            
            return results
    
    def get_relevant_stories_by_date(self, target_date: str) -> List[Story]:
        """Get only relevant stories for a specific date (legacy method)"""
        # Note: This method is deprecated since relevance is now user-specific
        # Keeping for backward compatibility
        stories = self.get_stories_by_date(target_date)
        return stories  # Return all stories since relevance is user-specific now
    
    def get_user_relevant_stories_by_date(self, user_id: str, target_date: str) -> List[Story]:
        """Get stories relevant to a specific user for a specific date based on their interests"""
        # First get all stories for the date
        all_stories = self.get_stories_by_date(target_date)
        
        # Get user's interest weights
        user_interests = self.get_user_interest_weights(user_id)
        
        if not user_interests:
            # If user has no specific interests, fall back to globally relevant stories
            return [story for story in all_stories if story.is_relevant]
        
        # Create user-specific filtering based on interests and story tags
        relevant_stories = []
        for story in all_stories:
            if self._is_story_relevant_to_user(story, user_interests):
                relevant_stories.append(story)
        
        return relevant_stories
    
    def _is_story_relevant_to_user(self, story: Story, user_interests: List[UserInterestWeight], debug: bool = False) -> bool:
        """Determine if a story is relevant to a specific user based on their interests"""
        if not user_interests:
            return False  # If user has no interests, don't show any stories
        
        # Create a lookup of user interests by keyword (case-insensitive)
        interest_lookup = {}
        for interest in user_interests:
            interest_lookup[interest.keyword.lower()] = interest.weight
        
        # Calculate relevance score based on story content and user interests
        relevance_score = 0.0
        matched_interests = 0
        
        # Analyze story content (title + summary if available)
        story_text = story.title.lower()
        if story.article_summary:
            story_text += " " + story.article_summary.lower()
        
        story_tags = [tag.lower() for tag in story.tags] if story.tags else []
        
        if debug:
            print(f"🔍 Checking story: {story.title[:50]}...")
            print(f"   Story tags: {story_tags}")
            print(f"   User interests: {list(interest_lookup.keys())}")
            print(f"   Story text: {story_text[:100]}...")
        
        # Score based on direct keyword matches in title and content
        for keyword, weight in interest_lookup.items():
            if keyword in story_text:
                relevance_score += weight
                matched_interests += 1
                if debug:
                    print(f"   ✅ Content match: '{keyword}' (weight: {weight})")
        
        # Semantic keyword expansion for better matching
        keyword_expansions = {
            'hardware': ['hardware', 'chip', 'processor', 'cpu', 'gpu', 'semiconductor', 'circuit', 'device', 'electronics'],
            'ai': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 'llm', 'gpt', 'claude', 'chatgpt', 'model', 'algorithm'],
            'programming': ['programming', 'code', 'software', 'development', 'developer', 'coding', 'python', 'javascript', 'api'],
            'startups': ['startup', 'startups', 'founder', 'funding', 'venture', 'vc', 'investment', 'entrepreneur'],
            'politics': ['politics', 'government', 'election', 'policy', 'trump', 'biden', 'congress'],
            'robotics': ['robot', 'robotics', 'automation', 'mechanical', 'servo', 'actuator']
        }
        
        # Check expanded keywords
        for keyword, weight in interest_lookup.items():
            if keyword in keyword_expansions:
                for expanded_keyword in keyword_expansions[keyword]:
                    if expanded_keyword in story_text and expanded_keyword != keyword:  # Avoid double counting
                        relevance_score += weight * 0.7  # Expanded matches get 70% weight
                        matched_interests += 1
                        if debug:
                            print(f"   ✅ Expanded match: '{expanded_keyword}' -> '{keyword}' (weight: {weight * 0.7})")
                        break  # Only count first expansion match per keyword
        
        # Enhanced tag matching (if tags are available)
        if story_tags:
            tag_to_interests_mapping = {
                'ai': ['artificial intelligence', 'ai', 'machine learning', 'ml'],
                'programming': ['programming', 'software development', 'code', 'development'],
                'web': ['web', 'programming', 'software development'],
                'mobile': ['mobile', 'programming', 'software development'],
                'startup': ['tech startups', 'startup', 'startups'],
                'business': ['business', 'economics', 'finance'],
                'politics': ['politics'],
                'science': ['science', 'physics', 'biology'],
                'hardware': ['hardware', 'robotics'],
                'security': ['security'],
                'climate': ['climate', 'environment'],
                'space': ['space'],
                'general': [],  # General stories don't match specific interests
                'community': [],
                'product': [],
                'educational': ['programming', 'software development']
            }
            
            # Check each story tag against user interests
            for tag in story_tags:
                if tag in tag_to_interests_mapping:
                    possible_interests = tag_to_interests_mapping[tag]
                    for possible_interest in possible_interests:
                        if possible_interest in interest_lookup:
                            weight = interest_lookup[possible_interest]
                            relevance_score += weight * 0.8  # Tag matches get 80% of keyword weight
                            matched_interests += 1
                            if debug:
                                print(f"   ✅ Tag match: '{tag}' -> '{possible_interest}' (weight: {weight * 0.8})")
                            break  # Only count first match per tag
        
        # Lower threshold for more inclusive filtering since we're working with limited tags
        is_relevant = relevance_score > 0.3 and matched_interests > 0
        
        if debug:
            print(f"   Final score: {relevance_score:.2f}, matches: {matched_interests}, relevant: {is_relevant}")
        
        return is_relevant
    
    def get_available_dates(self) -> List[str]:
        """Get all dates that have scraped data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT date FROM stories ORDER BY date DESC")
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_dates_for_user(self, user_id: str) -> List[str]:
        """Get all dates that have scraped data and are accessible to the user (from signup date onwards)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT s.date 
                FROM stories s
                WHERE s.date >= (SELECT date(created_at) FROM users WHERE user_id = ?)
                ORDER BY s.date DESC
            """, (user_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def get_stats_by_date(self, target_date: str) -> Dict:
        """Get statistics for a specific date, matching what's displayed on the dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get basic story stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_scraped,
                    SUM(CASE WHEN COALESCE(was_cached, 0) = 0 THEN 1 ELSE 0 END) as total_stories,
                    AVG(points) as avg_points,
                    SUM(comments_count) as total_comments,
                    SUM(CASE WHEN COALESCE(was_cached, 0) = 1 THEN 1 ELSE 0 END) as cached_stories
                FROM stories 
                WHERE date = ?
            """, (target_date,))
            
            row = cursor.fetchone()
            
            # For multi-user system, calculate relevant stories across all users
            # Count unique stories that are relevant to at least one user
            cursor.execute("""
                SELECT COUNT(DISTINCT usr.story_id) as relevant_stories
                FROM user_story_relevance usr
                JOIN stories s ON usr.story_id = s.id
                WHERE s.date = ? AND usr.is_relevant = 1
            """, (target_date,))
            
            relevant_count = cursor.fetchone()[0] or 0
            
            # If no user-specific relevance data, fall back to legacy is_relevant column
            if relevant_count == 0:
                cursor.execute("""
                    SELECT SUM(CASE WHEN is_relevant THEN 1 ELSE 0 END) as relevant_stories
                    FROM stories 
                    WHERE date = ?
                """, (target_date,))
                relevant_count = cursor.fetchone()[0] or 0
            
            return {
                'total_stories': row[1] or 0,  # Non-cached stories only
                'total_scraped': row[0] or 0,  # All scraped stories
                'relevant_stories': relevant_count,
                'avg_points': round(row[2] or 0, 1),
                'total_comments': row[3] or 0,
                'cached_stories': row[4] or 0
            }
    
    def get_user_stats_by_date(self, user_id: str, target_date: str) -> Dict:
        """Get user-specific statistics for a date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get basic story stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_scraped,
                    SUM(CASE WHEN COALESCE(was_cached, 0) = 0 THEN 1 ELSE 0 END) as total_stories,
                    AVG(points) as avg_points,
                    SUM(comments_count) as total_comments,
                    SUM(CASE WHEN COALESCE(was_cached, 0) = 1 THEN 1 ELSE 0 END) as cached_stories
                FROM stories 
                WHERE date = ?
            """, (target_date,))
            
            row = cursor.fetchone()
            
            # Get user-specific relevant stories count
            cursor.execute("""
                SELECT COUNT(*) as relevant_stories
                FROM user_story_relevance usr
                JOIN stories s ON usr.story_id = s.id
                WHERE s.date = ? AND usr.user_id = ? AND usr.is_relevant = 1
            """, (target_date, user_id))
            
            relevant_count = cursor.fetchone()[0] or 0
            
            return {
                'total_stories': row[1] or 0,  # Non-cached stories only
                'total_scraped': row[0] or 0,  # All scraped stories
                'relevant_stories': relevant_count,
                'avg_points': round(row[2] or 0, 1),
                'total_comments': row[3] or 0,
                'cached_stories': row[4] or 0
            }
    
    def create_user(self, email: str, name: Optional[str] = None) -> str:
        """Create a new user and return their UUID"""
        user_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, email, name, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, email, name, datetime.now().isoformat()))
            conn.commit()
        return user_id
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by UUID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, email, name, created_at, last_active_at
                FROM users WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return User(
                    id=row[0], user_id=row[1], email=row[2], 
                    name=row[3], created_at=row[4], last_active_at=row[5]
                )
            return None
    
    def update_user_activity(self, user_id: str):
        """Update user's last active timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_active_at = ? WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            conn.commit()
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, email, name, created_at, last_active_at
                FROM users ORDER BY created_at DESC
            """)
            
            return [
                User(id=row[0], user_id=row[1], email=row[2], 
                     name=row[3], created_at=row[4], last_active_at=row[5])
                for row in cursor.fetchall()
            ]

    def log_interaction(self, user_id: str, story_id: int, interaction_type: str, duration_seconds: Optional[int] = None):
        """Log a user interaction with a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # For rating interactions (thumbs_up/thumbs_down), remove the opposite rating first
            if interaction_type in ['thumbs_up', 'thumbs_down']:
                opposite_type = 'thumbs_down' if interaction_type == 'thumbs_up' else 'thumbs_up'
                cursor.execute("""
                    DELETE FROM user_interactions 
                    WHERE user_id = ? AND story_id = ? AND interaction_type = ?
                """, (user_id, story_id, opposite_type))
                
                # Also remove existing rating of the same type to allow toggling
                cursor.execute("""
                    DELETE FROM user_interactions 
                    WHERE user_id = ? AND story_id = ? AND interaction_type = ?
                """, (user_id, story_id, interaction_type))
            
            cursor.execute("""
                INSERT INTO user_interactions 
                (user_id, story_id, interaction_type, timestamp, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, story_id, interaction_type, datetime.now().isoformat(), duration_seconds))
            conn.commit()
    
    def get_story_interactions(self, user_id: str, story_id: int) -> List[Dict]:
        """Get all interactions for a specific story by a specific user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT interaction_type, timestamp, duration_seconds
                FROM user_interactions 
                WHERE user_id = ? AND story_id = ?
                ORDER BY timestamp DESC
            """, (user_id, story_id))
            
            return [
                {
                    'interaction_type': row[0],
                    'timestamp': row[1],
                    'duration_seconds': row[2]
                }
                for row in cursor.fetchall()
            ]
    
    def remove_interaction(self, user_id: str, story_id: int, interaction_type: str):
        """Remove a specific interaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_interactions 
                WHERE user_id = ? AND story_id = ? AND interaction_type = ?
            """, (user_id, story_id, interaction_type))
            conn.commit()
    
    def get_saved_stories(self, user_id: str) -> List[Dict]:
        """Get all saved stories for a specific user, ordered by save date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT s.id, s.date, s.rank, s.title, s.url, s.points, 
                       s.author, s.comments_count, s.hn_discussion_url, 
                       s.article_summary, s.comments_analysis, s.is_relevant, 
                       s.relevance_score, s.scraped_at, ui.timestamp as saved_at,
                       COALESCE(s.was_cached, 0) as was_cached, s.tags, sn.notes
                FROM stories s
                JOIN user_interactions ui ON s.id = ui.story_id
                LEFT JOIN story_notes sn ON s.id = sn.story_id AND sn.user_id = ui.user_id
                WHERE ui.user_id = ? AND ui.interaction_type = 'save'
                ORDER BY ui.timestamp DESC
            """, (user_id,))
            
            saved_stories = []
            for row in cursor.fetchall():
                comments_analysis = None
                if row[10]:  # comments_analysis column
                    try:
                        comments_analysis = json.loads(row[10])
                    except json.JSONDecodeError:
                        pass
                
                tags = None
                if row[16]:  # tags column
                    try:
                        tags = json.loads(row[16])
                    except json.JSONDecodeError:
                        pass
                
                saved_stories.append({
                    'id': row[0],
                    'date': row[1],
                    'rank': row[2],
                    'title': row[3],
                    'url': row[4],
                    'points': row[5],
                    'author': row[6],
                    'comments_count': row[7],
                    'hn_discussion_url': row[8],
                    'article_summary': row[9],
                    'comments_analysis': comments_analysis,
                    'is_relevant': bool(row[11]),
                    'relevance_score': row[12],
                    'scraped_at': row[13],
                    'saved_at': row[14],
                    'was_cached': bool(row[15]),
                    'tags': tags,
                    'notes': row[17]  # notes from story_notes table
                })
            
            return saved_stories
    
    def save_story_notes(self, user_id: str, story_id: int, notes: str):
        """Save or update personal notes for a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO story_notes 
                (user_id, story_id, notes, created_at, updated_at)
                VALUES (?, ?, ?, 
                    COALESCE((SELECT created_at FROM story_notes WHERE user_id = ? AND story_id = ?), ?),
                    ?)
            """, (user_id, story_id, notes, user_id, story_id, now, now))
            conn.commit()
    
    def get_story_notes(self, user_id: str, story_id: int) -> Optional[str]:
        """Get personal notes for a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT notes FROM story_notes WHERE user_id = ? AND story_id = ?
            """, (user_id, story_id))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_user_interaction_stats(self, user_id: str, days: int = 30) -> Dict:
        """Get user interaction statistics for the last N days"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    interaction_type,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration
                FROM user_interactions 
                WHERE user_id = ? AND timestamp > datetime('now', '-{} days')
                GROUP BY interaction_type
            """.format(days), (user_id,))
            
            results = cursor.fetchall()
            stats = {}
            for row in results:
                stats[row[0]] = {
                    'count': row[1],
                    'avg_duration': round(row[2] or 0, 1)
                }
            return stats
    
    def update_user_interest_weight(self, user_id: str, keyword: str, weight: float, category: str):
        """Update or insert a user-specific interest weight"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_interest_weights 
                (user_id, keyword, weight, category, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, keyword, weight, category, datetime.now().isoformat()))
            conn.commit()
    
    def get_user_interest_weights(self, user_id: str) -> List[UserInterestWeight]:
        """Get all interest weights for a specific user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, keyword, weight, category, updated_at
                FROM user_interest_weights 
                WHERE user_id = ?
                ORDER BY weight DESC, keyword
            """, (user_id,))
            
            return [
                UserInterestWeight(
                    id=row[0], user_id=row[1], keyword=row[2], weight=row[3], 
                    category=row[4], updated_at=row[5]
                )
                for row in cursor.fetchall()
            ]
    
    def delete_user_interest_weight(self, user_id: str, interest_id: int):
        """Delete a user-specific interest weight by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_interest_weights WHERE user_id = ? AND id = ?
            """, (user_id, interest_id))
            conn.commit()
            return cursor.rowcount > 0  # Returns True if a row was deleted
    
    def copy_default_interests_to_user(self, user_id: str):
        """Copy default interest weights to a new user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_interest_weights (user_id, keyword, weight, category, updated_at)
                SELECT ?, keyword, weight, category, ?
                FROM interest_weights
            """, (user_id, datetime.now().isoformat()))
            conn.commit()

    # Keep original methods for backward compatibility and default templates
    def update_interest_weight(self, keyword: str, weight: float, category: str):
        """Update or insert a global interest weight (for default templates)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO interest_weights 
                (keyword, weight, category, updated_at)
                VALUES (?, ?, ?, ?)
            """, (keyword, weight, category, datetime.now().isoformat()))
            conn.commit()
    
    def get_interest_weights(self) -> List[InterestWeight]:
        """Get all global interest weights"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, keyword, weight, category, updated_at
                FROM interest_weights 
                ORDER BY weight DESC, keyword
            """)
            
            return [
                InterestWeight(
                    id=row[0], keyword=row[1], weight=row[2], 
                    category=row[3], updated_at=row[4]
                )
                for row in cursor.fetchall()
            ]
    
    def delete_interest_weight(self, interest_id: int):
        """Delete a global interest weight by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM interest_weights WHERE id = ?
            """, (interest_id,))
            conn.commit()
            return cursor.rowcount > 0  # Returns True if a row was deleted
    
    def _migrate_to_multi_user(self, cursor):
        """Migrate existing single-user database to multi-user schema"""
        try:
            # Check if we have existing user_interactions without user_id
            cursor.execute("PRAGMA table_info(user_interactions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'user_id' not in columns and 'story_id' in columns:
                print("🔄 Migrating user_interactions table to multi-user schema...")
                # Backup existing interactions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_interactions_backup AS 
                    SELECT * FROM user_interactions
                """)
                
                # Drop old table
                cursor.execute("DROP TABLE user_interactions")
                print("✅ user_interactions table migration complete")
            
            # Check story_notes table
            try:
                cursor.execute("PRAGMA table_info(story_notes)")
                story_notes_columns = [row[1] for row in cursor.fetchall()]
                
                if 'user_id' not in story_notes_columns and 'story_id' in story_notes_columns:
                    print("🔄 Migrating story_notes table...")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS story_notes_backup AS 
                        SELECT * FROM story_notes
                    """)
                    cursor.execute("DROP TABLE story_notes")
                    print("✅ story_notes table migration complete")
            except:
                # story_notes table might not exist yet
                pass
                
        except Exception as e:
            print(f"⚠️ Migration warning: {e}")

    def batch_process_user_relevance(self, user_id: str, limit_days: int = 30) -> Dict[str, int]:
        """
        Process relevance for all existing stories for a new user.
        Returns statistics about processing.
        """
        import sys
        import os
        # Add parent directory to path to import ai_pipeline
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ai_pipeline import CostOptimisedAI
        
        stats = {
            'total_stories': 0,
            'relevant_stories': 0,
            'processed_stories': 0,
            'cached_stories': 0
        }
        
        # Get user interests
        user_interests = self.get_user_interests_by_category(user_id)
        if not any(user_interests.values()):
            return stats  # No interests to process
        
        # Initialize AI pipeline
        ai_pipeline = CostOptimisedAI()
        
        # Get all recent stories (limit to last N days for performance)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, url, article_summary, comments_analysis, tags
                FROM stories
                WHERE date >= date('now', '-' || ? || ' days')
                ORDER BY date DESC, rank ASC
            """, (limit_days,))
            
            stories = cursor.fetchall()
            stats['total_stories'] = len(stories)
            
            # Process each story
            for story_row in stories:
                story_id, title, url, article_summary, comments_analysis_json, tags_json = story_row
                
                # Check if relevance already calculated
                existing_relevance = self.get_user_story_relevance(user_id, story_id)
                if existing_relevance:
                    stats['cached_stories'] += 1
                    if existing_relevance.is_relevant:
                        stats['relevant_stories'] += 1
                    continue
                
                # Prepare story data for relevance check
                story_data = {
                    'title': title,
                    'url': url,
                    'article_summary': article_summary
                }
                
                # Convert user interests to expected format
                formatted_interests = {
                    'high_priority': user_interests.get('high', []),
                    'medium_priority': user_interests.get('medium', []),
                    'low_priority': user_interests.get('low', [])
                }
                
                # Calculate relevance using AI pipeline
                is_relevant, relevance_score, relevance_reasoning = ai_pipeline.is_relevant_story_local(
                    story_data, formatted_interests
                )
                
                # Store relevance data
                self.store_user_story_relevance(
                    user_id=user_id,
                    story_db_id=story_id,
                    is_relevant=is_relevant,
                    relevance_score=relevance_score,
                    relevance_reasoning=relevance_reasoning
                )
                
                stats['processed_stories'] += 1
                if is_relevant:
                    stats['relevant_stories'] += 1
        
        return stats
    
    def batch_process_user_relevance_from_date(self, user_id: str, start_date: str) -> Dict[str, int]:
        """
        Process relevance for stories from a specific date onwards for a new user.
        This is optimized for new user onboarding to only process from their signup date.
        """
        import sys
        import os
        # Add parent directory to path to import ai_pipeline
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ai_pipeline import CostOptimisedAI
        
        stats = {
            'total_stories': 0,
            'relevant_stories': 0,
            'processed_stories': 0,
            'cached_stories': 0
        }
        
        # Get user interests
        user_interests = self.get_user_interests_by_category(user_id)
        print(f"🔍 Retrieved interests for user {user_id}: {user_interests}")
        if not any(user_interests.values()):
            print(f"❌ No interests found for user {user_id}")
            return stats  # No interests to process
        print(f"✅ Found interests: {sum(len(v) for v in user_interests.values())} total")
        
        # Initialize AI pipeline
        ai_pipeline = CostOptimisedAI()
        
        # Get stories from the start date onwards
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, url, article_summary, comments_analysis, tags
                FROM stories
                WHERE date >= ?
                ORDER BY date DESC, rank ASC
            """, (start_date,))
            
            stories = cursor.fetchall()
            stats['total_stories'] = len(stories)
            
            # Process each story
            for story_row in stories:
                story_id, title, url, article_summary, comments_analysis_json, tags_json = story_row
                
                # Check if relevance already calculated
                existing_relevance = self.get_user_story_relevance(user_id, story_id)
                if existing_relevance:
                    stats['cached_stories'] += 1
                    if existing_relevance.is_relevant:
                        stats['relevant_stories'] += 1
                    continue
                
                # Prepare story data for relevance check
                story_data = {
                    'title': title,
                    'url': url,
                    'article_summary': article_summary
                }
                
                # Convert user interests to expected format
                formatted_interests = {
                    'high_priority': user_interests.get('high', []),
                    'medium_priority': user_interests.get('medium', []),
                    'low_priority': user_interests.get('low', [])
                }
                
                # Calculate relevance using AI pipeline
                is_relevant, relevance_score, relevance_reasoning = ai_pipeline.is_relevant_story_local(
                    story_data, formatted_interests
                )
                
                # Store relevance data
                self.store_user_story_relevance(
                    user_id=user_id,
                    story_db_id=story_id,
                    is_relevant=is_relevant,
                    relevance_score=relevance_score,
                    relevance_reasoning=relevance_reasoning
                )
                
                stats['processed_stories'] += 1
                if is_relevant:
                    stats['relevant_stories'] += 1
        
        return stats
    
    def get_recent_stories_without_relevance(self, user_id: str, limit: int = 10) -> List[Story]:
        """
        Get recent stories that don't have relevance calculated for this user.
        Used for on-demand processing.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.date, s.rank, s.story_id, s.title, s.url, s.points, 
                       s.author, s.comments_count, s.hn_discussion_url, s.article_summary,
                       s.comments_analysis, s.scraped_at, COALESCE(s.was_cached, 0), s.tags
                FROM stories s
                LEFT JOIN user_story_relevance r ON s.id = r.story_id AND r.user_id = ?
                WHERE r.id IS NULL
                ORDER BY s.date DESC, s.rank ASC
                LIMIT ?
            """, (user_id, limit))
            
            stories = []
            for row in cursor.fetchall():
                comments_analysis = None
                if row[11]:
                    try:
                        comments_analysis = json.loads(row[11])
                    except json.JSONDecodeError:
                        pass
                
                tags = None
                if row[14]:
                    try:
                        tags = json.loads(row[14])
                    except json.JSONDecodeError:
                        pass
                
                stories.append(Story(
                    id=row[0], date=row[1], rank=row[2], story_id=row[3],
                    title=row[4], url=row[5], points=row[6], author=row[7],
                    comments_count=row[8], hn_discussion_url=row[9],
                    article_summary=row[10], comments_analysis=comments_analysis,
                    scraped_at=row[12], was_cached=bool(row[13]), tags=tags
                ))
            
            return stories

    def get_user_interests_by_category(self, user_id: str) -> Dict[str, List[str]]:
        """Get user interests organized by category"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT keyword, category
                FROM user_interest_weights
                WHERE user_id = ?
                ORDER BY weight DESC, keyword
            """, (user_id,))
            
            # Initialize with both legacy and new category formats
            interests = {
                'high': [],
                'medium': [], 
                'low': [],
                'technology': [],
                'business': [],
                'science': [],
                'general': []
            }
            
            for keyword, category in cursor.fetchall():
                # Handle both legacy priority format and new category format
                if category in interests:
                    interests[category].append(keyword)
                    
                    # For new categories, also add to legacy format for backward compatibility
                    # All new interests use weight 1.0, so map them to 'high' priority
                    if category in ['technology', 'business', 'science', 'general']:
                        if keyword not in interests['high']:  # Avoid duplicates
                            interests['high'].append(keyword)
            
            return interests

    def close(self):
        """Close database connection (SQLite auto-closes, but good practice)"""
        pass

def init_interest_weights(db: DatabaseManager):
    """Initialize default interest weights from scraper configuration"""
    # Default interests from scraper.py
    default_interests = {
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
    
    weight_mapping = {
        "high_priority": 1.0,
        "medium_priority": 0.6,
        "low_priority": 0.3
    }
    
    for category, keywords in default_interests.items():
        weight = weight_mapping[category]
        for keyword in keywords:
            db.update_interest_weight(keyword, weight, category.replace("_priority", ""))

if __name__ == "__main__":
    # Test the database setup
    db = DatabaseManager()
    print("✅ Database initialized successfully")
    
    # Initialize default interests
    init_interest_weights(db)
    print("✅ Default interest weights initialized")
    
    # Test importing existing JSON data if available
    import glob
    json_files = glob.glob("hn_scrape_*.json")
    for json_file in json_files[:1]:  # Import just the first one for testing
        db.import_json_data(json_file)
    
    # Show available dates
    dates = db.get_available_dates()
    print(f"📅 Available dates: {dates}")
    
    if dates:
        stats = db.get_stats_by_date(dates[0])
        print(f"📊 Stats for {dates[0]}: {stats}")
