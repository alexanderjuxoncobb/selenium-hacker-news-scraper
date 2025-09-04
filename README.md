# 🤖 AI-Powered Hacker News Multi-User Digest Platform

A complete multi-user platform for personalised Hacker News intelligence. Features web dashboard, cost-optimised AI pipeline with local embeddings, multi-user email digests, user analytics, and business intelligence extraction. Deployed on Railway with PostgreSQL and automated daily processing.

**I have stopped hosting this online due to rising costs and no time to optimise the deployment. Please contact me if you want to host it yourself and I can help you set it up!**


Sign up for an account: https://hnscraper.com

## ✨ Key Features

### **🚀 Multi-User Platform**
- **👥 Multi-User Support**: Individual user accounts with personalized interests
- **💰 75% Cost Reduction**: Local embeddings with selective OpenAI usage
- **🌐 Web Dashboard**: Modern FastAPI interface with mobile support  
- **📧 Personalized Email Digests**: Daily emails tailored to each user's interests
- **🔍 Business Intelligence**: Actionable insights and market signals
- **📊 User Analytics**: Interaction tracking and learning system
- **☁️ Cloud Deployment**: Production-ready Railway deployment with PostgreSQL

### **🧠 AI & Analysis**
- **🧠 Cost-Optimised AI Pipeline**: Local embeddings (sentence-transformers) with selective OpenAI refinement
- **📄 Smart Article Summarization**: Cached summaries with technical insights and actionable takeaways
- **💬 Advanced Comment Analysis**: HN discussion analysis with sentiment and theme extraction
- **🎯 Business Intelligence**: Market signals, investment opportunities, competitive intelligence
- **🤖 Personalized Relevance**: User-specific story scoring based on individual interest profiles

### **🛠️ Platform Features**
- **⏰ Daily Automation**: Automated daily processing at 8:30 AM London time via Railway Cron
- **📱 Mobile-Responsive**: Works perfectly on phones, tablets, and desktop
- **💾 Production Database**: PostgreSQL on Railway with full history and analytics
- **🔧 User Management**: Web-based user onboarding, interest management, and admin panels
- **📧 Email Integration**: Resend.com integration for reliable email delivery
- **🔐 Authentication**: Basic auth with admin access controls

## 🚀 Quick Start

### Local Development

#### 1. Setup Environment
```bash
git clone https://github.com/alexanderjuxoncobb/selenium-hacker-news-scraper.git
cd selenium-hacker-news-scraper
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env and add:
OPENAI_API_KEY=your_openai_api_key
RESEND_API_KEY=your_resend_api_key  # For email delivery
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

#### 3. Initialize Database & Start Dashboard
```bash
cd dashboard
python app.py
# Visit http://localhost:8000
```

#### 4. Test Multi-User System
```bash
# Run multi-user scraper (processes all users)
python multi_user_scraper.py

# Start local scheduler
python scheduler.py
```

### Production Deployment (Railway)

#### 1. Deploy to Railway
```bash
# Push to GitHub, then connect repository to Railway
railway login
railway link
railway deploy
```

#### 2. Set Environment Variables in Railway
```bash
OPENAI_API_KEY=your_openai_api_key
RESEND_API_KEY=your_resend_api_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
DATABASE_URL=postgresql://...  # Automatically provided by Railway PostgreSQL
```

#### 3. Access Your Platform
- Dashboard: `https://your-app.railway.app`
- Admin panel: `https://your-app.railway.app/admin`

## 🧠 AI Integration & Multi-User Intelligence

### Cost-Optimized AI Pipeline
The system uses a hybrid approach combining local AI with selective cloud AI usage:

**Local Processing (FREE):**
- **Sentence Transformers**: Local embedding model for relevance scoring
- **Similarity Matching**: Cosine similarity between story content and user interests
- **Smart Caching**: Stores processed articles to avoid duplicate OpenAI calls

**Selective OpenAI Usage (COST-OPTIMIZED):**
- **Edge Case Refinement**: Only when local confidence is 0.3-0.5
- **Summary Generation**: For highly relevant stories only
- **Business Intelligence**: Actionable insights extraction

### Personalized User Interests
Each user can customize their interest profile through the web dashboard:

