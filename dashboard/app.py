#!/usr/bin/env python3
"""
FastAPI Web Dashboard for HN Scraper
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, date, timedelta
import json
from typing import Optional
import os
import uvicorn
import secrets

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add parent directory
from database import DatabaseManager, init_interest_weights

# Import scheduler for Railway deployment
try:
    from railway_scheduler import start_background_scheduler
    # Start the scheduler when running on Railway
    if os.getenv('RAILWAY_ENVIRONMENT'):
        start_background_scheduler()
except ImportError:
    pass  # Scheduler not available in development

app = FastAPI(title="HN Scraper Dashboard", description="AI-Powered Hacker News Daily Digest")

# Mount static files (with error handling for Railway deployment)
import os
static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"Warning: Static directory '{static_dir}' not found. Static files will not be served.")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Initialize database
# This will use DATABASE_URL from environment if set, otherwise defaults to SQLite
db = DatabaseManager()

# Admin authentication
security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "hn_admin_2025")  # Change this in production!

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials"""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.on_event("startup")
async def startup_event():
    """Initialize database and import existing data on startup"""
    # Initialize default interests if not already done
    interest_weights = db.get_interest_weights()
    if not interest_weights:
        init_interest_weights(db)
        print("✅ Initialized default interest weights")
    
    # Auto-import disabled for testing
    # TODO: Re-enable when needed for production
    # import glob
    # json_files = glob.glob("../hn_scrape_*.json") + glob.glob("../enhanced_hn_scrape_*.json")
    # for json_file in json_files:
    #     try:
    #         file_date = json_file.split('_')[2][:8]
    #         formatted_date = f"{file_date[:4]}-{file_date[4:6]}-{file_date[6:8]}"
    #         existing_stories = db.get_stories_by_date(formatted_date)
    #         if not existing_stories:
    #             db.import_json_data(json_file)
    #     except Exception as e:
    #         print(f"⚠️  Error importing {json_file}: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - show setup instructions or redirect existing user"""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/setup", response_class=HTMLResponse)
async def setup_form(request: Request):
    """User setup form"""
    # Organized core topics
    topic_sections = {
        "Technology & Programming": [
            "artificial intelligence", "machine learning", "software development", 
            "programming", "hardware", "robotics"
        ],
        "Business & Finance": [
            "startups", "business", "finance", "cryptocurrency"
        ],
        "Science & Health": [
            "science", "health", "medicine", "climate"
        ],
        "General Interest": [
            "politics", "education", "books", "music"
        ]
    }
    
    return templates.TemplateResponse("setup.html", {
        "request": request,
        "topic_sections": topic_sections
    })

