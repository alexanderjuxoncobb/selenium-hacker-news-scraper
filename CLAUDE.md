# Hacker News Scraper Enhancement Project

## Project Overview
This is an AI-powered Hacker News scraper that needs significant enhancements to maximize daily value. The current system scrapes HN stories, uses OpenAI for relevance filtering and analysis, and generates markdown digests.

## Current Architecture
- **scraper.py**: Main scraping logic with OpenAI integration (456 billion parameters MiniMax-M1 model mentioned in recent digest)
- **scheduler.py**: Daily automation at 8:30 AM London time
- **Output**: JSON data + Markdown email digests
- **AI Features**: Story relevance filtering, article summarization, comment analysis
- **Cost**: Heavy OpenAI API usage for all operations

## Planned Enhancements (Priority Order)

### 1. Cost-Optimized AI Pipeline 
**Goal**: Reduce OpenAI costs by 80% while maintaining quality
**Implementation**:
- Replace expensive relevance filtering with local embeddings (sentence-transformers)
- Use OpenAI only for final summaries and complex analysis
- Implement hybrid approach: local preprocessing → OpenAI refinement
- Add caching for similar stories to avoid duplicate API calls

### 2. Web Dashboard Interface
**Goal**: Replace markdown file reading with proper web interface
**Implementation**:
- Create Flask/FastAPI web app with mobile-responsive design
- Dashboard features:
  - Daily digest viewer with story cards
  - Interest management interface
  - Historical story browser
  - Reading progress tracking
  - Story interaction logging (for learning system)
- Database backend (SQLite initially, PostgreSQL for production)
- URL structure: `/dashboard/YYYY-MM-DD` for daily digests

### 3. Dynamic Interest Learning System
**Goal**: Automatically improve relevance based on user behavior
**Implementation**:
- Track user interactions via web dashboard:
  - Stories clicked/read
  - Time spent reading
  - Stories saved/bookmarked
  - Stories shared
- Machine learning model to adjust interest weights
- Feedback mechanism: thumbs up/down on story relevance
- Weekly interest profile updates based on behavior
- Export/import interest profiles

### 4. Actionable Insights Mode
**Goal**: Transform from news reading to business intelligence
**Implementation**:
- Enhanced AI prompts for extracting:
  - Market signals and trends
  - Investment opportunities
  - Competitive intelligence
  - Technical insights and tutorials
  - Business model analysis
- Separate "Business Insights" section in daily digest
- Company/startup tracking with funding/valuation updates
- Technology adoption trend analysis

### 5. Email Notification with Dashboard Link
**Goal**: Morning email with link to latest web dashboard
**Implementation**:
- SMTP integration (Gmail/SendGrid)
- HTML email template with:
  - Summary stats (X relevant stories found)
  - Top 3 story headlines with relevance scores
  - Direct link to dashboard for full digest
  - Personalized greeting and reading time estimate
- Mobile-optimized email design
- Send at user's optimal reading time (configurable)

## Technical Implementation Details

### Database Schema
```sql
-- Stories table
CREATE TABLE stories (
    id INTEGER PRIMARY KEY,
    date DATE,
    rank INTEGER,
    title TEXT,
    url TEXT,
    points INTEGER,
    author TEXT,
    comments_count INTEGER,
    hn_discussion_url TEXT,
    article_summary TEXT,
    is_relevant BOOLEAN,
    relevance_score FLOAT,
    scraped_at TIMESTAMP
);

-- User interactions for learning
CREATE TABLE user_interactions (
    id INTEGER PRIMARY KEY,
    story_id INTEGER,
    interaction_type TEXT, -- 'click', 'read', 'save', 'share', 'thumbs_up', 'thumbs_down'
    timestamp TIMESTAMP,
    duration_seconds INTEGER,
    FOREIGN KEY (story_id) REFERENCES stories (id)
);

-- Dynamic interests tracking
CREATE TABLE interest_weights (
    id INTEGER PRIMARY KEY,
    keyword TEXT,
    weight FLOAT,
    category TEXT, -- 'high', 'medium', 'low'
    updated_at TIMESTAMP
);
```

### Cost Optimization Strategy
```python
# Current: $0.10-0.30 per day in OpenAI costs
# Target: $0.02-0.06 per day

# Phase 1: Local relevance filtering
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')  # Local embedding model

# Phase 2: Cached summaries
# Store article hashes to avoid re-summarizing same content
# Use Redis/SQLite for caching

# Phase 3: Batch API calls
# Group similar operations, use cheaper models where possible
```

### Web Dashboard Tech Stack
```python
# Backend: FastAPI (async, fast, modern)
# Frontend: Jinja2 templates + HTMX for interactivity
# Database: SQLite for development, PostgreSQL for production
# Styling: Tailwind CSS for rapid UI development
# Charts: Chart.js for trend visualization
```

### Email Integration
```python
# SMTP setup with environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")  # Gmail app password
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# HTML email template with dashboard link
template = """
<h2>🤖 Your Daily HN Digest is Ready</h2>
<p>Found {relevant_count} relevant stories out of {total_count}</p>
<a href="{dashboard_url}" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">
    View Full Dashboard
</a>
"""
```

