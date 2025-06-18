# 🤖 AI-Powered Hacker News Daily Scraper

An intelligent Python-based web scraper that automatically extracts the top 30 Hacker News stories daily, uses AI to analyze their relevance based on your interests, generates detailed article summaries, and provides comprehensive insights from community discussions.

## ✨ Key Features

- **🧠 AI-Powered Relevance Filtering**: Uses OpenAI GPT-4o-mini to intelligently filter stories based on your personal interests
- **📄 Smart Article Summarization**: Generates detailed, specific summaries with concrete details, quotes, and technical insights
- **💬 Advanced Comment Analysis**: AI-powered theme extraction, sentiment analysis, and quote extraction from HN discussions
- **⏰ Daily Automation**: Runs automatically at 8:30 AM London time every day
- **📊 Rich Output**: Generates both structured JSON data and beautifully formatted markdown email digests
- **🔧 Fully Customizable**: Easy to modify interests, scheduling, and analysis parameters

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

### 3. Test the Scraper
```bash
# Quick test (single story, basic info)
python quick_test.py

# Test with full AI processing (3 stories)
python scraper.py test

# Full daily scraping (30 stories with AI analysis)
python scraper.py
```

### 4. Start Daily Scheduler
```bash
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

## 🛠️ Project Structure

```
selenium-hacker-news-scraper/
├── scraper.py              # Main scraping logic with AI integration
├── scheduler.py            # Daily scheduling system
├── quick_test.py          # Simple test script
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore patterns
└── README.md           # This file

Generated Files:
├── hn_scrape_*.json    # Daily scraping data
├── daily_digest_*.md   # Email digest files
└── test_digest_*.md    # Test output files
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

## 📦 Dependencies

**Core Dependencies:**
- `selenium==4.33.0` - Web scraping automation
- `openai==1.88.0` - AI integration for analysis
- `beautifulsoup4==4.13.4` - HTML parsing
- `requests==2.32.4` - HTTP requests
- `schedule==1.2.2` - Daily scheduling
- `python-dotenv==1.1.0` - Environment variables
- `pytz==2025.2` - Timezone handling

**Additional Dependencies:**
- `webdriver-manager==4.0.2` - Chrome driver management
- Various supporting packages for web automation

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

### Environment Variables for Deployment
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## 🎯 Use Cases

- **Personal News Digest**: Get AI-filtered HN stories matching your interests
- **Tech Trend Analysis**: Understand community sentiment on trending technologies
- **Research Tool**: Gather insights on specific technical topics
- **Content Curation**: Create curated content for blogs or newsletters
- **Market Research**: Track startup and technology discussions

## 🚧 Future Enhancements

- **Email Integration**: SMTP setup for automatic email delivery
- **Database Storage**: PostgreSQL for historical data and trend analysis
- **Web Dashboard**: Interactive interface for viewing results
- **Slack/Discord Integration**: Post digests to team channels
- **Advanced Filtering**: More sophisticated AI-powered relevance scoring
- **Multi-source Support**: Expand beyond Hacker News to other tech sites

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