@app.post("/setup", response_class=HTMLResponse)
async def setup_submit(request: Request):
    """Process user setup form"""
    try:
        # Get form data
        form_data = await request.form()
        email = form_data.get("email")
        name = form_data.get("name")
        custom_interests = form_data.get("custom_interests")
        
        if not email:
            raise ValueError("Email is required")
        
        # Create user
        user_id = db.create_user(email, name)
        
        # Don't copy defaults - users only get interests they explicitly select
        
        # Topic category mapping for organization
        topic_to_category = {
            # Technology & Programming
            "artificial intelligence": "technology", "machine learning": "technology", 
            "software development": "technology", "programming": "technology", 
            "hardware": "technology", "robotics": "technology",
            
            # Business & Finance  
            "startups": "business", "business": "business", 
            "finance": "business", "cryptocurrency": "business",
            
            # Science & Health
            "science": "science", "health": "science", 
            "medicine": "science", "climate": "science",
            
            # General Interest
            "politics": "general", "education": "general", 
            "books": "general", "music": "general"
        }
        
        # All available topics from sections
        topic_sections = {
            "Technology & Programming": [
                "artificial intelligence", "machine learning", "software development", 
                "programming", "hardware", "robotics"
            ],
            "Business & Finance": [
                "startups", "business", "finance", "cryptocurrency"
            ],
            "Science & Health": [
                "science", "health", "medicine", "climate"
            ],
            "General Interest": [
                "politics", "education", "books", "music"
            ]
        }
        
        all_topics = []
        for topics in topic_sections.values():
            all_topics.extend(topics)
        
        # Acronym mapping for content matching
        acronym_mapping = {
            "artificial intelligence": ["AI"],
            "machine learning": ["ML"],
            "startups": ["tech startups"]
        }
        
        interests_added = 0
        # Process checkbox selections (simple interested/not interested)
        for topic in all_topics:
            is_interested = form_data.get(f"topic_{topic}")
            print(f"🔍 Topic: {topic}, Selected: {bool(is_interested)}")
            if is_interested:  # Checkbox was checked
                category = topic_to_category.get(topic, "general")
                # Always use weight 1.0 for all interests
                db.update_user_interest_weight(user_id, topic, 1.0, category)
                interests_added += 1
                print(f"✅ Added interest: {topic} (category: {category})")
                
                # Add acronyms/related terms for better content matching
                if topic in acronym_mapping:
                    for related_term in acronym_mapping[topic]:
                        db.update_user_interest_weight(user_id, related_term, 1.0, category)
                        interests_added += 1
                        print(f"✅ Added related term: {related_term} (category: {category})")
        
        print(f"📊 Total interests added: {interests_added}")
        
        # Add custom interests (no priority format, just keywords)
        for key, value in form_data.items():
            if key.startswith("custom_interest_"):
                keyword = value.strip()
                if keyword:
                    # Assign custom interests to general category by default
                    db.update_user_interest_weight(user_id, keyword, 1.0, "general")
                    print(f"✅ Added custom interest: {keyword} (category: general)")
        
        # Process only today's stories for the new user (signup date)
        print(f"🔄 Processing today's stories for new user {user_id}...")
        processing_stats = db.batch_process_user_relevance_from_date(user_id, date.today().isoformat())
        print(f"✅ Processed {processing_stats['processed_stories']} stories, found {processing_stats['relevant_stories']} relevant")
        print(f"📊 Processing stats: {processing_stats}")
        
        # Get user and interest count for success page
        user = db.get_user(user_id)
        user_interests = db.get_user_interest_weights(user_id)
        
        return templates.TemplateResponse("setup_success.html", {
            "request": request,
            "user": user,
            "interest_count": len(user_interests),
            "processing_stats": processing_stats
        })
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        error = "Something went wrong during setup. Please try again."
        
        # Return form with error
        topic_sections = {
            "Technology & Programming": [
                "artificial intelligence", "machine learning", "software development", 
                "programming", "hardware", "robotics"
            ],
            "Business & Finance": [
                "startups", "business", "finance", "cryptocurrency"
            ],
            "Science & Health": [
                "science", "health", "medicine", "climate"
            ],
            "General Interest": [
                "politics", "education", "books", "music"
            ]
        }
        
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "topic_sections": topic_sections,
            "error": error
        })

@app.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def user_dashboard(request: Request, user_id: str):
    """User dashboard - redirect to today's digest or latest available"""
    # Verify user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user activity
    db.update_user_activity(user_id)
    
    available_dates = db.get_available_dates_for_user(user_id)
    if not available_dates:
        # No data available for this user yet (maybe they just signed up)
        # Redirect to today's date anyway, which will show no data message
        return RedirectResponse(url=f"/dashboard/{user_id}/{date.today().isoformat()}")
    
    # Try to find today's data, otherwise use latest available for user
    today = date.today().isoformat()
    target_date = today if today in available_dates else available_dates[0]
    
    return RedirectResponse(url=f"/dashboard/{user_id}/{target_date}")

