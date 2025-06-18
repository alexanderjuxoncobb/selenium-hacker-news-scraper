#!/usr/bin/env python3
"""
FastAPI Web Dashboard for HN Scraper
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, date, timedelta
import json
from typing import Optional
import os
import uvicorn

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import DatabaseManager, init_interest_weights

app = FastAPI(title="HN Scraper Dashboard", description="AI-Powered Hacker News Daily Digest")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Initialize database
db = DatabaseManager("../hn_scraper.db")

@app.on_event("startup")
async def startup_event():
    """Initialize database and import existing data on startup"""
    # Initialize default interests if not already done
    interest_weights = db.get_interest_weights()
    if not interest_weights:
        init_interest_weights(db)
        print("✅ Initialized default interest weights")
    
    # Import any existing JSON data (both old and enhanced formats)
    import glob
    json_files = glob.glob("../hn_scrape_*.json") + glob.glob("../enhanced_hn_scrape_*.json")
    for json_file in json_files:
        try:
            # Check if this file's data is already imported
            file_date = json_file.split('_')[2][:8]  # Extract YYYYMMDD
            formatted_date = f"{file_date[:4]}-{file_date[4:6]}-{file_date[6:8]}"
            existing_stories = db.get_stories_by_date(formatted_date)
            
            if not existing_stories:
                db.import_json_data(json_file)
        except Exception as e:
            print(f"⚠️  Error importing {json_file}: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirect to today's digest or latest available"""
    available_dates = db.get_available_dates()
    
    if not available_dates:
        return templates.TemplateResponse("no_data.html", {"request": request})
    
    # Try to find today's data, otherwise use latest
    today = date.today().isoformat()
    target_date = today if today in available_dates else available_dates[0]
    
    return RedirectResponse(url=f"/dashboard/{target_date}")

@app.get("/dashboard/{target_date}", response_class=HTMLResponse)
async def dashboard(request: Request, target_date: str):
    """Main dashboard page for a specific date"""
    try:
        # Validate date format
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get stories and stats
    stories = db.get_stories_by_date(target_date)
    relevant_stories = [s for s in stories if s.is_relevant]
    stats = db.get_stats_by_date(target_date)
    available_dates = db.get_available_dates()
    
    if not stories:
        return templates.TemplateResponse("no_data.html", {
            "request": request,
            "target_date": target_date,
            "available_dates": available_dates
        })
    
    # Get navigation dates
    current_index = available_dates.index(target_date) if target_date in available_dates else 0
    prev_date = available_dates[current_index + 1] if current_index + 1 < len(available_dates) else None
    next_date = available_dates[current_index - 1] if current_index > 0 else None
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "target_date": target_date,
        "stories": stories,
        "relevant_stories": relevant_stories,
        "stats": stats,
        "available_dates": available_dates,
        "prev_date": prev_date,
        "next_date": next_date
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
                "is_relevant": s.is_relevant,
                "relevance_score": s.relevance_score,
                "comments_analysis": s.comments_analysis
            }
            for s in stories
        ]
    }

@app.post("/api/interaction/{story_id}")
async def log_story_interaction(story_id: int, interaction_type: str = Form(...), duration: Optional[int] = Form(None)):
    """Log user interaction with a story for learning system"""
    try:
        db.log_interaction(story_id, interaction_type, duration)
        
        # For thumbs up/down, we can immediately learn from this feedback
        if interaction_type in ['thumbs_up', 'thumbs_down']:
            print(f"📊 User feedback: {interaction_type} for story {story_id}")
            # TODO: Update interest weights based on feedback
        
        return {
            "status": "logged", 
            "story_id": story_id, 
            "interaction": interaction_type,
            "message": "Feedback recorded for learning system"
        }
    except Exception as e:
        print(f"❌ Error logging interaction: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/interactions/{story_id}")
async def get_story_interactions(story_id: int):
    """Get all interactions for a specific story"""
    try:
        interactions = db.get_story_interactions(story_id)
        return {
            "status": "success",
            "story_id": story_id,
            "interactions": interactions
        }
    except Exception as e:
        print(f"❌ Error getting interactions: {e}")
        return {"status": "error", "message": str(e)}

@app.delete("/api/interaction/{story_id}/{interaction_type}")
async def remove_story_interaction(story_id: int, interaction_type: str):
    """Remove a specific interaction"""
    try:
        db.remove_interaction(story_id, interaction_type)
        return {
            "status": "removed",
            "story_id": story_id,
            "interaction": interaction_type,
            "message": "Interaction removed successfully"
        }
    except Exception as e:
        print(f"❌ Error removing interaction: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/saved-stories")
async def get_saved_stories():
    """Get all saved stories with their details"""
    try:
        saved_stories = db.get_saved_stories()
        return {
            "status": "success",
            "saved_stories": saved_stories
        }
    except Exception as e:
        print(f"❌ Error getting saved stories: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/interests", response_class=HTMLResponse)
async def interests_page(request: Request):
    """Interest management page"""
    interest_weights = db.get_interest_weights()
    interaction_stats = db.get_user_interaction_stats()
    
    return templates.TemplateResponse("interests.html", {
        "request": request,
        "interest_weights": interest_weights,
        "interaction_stats": interaction_stats
    })

@app.post("/interests/update")
async def update_interests(
    keyword: str = Form(...),
    weight: float = Form(...),
    category: str = Form(...)
):
    """Update interest weight"""
    db.update_interest_weight(keyword, weight, category)
    return RedirectResponse(url="/interests", status_code=303)

@app.delete("/api/interests/{interest_id}")
async def delete_interest(interest_id: int):
    """Delete an interest weight"""
    try:
        success = db.delete_interest_weight(interest_id)
        if success:
            return {"status": "deleted", "interest_id": interest_id, "message": "Interest deleted successfully"}
        else:
            return {"status": "error", "message": "Interest not found"}
    except Exception as e:
        print(f"❌ Error deleting interest: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics and trends page"""
    available_dates = db.get_available_dates()
    
    # Get stats for each date
    daily_stats = []
    for date_str in available_dates[-30:]:  # Last 30 days
        stats = db.get_stats_by_date(date_str)
        stats['date'] = date_str
        daily_stats.append(stats)
    
    interaction_stats = db.get_user_interaction_stats()
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "daily_stats": daily_stats,
        "interaction_stats": interaction_stats,
        "available_dates": available_dates
    })

@app.post("/api/story/{story_id}/notes")
async def save_story_notes(story_id: int, notes: str = Form(...)):
    """Save personal notes for a story"""
    try:
        db.save_story_notes(story_id, notes)
        return {
            "status": "saved",
            "story_id": story_id,
            "message": "Notes saved successfully"
        }
    except Exception as e:
        print(f"❌ Error saving notes: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/story/{story_id}/notes")
async def get_story_notes(story_id: int):
    """Get personal notes for a story"""
    try:
        notes = db.get_story_notes(story_id)
        return {
            "status": "success",
            "story_id": story_id,
            "notes": notes
        }
    except Exception as e:
        print(f"❌ Error getting notes: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/saved", response_class=HTMLResponse)
async def saved_stories_page(request: Request):
    """Saved stories page"""
    saved_stories = db.get_saved_stories()
    
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
        "total_saved": len(saved_stories)
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