## File Structure After Enhancements
```
selenium-hacker-news-scraper/
├── scraper.py              # Enhanced with cost optimization
├── scheduler.py            # Updated to trigger dashboard generation
├── dashboard/
│   ├── app.py             # FastAPI web application
│   ├── database.py        # Database models and operations
│   ├── templates/         # Jinja2 HTML templates
│   └── static/           # CSS, JS, images
├── learning/
│   ├── interest_learner.py # ML model for interest learning
│   └── embeddings.py      # Local embedding operations
├── email_sender.py        # Email notification system
├── requirements.txt       # Updated dependencies
├── .env                  # Environment variables
└── CLAUDE.md            # This file
```

## Implementation Status ✅

### ✅ COMPLETED PHASES:

#### **Phase 1: Web Dashboard** ✅
- **FastAPI web application** with mobile-responsive design
- **SQLite database** with comprehensive data models
- **Dashboard interface** at http://localhost:8000
- **Story visualization** with relevance scores and analytics
- **Interest management** page for customizing filters
- **Analytics page** with trends and interaction tracking

#### **Phase 2: Cost-Optimized AI Pipeline** ✅
- **75% cost reduction** achieved in testing
- **Local embeddings** using sentence-transformers (22MB model)
- **Smart caching** for article summaries (7-day expiry)
- **AI refinement** only for edge cases (0.3-0.5 similarity)
- **Efficient comment analysis** with targeted OpenAI usage

#### **Phase 3: User Interaction Tracking** ✅
- **Click tracking** for story engagement
- **Thumbs up/down** feedback system
- **Reading time** monitoring
- **Save/bookmark** functionality
- **Database logging** for learning system preparation

#### **Phase 4: Email Notifications** ✅
- **HTML email templates** with mobile optimization
- **SMTP integration** (Gmail/SendGrid compatible)
- **Dashboard links** in daily emails
- **Cost savings reports** included in emails
- **Configuration via .env** file

#### **Phase 5: Actionable Insights Mode** ✅
- **Business intelligence extraction** from stories
- **Market signals** and investment opportunities
- **Competitive intelligence** tracking
- **Actionable takeaways** with priority scoring
- **Executive summaries** with AI-generated insights

### 🚧 PENDING PHASES:

#### **Phase 6: Dynamic Interest Learning System** 🚧
- Use interaction data to automatically adjust interest weights
- Machine learning model for relevance prediction
- Feedback loop integration
- Weekly interest profile updates

## Current Architecture (IMPLEMENTED)

### **Cost-Optimized AI Pipeline** 💰
```python
# 75% cost savings achieved:
# Traditional: 5 API calls per story analysis
# Optimized: 1-2 API calls per story analysis

# Local embedding filtering (FREE)
similarity_score = cosine_similarity(story_embedding, interest_embeddings)

# Smart caching (FREE for repeated articles)
if url_hash in cache: return cached_summary

# AI refinement (SELECTIVE)
if 0.3 <= confidence <= 0.5: use_openai_refinement()
```

### **Web Dashboard** 🌐
- **Backend**: FastAPI with SQLite/PostgreSQL
- **Frontend**: Jinja2 templates + Tailwind CSS + HTMX
- **Features**: Story cards, analytics, interest management
- **Mobile**: Responsive design for phone/tablet usage

### **Email System** 📧
- **HTML templates** with inline CSS
- **Cost optimization reports** included
- **Dashboard deep links** for each date
- **Story previews** with relevance scores

### **Actionable Insights** 🔍
- **Market Intelligence**: Funding, acquisitions, trends
- **Business Opportunities**: Market gaps, pain points
- **Investment Signals**: Promising startups, sectors
- **Competitive Intelligence**: Strategic moves, partnerships
- **Priority Scoring**: Automatic relevance + engagement scoring

## Success Metrics
- **Cost Reduction**: <$0.10/day OpenAI costs (from current $0.20-0.30)
- **Relevance Improvement**: >90% of recommended stories are actually read
- **User Engagement**: Daily dashboard usage >5 minutes
- **Actionable Value**: At least 1 actionable insight per day
- **Convenience**: <30 seconds from email to reading relevant stories

## Environment Variables Needed
```bash
# Existing
OPENAI_API_KEY=your_openai_key

# New additions
DATABASE_URL=sqlite:///hn_scraper.db  # or PostgreSQL URL
EMAIL_USER=your_email@gmail.com
EMAIL_APP_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient@example.com
DASHBOARD_BASE_URL=http://localhost:8000  # or deployed URL
SECRET_KEY=your-secret-key-for-sessions
```

## Notes for Implementation
- Maintain backward compatibility with existing JSON/MD outputs
- Test each phase thoroughly before moving to next
- Monitor API costs during transition
- Keep user data privacy in mind for interaction tracking
- Design dashboard to work well on mobile devices
- Consider rate limiting for HN scraping to be respectful

---
*This file will be updated as implementation progresses*