@app.get("/dashboard/{user_id}/{target_date}", response_class=HTMLResponse)
async def user_dashboard_date(request: Request, user_id: str, target_date: str):
    """User-specific dashboard page for a specific date"""
    # Verify user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Validate date format
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Update user activity
    db.update_user_activity(user_id)
    
    # Get stories with user-specific relevance data
    stories_with_relevance = db.get_stories_with_user_relevance(user_id, target_date)
    
    # Check if we need to process relevance on-demand
    needs_processing = False
    for story, relevance in stories_with_relevance:
        if not relevance:
            needs_processing = True
            break
    
    # If no relevance data exists and user has interests, process on-demand
    if needs_processing:
        user_interests = db.get_user_interests_by_category(user_id)
        if any(user_interests.values()):
            print(f"📊 Processing relevance on-demand for user {user_id} on {target_date}")
            # Process just this date's stories
            target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
            days_ago = (datetime.now() - target_datetime).days
            if days_ago <= 30:  # Only process if within last 30 days
                print(f"⚠️  Re-processing relevance for {target_date} (days_ago: {days_ago})")
                db.batch_process_user_relevance(user_id, limit_days=days_ago + 1)
                # Re-fetch stories with newly calculated relevance
                stories_with_relevance = db.get_stories_with_user_relevance(user_id, target_date)
    
    # Separate stories and extract relevant ones
    all_stories = []
    relevant_stories = []
    
    for story, relevance in stories_with_relevance:
        # Add relevance data to story for template access
        if relevance:
            story.is_relevant = relevance.is_relevant
            story.relevance_score = float(relevance.relevance_score) if relevance.relevance_score is not None else 0.0
            story.relevance_reasoning = relevance.relevance_reasoning
            if relevance.is_relevant:
                relevant_stories.append(story)
                print(f"✅ Story {story.id} marked as RELEVANT (score: {story.relevance_score})")
            else:
                print(f"❌ Story {story.id} marked as NOT RELEVANT (score: {story.relevance_score})")
        else:
            # No relevance data for this user yet
            story.is_relevant = False
            story.relevance_score = 0.0
            story.relevance_reasoning = None
            print(f"⚠️  Story {story.id} has NO relevance data")
        
        all_stories.append(story)
    
    user_interests = db.get_user_interest_weights(user_id)
    
    stats = db.get_user_stats_by_date(user_id, target_date)
    available_dates = db.get_available_dates_for_user(user_id)
    
    if not all_stories:
        return templates.TemplateResponse("no_data.html", {
            "request": request,
            "target_date": target_date,
            "available_dates": available_dates,
            "user": user
        })
    
    # Get navigation dates
    current_index = available_dates.index(target_date) if target_date in available_dates else 0
    prev_date = available_dates[current_index + 1] if current_index + 1 < len(available_dates) else None
    next_date = available_dates[current_index - 1] if current_index > 0 else None
    
    # Override the relevant_stories count in stats with the actual user-specific count
    stats['relevant_stories'] = len(relevant_stories)
    print(f"📊 Dashboard stats for {user_id} on {target_date}: {len(relevant_stories)} relevant out of {len(all_stories)} total")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "target_date": target_date,
        "stories": all_stories,
        "relevant_stories": relevant_stories,
        "stats": stats,
        "available_dates": available_dates,
        "prev_date": prev_date,
        "next_date": next_date,
        "user": user,
        "user_interests": user_interests
    })

@app.get("/api/stories/{target_date}")
async def api_stories(target_date: str):
    """API endpoint to get stories for a specific date"""
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    stories = db.get_stories_by_date(target_date)
    stats = db.get_stats_by_date(target_date)
    
    return {
        "date": target_date,
        "stats": stats,
        "stories": [
            {
                "id": s.id,
                "rank": s.rank,
                "title": s.title,
                "url": s.url,
                "points": s.points,
                "author": s.author,
                "comments_count": s.comments_count,
                "hn_discussion_url": s.hn_discussion_url,
                "article_summary": s.article_summary,
                "comments_analysis": s.comments_analysis
            }
            for s in stories
        ]
    }

