# 🤖 Enhanced AI-Powered Hacker News Daily Scraper

An intelligent Python-based web scraper with web dashboard, cost-optimised AI pipeline, email notifications, and business intelligence extraction. Automatically scrapes top thirty Hacker News stories daily, analyses relevance with 75% cost savings through local embeddings, and provides actionable insights through a modern web interface.

## ✨ Key Features

### **🚀 Enhanced Pipeline (NEW)**
- **💰 75% Cost Reduction**: Local embeddings and selective OpenAI usage
- **🌐 Web Dashboard**: Modern FastAPI interface with mobile support
- **📧 Email Notifications**: Rich HTML emails with dashboard links
- **🔍 Business Intelligence**: Actionable insights and market signals
- **📊 User Analytics**: Interaction tracking and personalised learning

### **🧠 AI & Analysis**
- **🧠 Cost-Optimised AI Filtering**: Local embeddings with GPT-four-o-mini refinement
- **📄 Smart Article Summarization**: Cached summaries with detailed technical insights
- **💬 Advanced Comment Analysis**: Deep technical extraction and sentiment analysis
- **🎯 Actionable Insights**: Market signals, investment opportunities, competitive intelligence

### **🛠️ Platform Features**
- **⏰ Daily Automation**: Runs automatically at 8:30 AM London time
- **📱 Mobile-Responsive**: Works perfectly on phones, tablets, and desktop
- **💾 Data Persistence**: SQLite database with full history and analytics
- **🔧 Fully Customizable**: Web-based interest management and settings

## 🚀 Quick Start

### 1. Setup Environment
```bash
git clone https://github.com/alexanderjuxoncobb/selenium-hacker-news-scraper.git
cd selenium-hacker-news-scraper
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure OpenAI API
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 3. Test the Enhanced System
```bash
# Test cost-optimised AI pipeline
python ai_pipeline.py

# Test enhanced scraper (three stories with full features)
python enhanced_scraper.py test

# Test email notifications (requires .env setup)
python email_sender.py

# Start web dashboard
cd dashboard
python app.py
# Visit http://localhost:8000
```

### 4. Run Full Enhanced Pipeline
```bash
# Full enhanced daily scraping (30 stories with all features)
python enhanced_scraper.py

# Start daily automation
python scheduler.py
```

## 🧠 AI Integration

### Intelligent Story Filtering
The scraper uses AI to evaluate story relevance based on your interests:

**High Priority Interests:**
- Artificial Intelligence, Machine Learning, AI agents
- Tech startups, software development, programming
- Mathematics, statistics
- Behavioral economics, behavioral finance

**Medium Priority Interests:**
- Robotics, hardware
- Politics (Trump, UK, Europe)
- Health, wellness, running
- Books, reading

**Low Priority Interests:**
- Music technology

### Article Summarization
- Scrapes full article content from external links
- Uses OpenAI GPT-4o-mini to generate detailed summaries
- Includes specific technical details, metrics, quotes, and actionable insights
- Mentions specific tools, technologies, companies, and people by name

### Comment Analysis
- Scrapes and analyzes top comments from HN discussions
- AI-powered theme extraction with specific topics and technologies mentioned
- Sentiment analysis with concrete examples
- Extracts specific quotes showing agreement and disagreement points
- Provides detailed community sentiment summaries

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

## 🛠️ Enhanced Project Structure

```
selenium-hacker-news-scraper/
├── enhanced_scraper.py     # 🚀 Main enhanced scraper (START HERE)
├── ai_pipeline.py          # 💰 Cost-optimized AI with local embeddings  
├── email_sender.py         # 📧 Email notification system
├── actionable_insights.py  # 🔍 Business intelligence analyzer
├── scheduler.py            # ⏰ Daily automation
├── dashboard/              # 🌐 Web Dashboard
│   ├── app.py             #     FastAPI web application
│   ├── database.py        #     Database models & operations
│   ├── templates/         #     HTML templates
│   └── static/           #     CSS, JS, images
├── scraper.py             # 📜 Original scraper (legacy)
├── requirements.txt       # 📦 All dependencies
├── .env.example          # 🔧 Environment variables template
└── CLAUDE.md            # 📋 Detailed project documentation

