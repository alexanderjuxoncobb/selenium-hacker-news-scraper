#!/usr/bin/env python3
"""
Database models and operations for HN Scraper Dashboard
"""

import sqlite3
import json
from datetime import datetime, date
from typing import List, Dict, Optional
from dataclasses import dataclass
import os

@dataclass
class Story:
    id: Optional[int]
    date: str
    rank: int
    title: str
    url: str
    points: int
    author: str
    comments_count: int
    hn_discussion_url: str
    article_summary: Optional[str]
    is_relevant: bool
    relevance_score: float
    scraped_at: str
    comments_analysis: Optional[Dict] = None

@dataclass
class UserInteraction:
    id: Optional[int]
    story_id: int
    interaction_type: str  # 'click', 'read', 'save', 'share', 'thumbs_up', 'thumbs_down'
    timestamp: str
    duration_seconds: Optional[int] = None

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
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Stories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    points INTEGER DEFAULT 0,
                    author TEXT,
                    comments_count INTEGER DEFAULT 0,
                    hn_discussion_url TEXT,
                    article_summary TEXT,
                    comments_analysis TEXT,  -- JSON string
                    is_relevant BOOLEAN DEFAULT FALSE,
                    relevance_score REAL DEFAULT 0.0,
                    scraped_at TEXT NOT NULL,
                    UNIQUE(date, rank)
                )
            """)
            
            # User interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER NOT NULL,
                    interaction_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_seconds INTEGER,
                    FOREIGN KEY (story_id) REFERENCES stories (id)
                )
            """)
            
            # Interest weights table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interest_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    weight REAL NOT NULL,
                    category TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Story notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS story_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (story_id) REFERENCES stories (id),
                    UNIQUE(story_id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_date ON stories (date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_relevant ON stories (is_relevant)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_story ON user_interactions (story_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions (interaction_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_story ON story_notes (story_id)")
            
            conn.commit()
    
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
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO stories 
                        (date, rank, title, url, points, author, comments_count, 
                         hn_discussion_url, article_summary, comments_analysis, 
                         is_relevant, relevance_score, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        scrape_date,
                        story.get('rank', 0),
                        story.get('title', ''),
                        story.get('url', ''),
                        story.get('points', 0),
                        story.get('author', ''),
                        story.get('comments_count', 0),
                        story.get('hn_discussion_url', ''),
                        story.get('article_summary'),
                        comments_analysis_json,
                        story.get('is_relevant', False),
                        1.0 if story.get('is_relevant', False) else 0.0,  # Simple relevance score
                        story.get('scraped_at', data.get('scrape_date', ''))
                    ))
                
                conn.commit()
                print(f"✅ Imported {len(stories)} stories from {json_file_path}")
                
        except Exception as e:
            print(f"❌ Error importing JSON data: {str(e)}")
    
    def get_stories_by_date(self, target_date: str) -> List[Story]:
        """Get all stories for a specific date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, date, rank, title, url, points, author, comments_count,
                       hn_discussion_url, article_summary, comments_analysis,
                       is_relevant, relevance_score, scraped_at
                FROM stories 
                WHERE date = ? 
                ORDER BY rank
            """, (target_date,))
            
            rows = cursor.fetchall()
            stories = []
            
            for row in rows:
                comments_analysis = None
                if row[10]:  # comments_analysis column
                    try:
                        comments_analysis = json.loads(row[10])
                    except json.JSONDecodeError:
                        pass
                
                story = Story(
                    id=row[0], date=row[1], rank=row[2], title=row[3], url=row[4],
                    points=row[5], author=row[6], comments_count=row[7],
                    hn_discussion_url=row[8], article_summary=row[9],
                    is_relevant=bool(row[11]), relevance_score=row[12],
                    scraped_at=row[13], comments_analysis=comments_analysis
                )
                stories.append(story)
            
            return stories
    
    def get_relevant_stories_by_date(self, target_date: str) -> List[Story]:
        """Get only relevant stories for a specific date"""
        stories = self.get_stories_by_date(target_date)
        return [story for story in stories if story.is_relevant]
    
    def get_available_dates(self) -> List[str]:
        """Get all dates that have scraped data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT date FROM stories ORDER BY date DESC")
            return [row[0] for row in cursor.fetchall()]
    
    def get_stats_by_date(self, target_date: str) -> Dict:
        """Get statistics for a specific date, matching what's displayed on the dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_stories,
                    SUM(CASE WHEN is_relevant THEN 1 ELSE 0 END) as relevant_stories,
                    AVG(points) as avg_points,
                    SUM(comments_count) as total_comments
                FROM stories 
                WHERE date = ?
            """, (target_date,))
            
            row = cursor.fetchone()
            return {
                'total_stories': row[0] or 0,
                'relevant_stories': row[1] or 0,
                'avg_points': round(row[2] or 0, 1),
                'total_comments': row[3] or 0
            }
    
    def log_interaction(self, story_id: int, interaction_type: str, duration_seconds: Optional[int] = None):
        """Log a user interaction with a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # For rating interactions (thumbs_up/thumbs_down), remove the opposite rating first
            if interaction_type in ['thumbs_up', 'thumbs_down']:
                opposite_type = 'thumbs_down' if interaction_type == 'thumbs_up' else 'thumbs_up'
                cursor.execute("""
                    DELETE FROM user_interactions 
                    WHERE story_id = ? AND interaction_type = ?
                """, (story_id, opposite_type))
                
                # Also remove existing rating of the same type to allow toggling
                cursor.execute("""
                    DELETE FROM user_interactions 
                    WHERE story_id = ? AND interaction_type = ?
                """, (story_id, interaction_type))
            
            cursor.execute("""
                INSERT INTO user_interactions 
                (story_id, interaction_type, timestamp, duration_seconds)
                VALUES (?, ?, ?, ?)
            """, (story_id, interaction_type, datetime.now().isoformat(), duration_seconds))
            conn.commit()
    
    def get_story_interactions(self, story_id: int) -> List[Dict]:
        """Get all interactions for a specific story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT interaction_type, timestamp, duration_seconds
                FROM user_interactions 
                WHERE story_id = ?
                ORDER BY timestamp DESC
            """, (story_id,))
            
            return [
                {
                    'interaction_type': row[0],
                    'timestamp': row[1],
                    'duration_seconds': row[2]
                }
                for row in cursor.fetchall()
            ]
    
    def remove_interaction(self, story_id: int, interaction_type: str):
        """Remove a specific interaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_interactions 
                WHERE story_id = ? AND interaction_type = ?
            """, (story_id, interaction_type))
            conn.commit()
    
    def get_saved_stories(self) -> List[Dict]:
        """Get all saved stories with their details, ordered by save date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT s.id, s.date, s.rank, s.title, s.url, s.points, 
                       s.author, s.comments_count, s.hn_discussion_url, 
                       s.article_summary, s.comments_analysis, s.is_relevant, 
                       s.relevance_score, s.scraped_at, ui.timestamp as saved_at
                FROM stories s
                JOIN user_interactions ui ON s.id = ui.story_id
                WHERE ui.interaction_type = 'save'
                ORDER BY ui.timestamp DESC
            """)
            
            saved_stories = []
            for row in cursor.fetchall():
                comments_analysis = None
                if row[10]:  # comments_analysis column
                    try:
                        comments_analysis = json.loads(row[10])
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
                    'saved_at': row[14]
                })
            
            return saved_stories
    
    def save_story_notes(self, story_id: int, notes: str):
        """Save or update personal notes for a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO story_notes 
                (story_id, notes, created_at, updated_at)
                VALUES (?, ?, 
                    COALESCE((SELECT created_at FROM story_notes WHERE story_id = ?), ?),
                    ?)
            """, (story_id, notes, story_id, now, now))
            conn.commit()
    
    def get_story_notes(self, story_id: int) -> Optional[str]:
        """Get personal notes for a story"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT notes FROM story_notes WHERE story_id = ?
            """, (story_id,))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_user_interaction_stats(self, days: int = 30) -> Dict:
        """Get user interaction statistics for the last N days"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    interaction_type,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration
                FROM user_interactions 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY interaction_type
            """.format(days))
            
            results = cursor.fetchall()
            stats = {}
            for row in results:
                stats[row[0]] = {
                    'count': row[1],
                    'avg_duration': round(row[2] or 0, 1)
                }
            return stats
    
    def update_interest_weight(self, keyword: str, weight: float, category: str):
        """Update or insert an interest weight"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO interest_weights 
                (keyword, weight, category, updated_at)
                VALUES (?, ?, ?, ?)
            """, (keyword, weight, category, datetime.now().isoformat()))
            conn.commit()
    
    def get_interest_weights(self) -> List[InterestWeight]:
        """Get all interest weights"""
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
        """Delete an interest weight by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM interest_weights WHERE id = ?
            """, (interest_id,))
            conn.commit()
            return cursor.rowcount > 0  # Returns True if a row was deleted
    
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