@app.post("/api/interaction/{user_id}/{story_id}")
async def log_story_interaction(user_id: str, story_id: int, interaction_type: str = Form(...), duration: Optional[int] = Form(None)):
    """Log user interaction with a story for learning system"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.log_interaction(user_id, story_id, interaction_type, duration)
        
        # For thumbs up/down, we can immediately learn from this feedback
        if interaction_type in ['thumbs_up', 'thumbs_down']:
            print(f"📊 User feedback: {interaction_type} for story {story_id}")
            
            # Trigger learning system (run in background to avoid blocking response)
            try:
                import threading
                from interest_learner import InterestLearner
                
                def run_learning():
                    try:
                        learner = InterestLearner(db.db_path)
                        
                        # Get total feedback count
                        stats = learner.get_learning_stats()
                        
                        # Run learning cycle every 5 feedback items
                        if stats["total_feedback"] % 5 == 0 and stats["total_feedback"] >= 5:
                            print("🧠 Triggering interest learning cycle...")
                            results = learner.run_learning_cycle(days_back=14)  # Last 2 weeks
                            
                            if results.get("status") == "success":
                                print(f"✅ Learning complete: {results.get('changes_applied', 0)} weights updated")
                    except Exception as e:
                        print(f"⚠️ Learning system error: {e}")
                
                # Run learning in background thread
                learning_thread = threading.Thread(target=run_learning)
                learning_thread.daemon = True
                learning_thread.start()
                
            except ImportError:
                print("⚠️ Interest learning system not available")
            except Exception as e:
                print(f"⚠️ Error starting learning system: {e}")
        
        return {
            "status": "logged", 
            "story_id": story_id, 
            "interaction": interaction_type,
            "message": "Feedback recorded for learning system"
        }
    except Exception as e:
        print(f"❌ Error logging interaction: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/interactions/{user_id}/{story_id}")
async def get_story_interactions(user_id: str, story_id: int):
    """Get all interactions for a specific story by a specific user"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        interactions = db.get_story_interactions(user_id, story_id)
        return {
            "status": "success",
            "user_id": user_id,
            "story_id": story_id,
            "interactions": interactions
        }
    except Exception as e:
        print(f"❌ Error getting interactions: {e}")
        return {"status": "error", "message": str(e)}

@app.delete("/api/interaction/{user_id}/{story_id}/{interaction_type}")
async def remove_story_interaction(user_id: str, story_id: int, interaction_type: str):
    """Remove a specific interaction"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.remove_interaction(user_id, story_id, interaction_type)
        return {
            "status": "removed",
            "user_id": user_id,
            "story_id": story_id,
            "interaction": interaction_type,
            "message": "Interaction removed successfully"
        }
    except Exception as e:
        print(f"❌ Error removing interaction: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/saved-stories/{user_id}")
async def get_saved_stories(user_id: str):
    """Get all saved stories for a specific user"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        saved_stories = db.get_saved_stories(user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "saved_stories": saved_stories
        }
    except Exception as e:
        print(f"❌ Error getting saved stories: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/interests/{user_id}", response_class=HTMLResponse)
async def interests_page(request: Request, user_id: str):
    """User-specific interest management page"""
    # Verify user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user activity
    db.update_user_activity(user_id)
    
    interest_weights = db.get_user_interest_weights(user_id)
    interaction_stats = db.get_user_interaction_stats(user_id)
    
    return templates.TemplateResponse("interests.html", {
        "request": request,
        "interest_weights": interest_weights,
        "interaction_stats": interaction_stats,
        "user": user
    })

@app.post("/interests/{user_id}/update")
async def update_interests(
    user_id: str,
    keyword: str = Form(...),
    category: str = Form(...)
):
    """Add new interest for a specific user with single weight (1.0)"""
    # Verify user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Always use weight 1.0 for all interests
    db.update_user_interest_weight(user_id, keyword, 1.0, category)
    return RedirectResponse(url=f"/interests/{user_id}", status_code=303)

