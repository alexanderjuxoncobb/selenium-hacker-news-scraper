# User Onboarding Flow Documentation

## Overview
This document describes the complete user onboarding flow for the multi-user Hacker News scraper dashboard, including how new users get immediate access to relevant stories.

## Problem Solved
Previously, new users would see no relevant stories until the next daily scraping run. This created a poor first experience. The new system processes existing stories immediately when a user signs up.

## Update: Performance Optimization
- Initially processed last 7 days (500-700 stories) which was slow
- Now only processes stories from signup date onwards (typically today's ~30-100 stories)
- Users can only access stories from their signup date forward
- Much faster onboarding experience (2-5 seconds vs 30-60 seconds)

## User Onboarding Flow

### 1. User Registration (`/setup`)
- User enters email and optional name
- User selects interests from predefined topics
- User can add custom interests with priority levels (high/medium/low)

### 2. Interest Processing
When the setup form is submitted:
1. Create new user with UUID
2. Save all selected interests to `user_interest_weights` table
3. **NEW**: Automatically process last 7 days of stories for relevance

### 3. Batch Processing (Automatic)
The `batch_process_user_relevance_from_date()` function:
- Fetches stories only from the user's signup date (today)
- Uses the AI pipeline to calculate relevance for each story
- Stores results in `user_story_relevance` table
- Returns statistics (total stories, relevant stories found)
- Much faster onboarding - only processes ~30-100 stories instead of 500-700

### 4. Success Page
Shows the user:
- Confirmation of account creation
- Number of interests selected
- **Number of relevant stories already found**
- Links to dashboard and interest management

### 5. Immediate Access
Users can now:
- View their dashboard with relevant stories immediately
- See personalized relevance scores and reasoning
- Start interacting with stories (thumbs up/down, save, notes)

## On-Demand Processing

If a user views a date that hasn't been processed:
1. The dashboard checks for missing relevance data
2. If user has interests but no relevance scores, it processes on-demand
3. Processing happens transparently in the background
4. Results are cached for future visits

## Manual Recalculation

For administrators or troubleshooting:

```bash
# List all users
python recalculate_user_relevance.py --list-users

# Process specific user (last 30 days)
python recalculate_user_relevance.py --user-id <UUID>

# Process specific user (last 7 days)
python recalculate_user_relevance.py --user-id <UUID> --days 7

# Process all users
python recalculate_user_relevance.py --all-users --days 7
```

## Database Schema

### Key Tables for Onboarding

1. **users** - Stores user accounts
   - user_id (UUID)
   - email
   - name
   - created_at

2. **user_interest_weights** - User-specific interests
   - user_id
   - keyword
   - weight (1.0, 0.6, 0.3)
   - category (high, medium, low)

3. **user_story_relevance** - Calculated relevance scores
   - user_id
   - story_id
   - is_relevant
   - relevance_score
   - relevance_reasoning

## Performance Considerations

1. **Initial Processing**: Limited to last 7 days to balance completeness vs speed
2. **Caching**: Relevance scores are stored permanently, no recalculation needed
3. **On-Demand**: Only processes when needed, transparent to user
4. **Scalability**: Each user's processing is independent

## Cost Optimization

The batch processing uses the same cost-optimized AI pipeline:
1. Local embeddings for initial filtering (free)
2. OpenAI only for edge cases (0.3-0.5 similarity)
3. Typical cost: ~$0.01-0.02 per user for 7 days of stories

## Future Improvements

1. **Background Jobs**: Move processing to async queue for better performance
2. **Progress Bar**: Real-time progress during initial processing
3. **Selective Processing**: Only process stories from user's interest categories
4. **ML Learning**: Use interaction data to improve relevance over time