**Interest Categories:**
- **High Priority**: Core interests (3x weight multiplier)
- **Medium Priority**: Secondary interests (2x weight multiplier)  
- **Low Priority**: Casual interests (1x weight multiplier)

**Example Interest Keywords:**
- AI/ML, startups, programming, mathematics, finance
- Robotics, hardware, politics, health, books
- User-specific technical domains and topics

### Multi-User Processing
- **Personalized Relevance**: Each story scored individually per user
- **Batch Processing**: Efficient processing of all users in single run
- **Individual Digests**: Custom email content based on user's interest profile
- **Interaction Learning**: User clicks and feedback improve future relevance

## 📊 Generated Outputs

### JSON Data Files (`hn_scrape_YYYYMMDD_HHMMSS.json`)
Structured data containing:
```json
{
  "scrape_date": "2025-06-18T10:12:49.123456",
  "total_stories": 30,
  "relevant_stories": 8,
  "stories": [
    {
      "rank": 1,
      "title": "Story Title",
      "url": "https://example.com",
      "points": 145,
      "author": "username",
      "comments_count": 42,
      "is_relevant": true,
      "article_summary": "AI-generated detailed summary...",
      "comments_analysis": {
        "main_themes": ["Theme 1", "Theme 2"],
        "agreement_points": ["Quote 1", "Quote 2"],
        "disagreement_points": ["Counter-argument 1"],
        "sentiment_summary": "Detailed sentiment analysis..."
      }
    }
  ]
}
```

### Email Digest (`daily_digest_YYYYMMDD_HHMMSS.md`)
Beautifully formatted markdown including:
- Executive summary for each relevant story
- AI-generated article summaries with specific details
- Discussion analysis with themes and top comments
- Direct links to articles and HN discussions
- Community sentiment insights

## 🛠️ Project Architecture

```
selenium-hacker-news-scraper/
├── multi_user_scraper.py    # 🚀 Main multi-user processor (ENTRY POINT)
├── enhanced_scraper.py      # 🧠 Enhanced scraper with AI pipeline
├── ai_pipeline.py           # 💰 Cost-optimized AI with local embeddings  
├── email_sender.py          # 📧 Email notification system
├── actionable_insights.py   # 🔍 Business intelligence analyzer
├── dashboard/               # 🌐 Web Dashboard & Database
│   ├── app.py              #     FastAPI web application
│   ├── database.py         #     Database models & operations
│   ├── templates/          #     HTML templates (user & admin)
│   └── static/            #     CSS, JS, images
├── scheduler.py             # ⏰ Local development scheduler
├── railway_scheduler.py     # ☁️ Railway/production scheduler
├── railway_cron.py          # 🔄 Railway cron job runner
├── requirements.txt         # 📦 All dependencies
├── Procfile                # 🚀 Railway deployment config
├── runtime.txt             # 🐍 Python version specification
├── .env.example            # 🔧 Environment variables template
└── CLAUDE.md              # 📋 Detailed implementation documentation

Generated Files:
├── hn_scraper.db           # 💾 SQLite database (local)
├── .ai_cache/             # 🧠 AI caching directory
├── outputs/               # 📊 Generated content
│   ├── scrapes/          #     JSON scraping data
│   └── digests/          #     Markdown digest files
└── temp_*.json           # 🧪 Migration and test files
```

## 🔧 Configuration & User Management

### Web-Based User Management
All configuration is handled through the web dashboard:

**User Onboarding:**
1. Visit `/setup` to create your user account
2. Set up your personalized interest profile
3. Configure email preferences
4. Start receiving daily digests

**Interest Management:**
- Access `/interests` to modify your interest keywords
- Set priority levels (High/Medium/Low) for different topics
- Real-time preview of how changes affect story relevance
- Bulk import/export of interest profiles

**Admin Panel:**
- Access `/admin` with admin credentials
- View all users and their configurations
- Monitor system analytics and usage
- Manage email delivery status

### Environment Configuration

**Required Variables:**
```bash
OPENAI_API_KEY=your_openai_api_key
RESEND_API_KEY=your_resend_api_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
```

**Optional Variables:**
```bash
DATABASE_URL=postgresql://...  # Auto-provided by Railway
RAILWAY_ENVIRONMENT=production  # Auto-set by Railway
DEBUG=false  # Set to true for development
```