@app.delete("/api/interests/{user_id}/{interest_id}")
async def delete_interest(user_id: str, interest_id: int):
    """Delete a user-specific interest weight"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        success = db.delete_user_interest_weight(user_id, interest_id)
        if success:
            return {"status": "deleted", "user_id": user_id, "interest_id": interest_id, "message": "Interest deleted successfully"}
        else:
            return {"status": "error", "message": "Interest not found"}
    except Exception as e:
        print(f"❌ Error deleting interest: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/learning/stats")
async def get_learning_stats():
    """Get interest learning system statistics"""
    try:
        from interest_learner import InterestLearner
        learner = InterestLearner(db.db_path)
        stats = learner.get_learning_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        print(f"❌ Error getting learning stats: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/learning/run")
async def trigger_learning():
    """Manually trigger the interest learning cycle"""
    try:
        from interest_learner import InterestLearner
        learner = InterestLearner(db.db_path)
        results = learner.run_learning_cycle(days_back=30)
        return {"status": "success", "results": results}
    except Exception as e:
        print(f"❌ Error running learning cycle: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/analytics/{user_id}", response_class=HTMLResponse)
async def analytics_page(request: Request, user_id: str):
    """Analytics and trends page for specific user"""
    # Verify user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Get available dates for this user (from signup date onwards)
    available_dates = db.get_available_dates_for_user(user_id)
    
    # Get user-specific stats for each date
    daily_stats = []
    for date_str in available_dates[-30:]:  # Last 30 days from signup
        stats = db.get_user_stats_by_date(user_id, date_str)
        stats['date'] = date_str
        daily_stats.append(stats)
    
    interaction_stats = db.get_user_interaction_stats(user_id)
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "user": user,
        "daily_stats": daily_stats,
        "interaction_stats": interaction_stats,
        "available_dates": available_dates
    })

@app.post("/api/story/{user_id}/{story_id}/notes")
async def save_story_notes(user_id: str, story_id: int, notes: str = Form(...)):
    """Save personal notes for a story"""
    try:
        print(f"📝 Saving notes for user {user_id}, story {story_id}: '{notes[:50]}...'")
        
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            print(f"❌ User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        print(f"✅ User verified: {user.email}")
        
        db.save_story_notes(user_id, story_id, notes)
        print(f"✅ Notes saved successfully")
        
        return {
            "status": "saved",
            "user_id": user_id,
            "story_id": story_id,
            "message": "Notes saved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving notes: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error saving notes: {str(e)}")

# =============================================================================
# ADMIN/USER MANAGEMENT ROUTES
# =============================================================================

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_list(request: Request, admin: str = Depends(get_current_admin)):
    """Admin interface for viewing all users and their activity"""
    try:
        # Get all users
        all_users = db.get_all_users()
        
        # Get activity stats for each user
        users_with_stats = []
        for user in all_users:
            # Get user's interaction stats (last 30 days)
            interaction_stats = db.get_user_interaction_stats(user.user_id, days=30)
            
            # Get total interest weights
            user_interests = db.get_user_interest_weights(user.user_id)
            
            # Get saved stories count
            saved_stories = db.get_saved_stories(user.user_id)
            
            # Calculate activity score
            total_interactions = sum(stat['count'] for stat in interaction_stats.values())
            activity_score = "High" if total_interactions > 50 else "Medium" if total_interactions > 10 else "Low"
            
            users_with_stats.append({
                'user': user,
                'total_interactions': total_interactions,
                'activity_score': activity_score,
                'interests_count': len(user_interests),
                'saved_stories_count': len(saved_stories),
                'interaction_stats': interaction_stats
            })
        
        # Sort by last activity
        users_with_stats.sort(key=lambda x: x['user'].last_active_at or '1970-01-01', reverse=True)
        
        return templates.TemplateResponse("admin_users.html", {
            "request": request,
            "users_with_stats": users_with_stats,
            "total_users": len(all_users)
        })
        
    except Exception as e:
        print(f"❌ Error in admin users: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading admin interface: {str(e)}")

@app.get("/admin/user/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(request: Request, user_id: str, admin: str = Depends(get_current_admin)):
    """Admin detail view for a specific user"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get comprehensive user data
        user_interests = db.get_user_interest_weights(user_id)
        saved_stories = db.get_saved_stories(user_id)
        interaction_stats = db.get_user_interaction_stats(user_id, days=30)
        
        # Get recent relevant stories (last 3 days)
        available_dates = db.get_available_dates()[:3]
        recent_relevant_stories = []
        for date in available_dates:
            stories_with_relevance = db.get_stories_with_user_relevance(user_id, date)
            # Filter for relevant stories only
            relevant_stories = []
            for story, relevance in stories_with_relevance:
                if relevance and relevance.is_relevant and relevance.relevance_score > 0.0:
                    story.relevance_score = relevance.relevance_score  # Add for template access
                    relevant_stories.append(story)
            recent_relevant_stories.extend(relevant_stories[:5])  # Top 5 per day
        
        # Calculate engagement metrics
        total_interactions = sum(stat['count'] for stat in interaction_stats.values())
        thumbs_up = interaction_stats.get('thumbs_up', {}).get('count', 0)
        thumbs_down = interaction_stats.get('thumbs_down', {}).get('count', 0)
        
        engagement_rate = (thumbs_up + thumbs_down) / max(len(recent_relevant_stories), 1) * 100
        
        return templates.TemplateResponse("admin_user_detail.html", {
            "request": request,
            "user": user,
            "user_interests": user_interests,
            "saved_stories": saved_stories,
            "interaction_stats": interaction_stats,
            "recent_relevant_stories": recent_relevant_stories[:10],
            "total_interactions": total_interactions,
            "engagement_rate": engagement_rate,
            "available_dates": available_dates
        })
        
    except Exception as e:
        print(f"❌ Error in admin user detail: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading user details: {str(e)}")

