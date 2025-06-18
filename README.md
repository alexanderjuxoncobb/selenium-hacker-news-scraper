# 📰 Hacker News Daily Scraper

A Python-based web scraper that automatically extracts the top 30 Hacker News stories daily, analyzes their relevance, summarizes articles, and provides insights from community discussions.

## 🚀 Features

- **Daily Automation**: Runs at 8:30 AM London time every day
- **Smart Scraping**: Extracts top 30 HN stories with full metadata
- **Article Summarization**: Fetches and summarizes external articles
- **Comment Analysis**: Analyzes community discussions for themes and sentiment
- **AI-Ready**: Placeholder functions ready for AI enhancement
- **Multiple Outputs**: JSON data + Markdown email digest
- **Railway-Ready**: Designed for cloud deployment

## 📁 Project Structure

```
selenium-hacker-news-scraper/
├── scraper.py          # Main scraping logic
├── scheduler.py        # Daily scheduling system
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── venv/              # Virtual environment
└── outputs/           # Generated files (JSON + MD)
```

## 🛠️ Setup Instructions

### 1. Clone and Setup Environment
```bash
cd selenium-hacker-news-scraper
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Test the Scraper
```bash
# Activate virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Test with 3 stories
python scraper.py test

# Full scraping (30 stories)
python scraper.py

# Quick test (single story, no comments)
python quick_test.py
```

### 3. Start Daily Scheduler
```bash
python scheduler.py
```

## 📊 Output Format

### JSON Data (`hn_scrape_YYYYMMDD_HHMMSS.json`)
Structured data including:
- Story metadata (title, URL, points, author, time)
- Article summaries
- Comment analysis with themes and sentiment
- Full comment text and metadata

### Email Digest (`daily_digest_YYYYMMDD_HHMMSS.md`)
Formatted markdown including:
- Executive summary for each relevant story
- Article content summary
- Discussion analysis with top comments
- Direct links to articles and HN discussions

## 🔧 Key Components

### HackerNewsScraper Class
- `scrape_top_stories()`: Extracts HN homepage stories
- `get_article_summary()`: Fetches external article content
- `analyze_comments()`: Scrapes and analyzes HN comments
- `generate_executive_summary()`: Creates story summaries
- `generate_daily_email_content()`: Formats email digest

### Scheduler
- Runs daily at 8:30 AM London time
- Handles timezone conversion
- Automatic error handling and logging

## 🤖 AI Enhancement Placeholders

The following functions are ready for AI integration:

1. **`is_relevant_story()`** - Currently returns True for all stories
   - TODO: Add AI filtering based on user interests
   
2. **`get_article_summary()`** - Basic text extraction
   - TODO: Add AI summarization for better content analysis
   
3. **`_analyze_comment_themes()`** - Basic keyword matching
   - TODO: Add AI theme extraction and sentiment analysis

## 🌍 Deployment Options

### Local Deployment
```bash
# Keep running in background
nohup python scheduler.py &
```

### Cloud Deployment (Railway)
1. Push code to GitHub
2. Connect Railway to your repo
3. Set up PostgreSQL database
4. Configure environment variables
5. Deploy and enable cron scheduling

## 📧 Email Integration (Next Steps)

To complete the email functionality:

1. **Add Email Service**:
   ```python
   import smtplib
   from email.mime.text import MIMEText
   from email.mime.multipart import MIMEMultipart
   ```

2. **Set up SMTP Configuration**:
   - Gmail, SendGrid, or Amazon SES
   - Add credentials to environment variables

3. **Convert Markdown to HTML** for email:
   ```bash
   pip install markdown
   ```

## 🗄️ Database Integration (Next Steps)

For historical data storage:

1. **Install Prisma**:
   ```bash
   pip install prisma
   ```

2. **Set up PostgreSQL** on Railway

3. **Create Data Models** for stories, comments, and summaries

## ⚙️ Configuration

### Customization Options
- Change number of stories: Modify `num_stories` parameter
- Adjust comment analysis: Modify `num_comments` parameter
- Change schedule: Edit `scheduler.py` timing
- Customize themes: Modify keyword lists in `_analyze_comment_themes()`

### Environment Variables (for deployment)
```bash
ANTHROPIC_API_KEY=your_key_here  # For future AI integration
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
DATABASE_URL=postgresql://...
```

## 🧪 Testing

```bash
# Test email generation
python scraper.py test

# Test individual components
python -c "from scraper import HackerNewsScraper; s = HackerNewsScraper(); print(s.scrape_top_stories(1))"
```

## 📝 License

This project is for educational purposes. Be respectful of HN's servers and follow their robots.txt guidelines.

## 🤝 Contributing

Areas for enhancement:
- AI-powered relevance filtering
- Better article summarization
- Advanced sentiment analysis
- Email template improvements
- Database integration
- Web dashboard for viewing results

---

**Generated by Claude Code** 🤖