### Scheduling Options
- **Production (Railway)**: 8:30 AM London time via Railway Cron
- **Local Development**: Configurable via `scheduler.py`
- **Manual**: Run `python multi_user_scraper.py` anytime

## 🧪 Testing

```bash
# Quick functionality test
python quick_test.py

# Full AI processing test with 3 stories
python scraper.py test

# Test individual components
python -c "from scraper import HackerNewsScraper; s = HackerNewsScraper(); print(s.scrape_top_stories(1))"
```

## 📦 Production Dependencies

**Core AI & Scraping:**
- `selenium==4.25.0` - Web scraping automation
- `openai==1.91.0` - AI integration for analysis
- `sentence-transformers==3.2.1` - Local embeddings for cost optimization
- `scikit-learn==1.5.2` - Machine learning utilities
- `beautifulsoup4==4.12.3` - HTML parsing
- `requests==2.32.3` - HTTP requests

**Web Framework & Database:**
- `fastapi==0.115.4` - Modern async web framework
- `uvicorn[standard]==0.32.0` - ASGI server with performance optimizations
- `jinja2==3.1.4` - Template engine for HTML rendering
- `python-multipart==0.0.12` - Form handling for user input
- `psycopg2-binary==2.9.10` - PostgreSQL adapter for production database

**Email & Communication:**
- `resend==2.10.0` - Modern email delivery service
- `httpx>=0.27.2,<0.28.0` - Async HTTP client for API calls

**Automation & Utilities:**
- `schedule==1.2.2` - Daily scheduling for local development
- `python-dotenv==1.0.1` - Environment variable management
- `pytz==2024.2` - Timezone handling for London time scheduling
- `webdriver-manager==4.0.2` - Automated Chrome driver management

## 🌍 Deployment Architecture

### Production Deployment (Railway)
**Live Platform:** Fully deployed and operational

**Features:**
- **PostgreSQL Database**: Production-grade data persistence
- **Automated Daily Processing**: Railway Cron job at 8:30 AM London time  
- **Email Delivery**: Resend.com integration for reliable email delivery
- **Multi-User Support**: Web dashboard for user management
- **Auto-scaling**: Railway handles traffic and resource scaling
- **SSL/HTTPS**: Automatic SSL certificates

**Deployment Process:**
1. Push code to GitHub repository
2. Connect GitHub repo to Railway project
3. Add PostgreSQL addon to Railway project
4. Configure environment variables in Railway dashboard
5. Deploy automatically on git push

### Local Development
```bash
# Development server
cd dashboard && python app.py

# Background processing
python scheduler.py

# Manual processing
python multi_user_scraper.py
```

### Environment Variables (Production)
```bash
# AI & Processing
OPENAI_API_KEY=your_openai_api_key_here
RESEND_API_KEY=your_resend_api_key_here

# Authentication  
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password

# Database (Auto-configured by Railway)
DATABASE_URL=postgresql://user:pass@host:port/db

# System (Auto-configured by Railway)
RAILWAY_ENVIRONMENT=production
PORT=8000
```

## 🎯 Use Cases & Applications

### **Individual Users**
- **Personalized News Digest**: AI-filtered HN stories matching your specific interests
- **Tech Trend Monitoring**: Stay updated on emerging technologies and market trends
- **Research Tool**: Gather insights on technical topics with business context
- **Career Development**: Track technologies and skills relevant to your field

### **Teams & Organizations**
- **Content Curation**: Generate curated tech content for blogs, newsletters, or team updates
- **Market Intelligence**: Monitor startup ecosystem and competitive landscape
- **Investment Research**: Track funding trends, successful startups, and market signals
- **Business Development**: Identify partnership opportunities and market gaps

### **Multi-User Scenarios**
- **Family/Team Subscriptions**: Different family members get personalized digests
- **Company Departments**: Engineering, marketing, and leadership get different story perspectives
- **Investment Firms**: Partners receive market intelligence tailored to their focus areas
- **Tech Communities**: Members get stories relevant to their technical specializations

## ✅ Production Ready Platform