@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, admin: str = Depends(get_current_admin)):
    """Admin analytics dashboard"""
    try:
        # Get all users for analytics
        all_users = db.get_all_users()
        
        # Get system-wide stats
        available_dates = db.get_available_dates()
        
        # Calculate user engagement stats
        user_engagement = []
        total_interactions_all = 0
        active_users_count = 0
        
        for user in all_users:
            stats = db.get_user_interaction_stats(user.user_id, days=7)  # Last week
            total_user_interactions = sum(stat['count'] for stat in stats.values())
            total_interactions_all += total_user_interactions
            
            if total_user_interactions > 0:
                active_users_count += 1
            
            user_engagement.append({
                'user': user,
                'interactions': total_user_interactions,
                'interests_count': len(db.get_user_interest_weights(user.user_id))
            })
        
        # Sort by engagement
        user_engagement.sort(key=lambda x: x['interactions'], reverse=True)
        
        # Get recent stories stats
        recent_stats = []
        for date in available_dates[:7]:  # Last 7 days
            stats = db.get_stats_by_date(date)
            recent_stats.append({
                'date': date,
                'stats': stats
            })
        
        # Calculate averages
        avg_interactions_per_user = total_interactions_all / len(all_users) if all_users else 0
        user_activity_rate = (active_users_count / len(all_users)) * 100 if all_users else 0
        
        # Get cost optimization data from latest multi-user summary
        cost_optimization_data = None
        try:
            import glob
            import json
            # Find the latest multi_user_summary file in parent directory
            summary_files = glob.glob("../multi_user_summary_*.json")
            if summary_files:
                latest_summary_file = max(summary_files)
                with open(latest_summary_file, 'r') as f:
                    summary_data = json.load(f)
                    cost_optimization_data = summary_data.get('cost_optimization', {})
        except Exception as e:
            print(f"Could not load cost optimization data: {e}")
        
        return templates.TemplateResponse("admin_analytics.html", {
            "request": request,
            "total_users": len(all_users),
            "active_users": active_users_count,
            "user_activity_rate": user_activity_rate,
            "avg_interactions_per_user": avg_interactions_per_user,
            "user_engagement": user_engagement[:10],  # Top 10
            "recent_stats": recent_stats,
            "available_dates": available_dates,
            "cost_optimization": cost_optimization_data
        })
        
    except Exception as e:
        print(f"❌ Error in admin analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading analytics: {str(e)}")