Generated Files:
├── hn_scraper.db          # 💾 SQLite database
├── .ai_cache/            # 🧠 AI caching directory
├── enhanced_hn_scrape_*.json  # 📊 Enhanced scraping data
├── enhanced_digest_*.md   # 📧 Email digest files
└── test_*.json           # 🧪 Test output files
```

## 🔧 Configuration

### Customizing Your Interests
Edit the `user_interests` dictionary in `scraper.py` (lines 37-50):
```python
self.user_interests = {
    "high_priority": [
        "your", "high", "priority", "topics"
    ],
    "medium_priority": [
        "medium", "priority", "topics"
    ],
    "low_priority": [
        "low", "priority", "topics"
    ]
}
```

### Scheduling Options
- **Default**: 8:30 AM London time daily
- **Testing**: Uncomment line 48 in `scheduler.py` to run every minute
- **Custom**: Modify the schedule in `scheduler.py` line 45

### Story and Comment Limits
- **Stories**: Change `num_stories` parameter (default: 30)
- **Comments**: Change `num_comments` parameter (default: 10 for analysis, 3 for testing)

## 🧪 Testing

```bash
# Quick functionality test
python quick_test.py

# Full AI processing test with 3 stories
python scraper.py test

# Test individual components
python -c "from scraper import HackerNewsScraper; s = HackerNewsScraper(); print(s.scrape_top_stories(1))"
```

## 📦 Enhanced Dependencies

**Core AI & Scraping:**
- `selenium==4.33.0` - Web scraping automation
- `openai==1.88.0` - AI integration for analysis
- `sentence-transformers==4.1.0` - Local embeddings (NEW)
- `scikit-learn==1.7.0` - Machine learning utilities (NEW)
- `beautifulsoup4==4.13.4` - HTML parsing
- `requests==2.32.4` - HTTP requests

**Web Dashboard & API:**
- `fastapi==0.104.1` - Modern web framework (NEW)
- `uvicorn[standard]==0.24.0` - ASGI server (NEW)
- `jinja2==3.1.4` - Template engine (NEW)
- `python-multipart==0.0.20` - Form handling (NEW)

**Automation & Utilities:**
- `schedule==1.2.2` - Daily scheduling
- `python-dotenv==1.1.0` - Environment variables
- `pytz==2025.2` - Timezone handling
- `webdriver-manager==4.0.2` - Chrome driver management

## 🌍 Deployment Options

### Local Deployment
```bash
# Keep running in background
nohup python scheduler.py &

# Or use screen/tmux
screen -S hn-scraper
python scheduler.py
# Ctrl+A, D to detach
```

### Cloud Deployment
1. **Railway/Heroku**: Push to GitHub, connect repository, set environment variables
2. **DigitalOcean**: Deploy on a droplet with cron scheduling
3. **AWS EC2**: Set up instance with CloudWatch scheduling

### Enhanced Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Email Notifications (Optional)
EMAIL_USER=your_email@gmail.com
EMAIL_APP_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Dashboard Configuration (Optional)
DASHBOARD_BASE_URL=http://localhost:8000
SECRET_KEY=your-secret-key-for-sessions

# Database (Optional - defaults to SQLite)
DATABASE_URL=sqlite:///hn_scraper.db
```

## 🎯 Use Cases

- **Personal News Digest**: Get AI-filtered HN stories matching your interests
- **Tech Trend Analysis**: Understand community sentiment on trending technologies
- **Research Tool**: Gather insights on specific technical topics
- **Content Curation**: Create curated content for blogs or newsletters
- **Market Research**: Track startup and technology discussions

## 🎯 Completed Enhancements

- **✅ Email Integration**: Full SMTP setup with rich HTML templates
- **✅ Database Storage**: SQLite with option to upgrade to PostgreSQL
- **✅ Web Dashboard**: Complete FastAPI interface with mobile support
- **✅ Advanced Filtering**: Cost-optimized AI with local embeddings
- **✅ User Analytics**: Interaction tracking and personalized learning
- **✅ Business Intelligence**: Actionable insights and market analysis

## 🚧 Future Possibilities

- **Slack/Discord Integration**: Post digests to team channels
- **Multi-source Support**: Expand beyond Hacker News to other tech sites
- **Mobile App**: React Native or Flutter mobile application
- **Advanced ML**: Automated interest learning from user behavior
- **API Integration**: Connect with productivity tools (Notion, Obsidian)
- **Export Features**: PDF reports, RSS feeds, webhook integrations

## 🤝 Contributing

Areas for enhancement:
- Improve AI prompts for better analysis
- Add more output formats (HTML, PDF)
- Implement email notifications
- Add web interface
- Database integration for historical analysis
- Support for multiple news sources

## 📄 License

This project is for educational and personal use. Please be respectful of Hacker News servers and follow their terms of service and robots.txt guidelines.

## 🙏 Acknowledgments

- Built with [Selenium](https://selenium.dev/) for web automation
- Powered by [OpenAI](https://openai.com/) for intelligent analysis
- Inspired by the [Hacker News](https://news.ycombinator.com/) community

---

**🤖 Enhanced with AI by Claude Code**