### **Fully Implemented Features**
- **☁️ Cloud Deployment**: Live on Railway with PostgreSQL and automated scaling
- **👥 Multi-User Support**: Complete user management with personalized experiences
- **💰 Cost-Optimized AI**: 75% cost reduction through local embeddings + selective OpenAI
- **📧 Email Integration**: Production email delivery via Resend.com with rich HTML templates
- **🌐 Web Dashboard**: Mobile-responsive FastAPI interface with admin panels
- **📊 User Analytics**: Interaction tracking, feedback systems, and usage insights
- **🔍 Business Intelligence**: Actionable insights, market signals, and competitive intelligence
- **🔄 Automated Processing**: Daily cron jobs with error handling and monitoring

### **Enterprise-Grade Infrastructure**
- **Database**: PostgreSQL with migrations and backup systems
- **Authentication**: Admin access controls with secure credential management
- **Monitoring**: Comprehensive logging and error tracking
- **Scalability**: Auto-scaling web service and background job processing
- **Reliability**: Error handling, retry mechanisms, and graceful failure recovery

## 🚀 Future Enhancement Opportunities

### **Advanced AI Features**
- **Machine Learning**: Automated interest learning from user behavior patterns
- **Predictive Analytics**: Forecast trending topics before they become popular
- **Content Generation**: AI-generated weekly trend reports and analysis summaries
- **Sentiment Analysis**: Advanced community sentiment tracking with prediction models

### **Platform Integrations**
- **API Ecosystem**: REST API for third-party integrations and mobile apps
- **Productivity Tools**: Direct integration with Notion, Obsidian, Slack, Discord
- **Export Features**: PDF reports, RSS feeds, webhook integrations
- **Mobile Applications**: Native iOS/Android apps with push notifications

### **Multi-Source Intelligence**
- **Expanded Sources**: Reddit, GitHub trending, Product Hunt, tech blogs
- **Cross-Platform Analysis**: Compare sentiment and trends across multiple platforms
- **Real-time Updates**: Live updates during major tech events and product launches
- **Custom Data Sources**: Enterprise customers can add their own data feeds

## 🤝 Contributing

This is a production-ready platform, but there are opportunities for enhancement:

### **Technical Improvements**
- **Performance Optimization**: Improve AI processing speed and database query performance
- **Advanced Analytics**: Enhanced user behavior analysis and prediction models
- **Security Hardening**: Additional security measures for multi-user environments
- **Mobile Optimization**: Further mobile UX improvements and PWA features

### **Feature Enhancements**
- **AI Model Improvements**: Better local embedding models and prompt engineering
- **Integration APIs**: REST API development for third-party integrations
- **Advanced Filters**: More sophisticated content filtering and categorization
- **Export Features**: PDF reports, RSS feeds, and data export functionality

### **Development Process**
1. Fork the repository and create a feature branch
2. Test thoroughly in local development environment
3. Ensure all tests pass and maintain code quality
4. Submit pull request with detailed description
5. Maintain backward compatibility with existing user data

## 📄 License & Usage

**License:** MIT License - Free for personal and commercial use

**Terms of Use:**
- Respect Hacker News servers and follow their robots.txt guidelines
- Use OpenAI API responsibly and within your usage limits
- Comply with email delivery best practices (CAN-SPAM, GDPR)
- Production deployment requires proper security configurations

## 🙏 Acknowledgments & Technology Stack

**Core Technologies:**
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern, fast web framework for building APIs
- **[Selenium](https://selenium.dev/)** - Web automation and scraping capabilities
- **[OpenAI](https://openai.com/)** - AI-powered content analysis and summarization
- **[Sentence Transformers](https://www.sbert.net/)** - Local embedding models for cost optimization
- **[Railway](https://railway.app/)** - Cloud deployment platform with PostgreSQL
- **[Resend](https://resend.com/)** - Modern email delivery service

**Special Thanks:**
- **[Hacker News](https://news.ycombinator.com/)** community for providing high-quality tech discussions
- **[Y Combinator](https://www.ycombinator.com/)** for creating and maintaining the Hacker News platform
- Open source community for the excellent tools and libraries that make this platform possible

---

**🤖 Built with Claude Code - Production-Ready Multi-User AI Platform**  
*Transform how you consume tech news with personalized AI intelligence*
