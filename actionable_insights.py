#!/usr/bin/env python3
"""
Actionable Insights Module for HN Scraper
Extracts business intelligence, market signals, and actionable opportunities
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv

class ActionableInsightsAnalyzer:
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize actionable insights analyzer"""
        load_dotenv()
        
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key required for insights analysis")
        
        self.openai_client = OpenAI(api_key=api_key)
        
        # Categories for actionable insights
        self.insight_categories = {
            "market_signals": [
                "funding rounds", "acquisitions", "IPOs", "market trends",
                "adoption rates", "revenue growth", "user metrics"
            ],
            "technology_trends": [
                "new frameworks", "programming languages", "tools", "platforms",
                "architecture patterns", "performance improvements"
            ],
            "business_opportunities": [
                "market gaps", "emerging needs", "pain points", "disruption opportunities",
                "business models", "monetization strategies"
            ],
            "competitive_intelligence": [
                "competitor moves", "product launches", "strategy changes",
                "partnerships", "talent acquisition", "market positioning"
            ],
            "investment_signals": [
                "promising startups", "growing sectors", "technology adoption",
                "market validation", "traction indicators", "investor sentiment"
            ]
        }
    
    def analyse_story_for_insights(self, story_data: Dict) -> Dict:
        """
        Extract actionable insights from a story using AI analysis
        """
        title = story_data.get('title', '')
        url = story_data.get('url', '')
        article_summary = story_data.get('article_summary', '')
        comments_analysis = story_data.get('comments_analysis', {})
        
        # Skip analysis for stories without substantial content
        if not article_summary or article_summary in ["No article summary available", "Article content too short to summarize effectively."]:
            return {"has_insights": False, "reason": "Insufficient content for analysis"}
        
        try:
            # Create comprehensive analysis prompt
            prompt = self._create_insights_prompt(title, article_summary, comments_analysis)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a business intelligence analyst specializing in tech industry insights. Provide actionable analysis with specific, concrete recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean up the JSON result
            try:
                insights = json.loads(result)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing error: {e}")
                print(f"Raw response: {result[:200]}...")
                # Return basic insights structure
                return {"has_insights": False, "reason": "JSON parsing failed"}
            
            # Validate and enhance insights
            validated_insights = self._validate_and_enhance_insights(insights, story_data)
            
            return validated_insights
            
        except Exception as e:
            print(f"❌ Error analyzing insights for story: {e}")
            return {"has_insights": False, "reason": f"Analysis error: {str(e)}"}
    
    def _create_insights_prompt(self, title: str, article_summary: str, comments_analysis: Dict) -> str:
        """Create detailed prompt for insights extraction"""
        
        # Include community sentiment if available
        community_context = ""
        if comments_analysis.get('sentiment_summary'):
            community_context = f"\n\nCommunity Discussion Context:\n{comments_analysis['sentiment_summary']}"
        
        prompt = f"""
        Analyze this tech industry story for actionable business insights. Respond with JSON only.

        STORY: {title}
        SUMMARY: {article_summary}{community_context}

        Extract specific, actionable insights in these categories:

        {{
            "has_insights": true/false,
            "market_signals": {{
                "signal_type": "funding/adoption/growth/market_shift",
                "description": "Specific signal with numbers/details",
                "confidence": "high/medium/low",
                "timeframe": "immediate/short_term/long_term"
            }},
            "business_opportunities": {{
                "opportunity_type": "product/service/market/technology",
                "description": "Specific opportunity description",
                "target_market": "Who could benefit",
                "effort_level": "low/medium/high"
            }},
            "competitive_intelligence": {{
                "companies_mentioned": ["company1", "company2"],
                "strategic_moves": "Specific strategic insights",
                "market_impact": "How this affects the competitive landscape"
            }},
            "investment_insights": {{
                "investment_angle": "Why this is investable/watchable",
                "risk_factors": "Key risks to consider",
                "potential_returns": "Expected timeline and potential"
            }},
            "actionable_takeaways": [
                "Specific action item 1",
                "Specific action item 2"
            ],
            "key_metrics": {{
                "numbers_mentioned": ["$50M funding", "2x growth", "10M users"],
                "growth_indicators": "Specific growth metrics",
                "market_size": "Market size indicators if mentioned"
            }}
        }}

        Requirements:
        - Use only valid JSON format with properly escaped strings
        - Include specific companies, numbers, and concrete details
        - Provide actionable recommendations
        - Focus on market opportunities and business impact
        - If no significant insights exist, set has_insights to false
        - Escape all quotes and special characters in strings
        - Keep descriptions concise (under 100 characters each)
        """
        
        return prompt
    
    def _validate_and_enhance_insights(self, insights: Dict, story_data: Dict) -> Dict:
        """Validate and enhance the insights with additional context"""
        
        if not insights.get('has_insights', False):
            return insights
        
        # Add story metadata
        insights['story_metadata'] = {
            'title': story_data.get('title', ''),
            'url': story_data.get('url', ''),
            'points': story_data.get('points', 0),
            'comments_count': story_data.get('comments_count', 0),
            'author': story_data.get('author', ''),
            'relevance_score': story_data.get('relevance_score', 0.0),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Calculate insight priority score
        priority_score = self._calculate_insight_priority(insights, story_data)
        insights['priority_score'] = priority_score
        
        # Add insight categories
        insights['categories'] = self._categorize_insights(insights)
        
        return insights
    
    def _calculate_insight_priority(self, insights: Dict, story_data: Dict) -> float:
        """Calculate priority score based on multiple factors"""
        score = 0.0
        
        # Story engagement (40% weight)
        points = story_data.get('points', 0)
        comments = story_data.get('comments_count', 0)
        engagement_score = min((points / 100) + (comments / 50), 1.0) * 0.4
        score += engagement_score
        
        # Relevance score (30% weight)
        relevance = story_data.get('relevance_score', 0.0)
        score += relevance * 0.3
        
        # Insight quality indicators (30% weight)
        quality_score = 0.0
        
        # Check for specific numbers/metrics
        key_metrics = insights.get('key_metrics', {})
        if key_metrics.get('numbers_mentioned'):
            quality_score += 0.1
        
        # Check for high confidence market signals
        market_signals = insights.get('market_signals', {})
        if market_signals.get('confidence') == 'high':
            quality_score += 0.1
        
        # Check for specific companies mentioned
        competitive_intel = insights.get('competitive_intelligence', {})
        if competitive_intel.get('companies_mentioned'):
            quality_score += 0.05
        
        # Check for actionable takeaways
        takeaways = insights.get('actionable_takeaways', [])
        if len(takeaways) >= 2:
            quality_score += 0.05
        
        score += quality_score
        
        return min(score, 1.0)
    
    def _categorize_insights(self, insights: Dict) -> List[str]:
        """Categorize insights for better organization"""
        categories = []
        
        if insights.get('market_signals', {}).get('signal_type'):
            categories.append('market_intelligence')
        
        if insights.get('business_opportunities', {}).get('opportunity_type'):
            categories.append('business_opportunity')
        
        if insights.get('investment_insights', {}).get('investment_angle'):
            categories.append('investment_signal')
        
        if insights.get('competitive_intelligence', {}).get('companies_mentioned'):
            categories.append('competitive_intelligence')
        
        key_metrics = insights.get('key_metrics', {})
        if key_metrics.get('numbers_mentioned') or key_metrics.get('growth_indicators'):
            categories.append('quantitative_data')
        
        return categories or ['general_insight']
    
    def generate_insights_summary(self, all_insights: List[Dict]) -> Dict:
        """Generate summary of all actionable insights from daily stories"""
        
        # Filter insights with actual content
        valid_insights = [insight for insight in all_insights if insight.get('has_insights', False)]
        
        if not valid_insights:
            return {
                "total_insights": 0,
                "summary": "No actionable insights found in today's stories.",
                "top_insights": [],
                "categories_breakdown": {},
                "priority_distribution": {}
            }
        
        # Sort by priority score
        sorted_insights = sorted(valid_insights, key=lambda x: x.get('priority_score', 0), reverse=True)
        
        # Category breakdown
        categories_breakdown = {}
        for insight in valid_insights:
            for category in insight.get('categories', ['general_insight']):
                categories_breakdown[category] = categories_breakdown.get(category, 0) + 1
        
        # Priority distribution
        priority_distribution = {'high': 0, 'medium': 0, 'low': 0}
        for insight in valid_insights:
            score = insight.get('priority_score', 0)
            if score >= 0.7:
                priority_distribution['high'] += 1
            elif score >= 0.4:
                priority_distribution['medium'] += 1
            else:
                priority_distribution['low'] += 1
        
        # Generate AI summary of top insights
        top_insights = sorted_insights[:5]
        ai_summary = self._generate_ai_summary(top_insights)
        
        return {
            "total_insights": len(valid_insights),
            "summary": ai_summary,
            "top_insights": top_insights[:3],  # Top 3 for display
            "categories_breakdown": categories_breakdown,
            "priority_distribution": priority_distribution,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _generate_ai_summary(self, top_insights: List[Dict]) -> str:
        """Generate AI summary of top insights"""
        if not top_insights:
            return "No high-priority insights identified today."
        
        try:
            # Prepare data for summary
            insights_text = []
            for i, insight in enumerate(top_insights[:3], 1):
                title = insight.get('story_metadata', {}).get('title', 'Unknown Story')
                takeaways = insight.get('actionable_takeaways', [])
                market_signal = insight.get('market_signals', {}).get('description', '')
                opportunity = insight.get('business_opportunities', {}).get('description', '')
                
                insight_summary = f"Story {i}: {title}\n"
                if market_signal:
                    insight_summary += f"Market Signal: {market_signal}\n"
                if opportunity:
                    insight_summary += f"Opportunity: {opportunity}\n"
                if takeaways:
                    insight_summary += f"Actions: {', '.join(takeaways[:2])}\n"
                
                insights_text.append(insight_summary)
            
            combined_insights = "\n".join(insights_text)
            
            prompt = f"""
            Create a concise executive summary (2-3 sentences) of today's key business insights from Hacker News:

            {combined_insights}

            Focus on:
            - Most important trends or opportunities
            - Specific actionable intelligence
            - Market movements or business developments
            
            Write in a direct, actionable style for a business professional.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a business intelligence analyst. Create concise, actionable summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Error generating insights summary: {e}")
            return f"Found {len(top_insights)} actionable insights across market signals, business opportunities, and competitive intelligence."

def test_insights_analyzer():
    """Test the insights analyzer"""
    analyzer = ActionableInsightsAnalyzer()
    
    # Test story
    test_story = {
        "title": "Startup Raises $50M Series B to Build AI-Powered Code Review Tool",
        "url": "https://example.com/startup-funding",
        "points": 150,
        "comments_count": 45,
        "author": "founder123",
        "relevance_score": 0.8,
        "article_summary": "TechCorp announced a $50M Series B funding round led by Sequoia Capital to expand their AI-powered code review platform. The company has grown from 10 to 500 enterprise customers in 18 months, with customers reporting 40% reduction in bugs and 25% faster deployment cycles. The platform uses machine learning to automatically detect security vulnerabilities, code smells, and performance issues.",
        "comments_analysis": {
            "sentiment_summary": "Developers are excited about the technology but concerned about pricing for smaller teams. Several users mentioned they're already beta testing the platform."
        }
    }
    
    print("🧪 Testing actionable insights analyzer...")
    insights = analyzer.analyse_story_for_insights(test_story)
    
    print(f"\n📊 Insights Analysis Results:")
    print(f"Has insights: {insights.get('has_insights', False)}")
    print(f"Priority score: {insights.get('priority_score', 0):.2f}")
    print(f"Categories: {insights.get('categories', [])}")
    
    if insights.get('has_insights'):
        if insights.get('market_signals'):
            print(f"Market Signal: {insights['market_signals'].get('description', 'N/A')}")
        
        if insights.get('actionable_takeaways'):
            print(f"Action Items: {insights['actionable_takeaways']}")

if __name__ == "__main__":
    test_insights_analyzer()