@app.post("/admin/run-multi-user-scrape")
async def admin_trigger_scrape(admin: str = Depends(get_current_admin)):
    """Admin endpoint to trigger multi-user scraping"""
    try:
        import subprocess
        import threading
        
        def run_scrape():
            try:
                result = subprocess.run([
                    "python", "multi_user_scraper.py"
                ], capture_output=True, text=True, cwd="/Users/zebcobb/repos/selenium-hacker-news-scraper")
                print(f"Multi-user scrape completed with return code: {result.returncode}")
                if result.stdout:
                    print(f"Output: {result.stdout}")
                if result.stderr:
                    print(f"Errors: {result.stderr}")
            except Exception as e:
                print(f"Error running multi-user scrape: {e}")
        
        # Run in background thread
        scrape_thread = threading.Thread(target=run_scrape)
        scrape_thread.daemon = True
        scrape_thread.start()
        
        return {
            "status": "started",
            "message": "Multi-user scraping started in background. Check console for progress."
        }
        
    except Exception as e:
        print(f"❌ Error triggering scrape: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/debug/user/{user_id}/relevance/{target_date}")
async def debug_user_relevance(user_id: str, target_date: str):
    """Debug endpoint to check user-specific relevance filtering"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user interests
        user_interests = db.get_user_interest_weights(user_id)
        
        # Get all stories for the date
        all_stories = db.get_stories_by_date(target_date)
        
        debug_results = []
        for story in all_stories[:10]:  # Limit to first 10 for debugging
            is_relevant = db._is_story_relevant_to_user(story, user_interests, debug=True)
            debug_results.append({
                "title": story.title,
                "tags": story.tags,
                "is_relevant": is_relevant,
                "global_relevance": story.is_relevant
            })
        
        return {
            "user_id": user_id,
            "user_interests": [{"keyword": i.keyword, "weight": i.weight, "category": i.category} for i in user_interests],
            "target_date": target_date,
            "debug_results": debug_results
        }
        
    except Exception as e:
        print(f"❌ Error in debug endpoint: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/story/{user_id}/{story_id}/notes")
async def get_story_notes(user_id: str, story_id: int):
    """Get personal notes for a story"""
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        notes = db.get_story_notes(user_id, story_id)
        return {
            "status": "success",
            "user_id": user_id,
            "story_id": story_id,
            "notes": notes
        }
    except Exception as e:
        print(f"❌ Error getting notes: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/saved/{user_id}", response_class=HTMLResponse)
async def saved_stories_page(request: Request, user_id: str):
    """User-specific saved stories page"""
    # Verify user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user activity
    db.update_user_activity(user_id)
    
    saved_stories = db.get_saved_stories(user_id)
    
    # Group stories by date for better organization
    stories_by_date = {}
    for story in saved_stories:
        story_date = story['date']
        if story_date not in stories_by_date:
            stories_by_date[story_date] = []
        stories_by_date[story_date].append(story)
    
    return templates.TemplateResponse("saved.html", {
        "request": request,
        "saved_stories": saved_stories,
        "stories_by_date": stories_by_date,
        "total_saved": len(saved_stories),
        "user": user
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    available_dates = db.get_available_dates()
    return {
        "status": "healthy",
        "database_connected": True,
        "available_dates_count": len(available_dates),
        "latest_date": available_dates[0] if available_dates else None
    }

if __name__ == "__main__":
    # For development
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )