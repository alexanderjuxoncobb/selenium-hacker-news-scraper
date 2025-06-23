# Railway Deployment Guide

This guide will help you deploy your Hacker News Scraper to Railway with PostgreSQL and scheduled daily emails.

## Prerequisites

1. A Railway account (sign up at https://railway.app)
2. Railway CLI installed (optional but recommended)
3. Your project pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Step 1: Prepare Your Environment Variables

Create a `.env` file with the following variables:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# Email Configuration
EMAIL_USER=your_email@gmail.com
EMAIL_APP_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Dashboard Configuration
DASHBOARD_BASE_URL=https://your-app-name.up.railway.app
SECRET_KEY=your-secret-key-generate-a-random-string
ADMIN_PASSWORD=your-secure-admin-password

# Database (will be auto-configured by Railway)
# DATABASE_URL=postgresql://... (Railway will set this automatically)
```

## Step 2: Deploy to Railway

### Option A: Deploy via Railway Dashboard (Recommended)

1. Go to https://railway.app and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account and select your repository
5. Railway will auto-detect the configuration

### Option B: Deploy via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize new project
railway init

# Link to your repository
railway link

# Deploy
railway up
```

## Step 3: Add PostgreSQL Database

1. In your Railway project dashboard, click "New Service"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a PostgreSQL instance
4. The `DATABASE_URL` will be automatically injected into your app

## Step 4: Configure Environment Variables

1. In your Railway project dashboard, click on your app service
2. Go to "Variables" tab
3. Add all the environment variables from your `.env` file:
   - `OPENAI_API_KEY`
   - `EMAIL_USER`
   - `EMAIL_APP_PASSWORD`
   - `RECIPIENT_EMAIL`
   - `SMTP_SERVER`
   - `SMTP_PORT`
   - `DASHBOARD_BASE_URL` (use your Railway app URL)
   - `SECRET_KEY`
   - `ADMIN_PASSWORD`

## Step 5: Run Initial Database Migration

After deployment, you'll need to migrate your existing SQLite data to PostgreSQL:

1. SSH into your Railway instance or use the Railway CLI:
   ```bash
   railway run python migrate_to_postgresql.py
   ```

2. Verify the migration:
   ```bash
   railway run python -c "from dashboard.database import DatabaseManager; db = DatabaseManager(); print(db.get_available_dates())"
   ```

## Step 6: Set Up Cron Job for Daily Emails

Railway supports cron jobs through their platform:

1. In your Railway project dashboard, click "New Service"
2. Select "Cron Job"
3. Configure the cron job:
   - **Name**: Daily HN Scraper
   - **Schedule**: `30 8 * * *` (8:30 AM UTC, adjust for London time)
   - **Command**: `python railway_cron.py`
   - **Service**: Select your main app service

For London time (GMT/BST), you might want to adjust the cron schedule:
- Winter (GMT): `30 8 * * *` (8:30 AM)
- Summer (BST): `30 7 * * *` (7:30 AM UTC = 8:30 AM BST)

## Step 7: Verify Deployment

1. Visit your Railway app URL (e.g., `https://your-app-name.up.railway.app`)
2. Log in with your admin credentials
3. Check that the dashboard loads correctly
4. Verify database connection by viewing available dates

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure `DATABASE_URL` is properly set by Railway
   - Check PostgreSQL service is running

2. **Email Not Sending**
   - Verify Gmail App Password is correct
   - Check SMTP settings
   - Enable "Less secure app access" or use App Passwords

3. **Cron Job Not Running**
   - Check cron schedule syntax
   - Verify timezone settings
   - Check Railway logs for errors

### Viewing Logs

```bash
# View app logs
railway logs

# View specific service logs
railway logs -s your-service-name
```

## Monitoring

1. Railway provides built-in monitoring in the dashboard
2. Set up error notifications in Railway settings
3. Monitor daily email delivery
4. Check PostgreSQL usage and performance

## Cost Estimation

Railway pricing (as of 2025):
- **Hobby Plan**: $5/month (includes $5 of usage)
- **PostgreSQL**: ~$0.01/GB/hour
- **Compute**: ~$0.01/GB RAM/hour
- **Cron Jobs**: Included in compute time

Estimated monthly cost: $10-20 for a single-user setup

## Security Considerations

1. Always use strong passwords for `ADMIN_PASSWORD`
2. Rotate `SECRET_KEY` periodically
3. Use Railway's built-in SSL (automatic)
4. Regularly update dependencies
5. Monitor for suspicious activity

## Backup Strategy

1. Railway automatically backs up PostgreSQL
2. Consider setting up additional backups:
   ```bash
   # Export data
   railway run python -c "from dashboard.database import DatabaseManager; # export logic"
   ```

3. Store backups in external service (S3, Google Cloud Storage)

## Next Steps

1. Set up custom domain (optional)
2. Configure monitoring alerts
3. Set up user registration if needed
4. Optimize performance based on usage

---

For more help, check:
- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Issues: https://github.com/your-username/your-repo/issues