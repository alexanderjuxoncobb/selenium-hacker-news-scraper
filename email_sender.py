#!/usr/bin/env python3
"""
Email Notification System for HN Scraper
Sends daily digest notifications with dashboard links
"""

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
import resend

class EmailNotifier:
    def __init__(self):
        """Initialize email notifier with configuration from environment"""
        load_dotenv()
        
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_APP_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        self.dashboard_base_url = os.getenv('DASHBOARD_BASE_URL')
        if not self.dashboard_base_url:
            # For local development, use localhost
            self.dashboard_base_url = 'http://localhost:8000'
            print("⚠️  DASHBOARD_BASE_URL not set, using localhost:8000 for development")
        elif not self.dashboard_base_url.startswith(('http://', 'https://')):
            # Add https:// if no protocol specified
            self.dashboard_base_url = f'https://{self.dashboard_base_url}'
            print(f"ℹ️  Added https:// to DASHBOARD_BASE_URL: {self.dashboard_base_url}")
        
        # Validate configuration
        if not all([self.email_user, self.email_password, self.recipient_email]):
            raise ValueError(
                "Missing email configuration. Please set EMAIL_USER, EMAIL_APP_PASSWORD, "
                "and RECIPIENT_EMAIL in your .env file"
            )
    
    def create_daily_digest_email(self, digest_data: Dict, user_email: Optional[str] = None, user_id: Optional[str] = None) -> MIMEMultipart:
        """Create HTML email for daily digest with dashboard link"""
        
        scrape_date = digest_data.get('scrape_date', datetime.now().isoformat())
        date_str = scrape_date[:10]  # YYYY-MM-DD
        total_stories = digest_data.get('total_stories', 0)
        relevant_stories = digest_data.get('relevant_stories', 0)
        cost_report = digest_data.get('cost_optimization', {})
        
        # Get top 3 most relevant stories for preview
        stories = digest_data.get('stories', [])
        relevant_story_previews = [
            story for story in stories 
            if story.get('is_relevant', False)
        ][:3]
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"🤖 Your Daily HN Digest - {date_str} ({relevant_stories} relevant stories)"
        message["From"] = self.email_user
        message["To"] = user_email or self.recipient_email
        
        # Dashboard URL
        # Use user_id for personalized dashboard URL if available
        if user_id:
            dashboard_url = f"{self.dashboard_base_url}/dashboard/{user_id}/{date_str}"
        else:
            dashboard_url = f"{self.dashboard_base_url}/dashboard/{date_str}"
        
        # Create HTML content
        html_content = self._generate_html_email(
            date_str, total_stories, relevant_stories, 
            relevant_story_previews, dashboard_url, cost_report, user_id
        )
        
        # Create plain text fallback
        text_content = self._generate_text_email(
            date_str, total_stories, relevant_stories, 
            relevant_story_previews, dashboard_url, cost_report, user_id
        )
        
        # Attach parts
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        
        message.attach(part1)
        message.attach(part2)
        
        return message
    
    def _generate_html_email(self, date_str: str, total_stories: int, relevant_stories: int, 
                           story_previews: list, dashboard_url: str, cost_report: dict, user_id: str = None) -> str:
        """Generate HTML email content"""
        
        # Story previews HTML
        story_cards = ""
        for i, story in enumerate(story_previews, 1):
            relevance_score = story.get('relevance_score', 0.0)
            score_emoji = '🔥' if relevance_score > 0.7 else '⭐' if relevance_score > 0.5 else '🔍'
            
            story_cards += f"""
            <div style="background: #f8f9fa; border-left: 4px solid #ff6600; padding: 16px; margin: 12px 0; border-radius: 4px;">
                <h3 style="margin: 0 0 8px 0; color: #1f2937; font-size: 16px;">
                    {score_emoji} {story['title']}
                </h3>
                <p style="margin: 0; color: #6b7280; font-size: 14px;">
                    {story['points']} points • {story['author']} • {story['comments_count']} comments
                    • Relevance: {relevance_score:.2f}/1.0
                </p>
                <a href="{story['url']}" style="color: #ff6600; text-decoration: none; font-size: 14px;">
                    Read Article →
                </a>
            </div>
            """
        
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Your Daily HN Digest</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #374151; margin: 0; padding: 20px; background-color: #f9fafb;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #ff6600, #ff8533); color: white; padding: 24px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: bold;">
                        🤖 Your Daily HN Digest
                    </h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 16px;">
                        {date_str}
                    </p>
                </div>
                
                <!-- Summary -->
                <div style="padding: 24px;">
                    <div style="background: #f3f4f6; padding: 16px; border-radius: 6px; margin-bottom: 20px;">
                        <h2 style="margin: 0 0 8px 0; color: #1f2937; font-size: 18px;">📊 Today's Summary</h2>
                        <p style="margin: 0; color: #6b7280;">
                            Found <strong style="color: #ff6600;">{relevant_stories} relevant stories</strong> 
                            out of {total_stories} total stories
                        </p>
                    </div>
                    
                    
                    <!-- Main CTA Button -->
                    <div style="text-align: center; margin: 24px 0;">
                        <a href="{dashboard_url}" 
                           target="_blank" rel="noopener noreferrer"
                           style="display: inline-block; background: #ff6600; color: white; padding: 14px 28px; 
                                  text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;
                                  box-shadow: 0 2px 4px rgba(255, 102, 0, 0.3);">
                            📱 View Full Dashboard
                        </a>
                    </div>
                    
                    <!-- Story Previews -->
                    {f'<h2 style="color: #1f2937; margin: 24px 0 12px 0;">🔥 Top Relevant Stories</h2>{story_cards}' if story_previews else '<p style="text-align: center; color: #6b7280; font-style: italic;">No relevant stories found today. Consider adjusting your interests in the dashboard.</p>'}
                    
                    <!-- Footer Links -->
                    <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; margin-top: 24px; text-align: center;">
                        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">
                            Quick Links:
                        </p>
                        <a href="{self.dashboard_base_url}/interests{'/' + user_id if user_id else ''}" target="_blank" rel="noopener noreferrer" style="color: #ff6600; text-decoration: none; margin: 0 12px;">
                            ⚙️ Manage Interests
                        </a>
                        <a href="{self.dashboard_base_url}/analytics{'/' + user_id if user_id else ''}" target="_blank" rel="noopener noreferrer" style="color: #ff6600; text-decoration: none; margin: 0 12px;">
                            📊 View Analytics
                        </a>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f9fafb; padding: 16px; text-align: center; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">
                        🤖 Generated by your Enhanced Hacker News Scraper<br>
                        Powered by local embeddings and a selective OpenAI refinement
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_email(self, date_str: str, total_stories: int, relevant_stories: int, 
                           story_previews: list, dashboard_url: str, cost_report: dict, user_id: str = None) -> str:
        """Generate plain text email content"""
        
        text_parts = [
            f"🤖 Your Daily HN Digest - {date_str}",
            "=" * 40,
            "",
            f"📊 Summary: {relevant_stories} relevant stories out of {total_stories} total",
        ]
        
        
        text_parts.extend([
            "",
            f"📱 View Full Dashboard: {dashboard_url}",
            "",
        ])
        
        # Add story previews
        if story_previews:
            text_parts.append("🔥 Top Relevant Stories:")
            text_parts.append("")
            
            for i, story in enumerate(story_previews, 1):
                relevance_score = story.get('relevance_score', 0.0)
                score_emoji = '🔥' if relevance_score > 0.7 else '⭐' if relevance_score > 0.5 else '🔍'
                
                text_parts.extend([
                    f"{i}. {score_emoji} {story['title']}",
                    f"   {story['points']} points • {story['author']} • {story['comments_count']} comments",
                    f"   Relevance: {relevance_score:.2f}/1.0",
                    f"   Read: {story['url']}",
                    ""
                ])
        else:
            text_parts.extend([
                "No relevant stories found today.",
                "Consider adjusting your interests in the dashboard.",
                ""
            ])
        
        text_parts.extend([
            "Quick Links:",
            f"⚙️ Manage Interests: {self.dashboard_base_url}/interests{'/' + user_id if user_id else ''}",
            f"📊 View Analytics: {self.dashboard_base_url}/analytics{'/' + user_id if user_id else ''}",
            "",
            "🤖 Generated by your Enhanced Hacker News Scraper"
        ])
        
        return "\n".join(text_parts)
    
    def send_email(self, message: MIMEMultipart, recipient_email: Optional[str] = None) -> bool:
        """Send email using SMTP (supports custom recipient)"""
        try:
            recipient = recipient_email or self.recipient_email
            if not recipient:
                raise ValueError("No recipient email specified")
            
            # Create secure SSL context
            context = ssl.create_default_context()
            
            # Connect to server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.email_user, self.email_password)
                
                text = message.as_string()
                server.sendmail(self.email_user, recipient, text)
            
            print(f"✅ Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            return False
    
    def send_daily_digest(self, digest_data: Dict, user_email: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """Send daily digest email (supports multi-user)"""
        try:
            message = self.create_daily_digest_email(digest_data, user_email, user_id)
            return self.send_email(message, user_email)
        except Exception as e:
            print(f"❌ Error creating/sending daily digest email: {str(e)}")
            return False
    
    def send_multi_user_digests(self, users_data: list) -> Dict:
        """
        Send personalised digest emails to multiple users
        
        Args:
            users_data: List of dicts with keys: 'user', 'digest_data', 'user_email'
            
        Returns:
            Dict with success/failure counts and details
        """
        results = {
            "total_users": len(users_data),
            "emails_sent": 0,
            "emails_failed": 0,
            "failed_users": [],
            "success_users": []
        }
        
        print(f"📧 Sending personalised digests to {len(users_data)} users...")
        
        for user_data in users_data:
            user = user_data.get('user')
            digest_data = user_data.get('digest_data')
            user_email = user_data.get('user_email', user.get('email') if user else None)
            user_id = user.get('user_id') if user else None
            user_name = user.get('name', user.get('email', 'User')) if user else "User"
            
            if not user_email:
                print(f"⚠️ No email for user {user_name} (ID: {user_id})")
                results["emails_failed"] += 1
                results["failed_users"].append({
                    "user_id": user_id,
                    "name": user_name,
                    "reason": "No email address"
                })
                continue
            
            try:
                success = self.send_daily_digest(digest_data, user_email, user_id)
                if success:
                    results["emails_sent"] += 1
                    results["success_users"].append({
                        "user_id": user_id,
                        "name": user_name,
                        "email": user_email
                    })
                    print(f"✅ Sent digest to {user_name} ({user_email})")
                else:
                    results["emails_failed"] += 1
                    results["failed_users"].append({
                        "user_id": user_id,
                        "name": user_name,
                        "email": user_email,
                        "reason": "SMTP send failed"
                    })
                    print(f"❌ Failed to send digest to {user_name} ({user_email})")
                    
            except Exception as e:
                results["emails_failed"] += 1
                results["failed_users"].append({
                    "user_id": user_id,
                    "name": user_name,
                    "email": user_email,
                    "reason": str(e)
                })
                print(f"❌ Error sending to {user_name} ({user_email}): {e}")
        
        print(f"📊 Email summary: {results['emails_sent']} sent, {results['emails_failed']} failed")
        return results
    
    def send_test_email(self) -> bool:
        """Send a test email to verify configuration"""
        try:
            # Create test message
            message = MIMEMultipart()
            message["Subject"] = "🧪 HN Scraper Email Test"
            message["From"] = self.email_user
            message["To"] = self.recipient_email
            
            # Test content
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #ff6600;">🧪 Email Configuration Test</h2>
                <p>Your HN Scraper email system is working correctly!</p>
                <p><strong>Configuration:</strong></p>
                <ul>
                    <li>SMTP Server: {self.smtp_server}:{self.smtp_port}</li>
                    <li>From: {self.email_user}</li>
                    <li>To: {self.recipient_email}</li>
                    <li>Dashboard URL: {self.dashboard_base_url}</li>
                </ul>
                <p>You're all set to receive daily digest emails! 🎉</p>
            </body>
            </html>
            """
            
            text = f"""
            🧪 Email Configuration Test
            
            Your HN Scraper email system is working correctly!
            
            Configuration:
            - SMTP Server: {self.smtp_server}:{self.smtp_port}
            - From: {self.email_user}
            - To: {self.recipient_email}
            - Dashboard URL: {self.dashboard_base_url}
            
            You're all set to receive daily digest emails! 🎉
            """
            
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)
            
            return self.send_email(message)
            
        except Exception as e:
            print(f"❌ Error sending test email: {str(e)}")
            return False

class ResendEmailNotifier(EmailNotifier):
    """Email notifier using Resend API instead of SMTP"""
    
    def __init__(self):
        """Initialize Resend email notifier"""
        load_dotenv()
        
        # Resend configuration
        self.resend_api_key = os.getenv('RESEND_API_KEY')
        if not self.resend_api_key:
            raise ValueError("Missing RESEND_API_KEY in .env file")
        
        # Configure Resend
        resend.api_key = self.resend_api_key
        
        # Email configuration
        self.email_user = os.getenv('EMAIL_USER', 'digest@yourdomain.com')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        self.dashboard_base_url = os.getenv('DASHBOARD_BASE_URL')
        if not self.dashboard_base_url:
            # For local development, use localhost
            self.dashboard_base_url = 'http://localhost:8000'
            print("⚠️  DASHBOARD_BASE_URL not set, using localhost:8000 for development")
        elif not self.dashboard_base_url.startswith(('http://', 'https://')):
            # Add https:// if no protocol specified
            self.dashboard_base_url = f'https://{self.dashboard_base_url}'
            print(f"ℹ️  Added https:// to DASHBOARD_BASE_URL: {self.dashboard_base_url}")
        
        # Validate configuration (RECIPIENT_EMAIL not required for multi-user mode)
        if not self.recipient_email:
            print("⚠️  RECIPIENT_EMAIL not set - only multi-user emails will work")
    
    def send_email(self, message: MIMEMultipart, recipient_email: Optional[str] = None) -> bool:
        """Send email using Resend API"""
        try:
            recipient = recipient_email or self.recipient_email
            if not recipient:
                raise ValueError("No recipient email specified")
            
            # Extract subject from message
            subject = message["Subject"]
            
            # Get HTML and text parts
            html_content = None
            text_content = None
            
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    html_content = part.get_payload(decode=True).decode()
                elif part.get_content_type() == "text/plain":
                    text_content = part.get_payload(decode=True).decode()
            
            # Send via Resend
            response = resend.Emails.send({
                "from": self.email_user,
                "to": recipient,
                "subject": subject,
                "html": html_content,
                "text": text_content
            })
            
            print(f"✅ Email sent successfully to {recipient} via Resend (ID: {response.get('id', 'unknown')})")
            return True
            
        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown error"
            print(f"❌ Error sending email via Resend: {error_msg}")
            # Try to extract more error details if available
            if hasattr(e, '__dict__'):
                print(f"   Error details: {e.__dict__}")
            return False
    
    def send_test_email(self) -> bool:
        """Send a test email via Resend to verify configuration"""
        try:
            # Send test email directly via Resend
            response = resend.Emails.send({
                "from": self.email_user,
                "to": self.recipient_email,
                "subject": "🧪 HN Scraper Email Test (Resend)",
                "html": f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #ff6600;">🧪 Email Configuration Test (Resend)</h2>
                    <p>Your HN Scraper email system is working correctly with Resend!</p>
                    <p><strong>Configuration:</strong></p>
                    <ul>
                        <li>Email Provider: Resend API</li>
                        <li>From: {self.email_user}</li>
                        <li>To: {self.recipient_email}</li>
                        <li>Dashboard URL: {self.dashboard_base_url}</li>
                    </ul>
                    <p>You're all set to receive daily digest emails! 🎉</p>
                </body>
                </html>
                """,
                "text": f"""
                🧪 Email Configuration Test (Resend)
                
                Your HN Scraper email system is working correctly with Resend!
                
                Configuration:
                - Email Provider: Resend API
                - From: {self.email_user}
                - To: {self.recipient_email}
                - Dashboard URL: {self.dashboard_base_url}
                
                You're all set to receive daily digest emails! 🎉
                """
            })
            
            print(f"✅ Test email sent successfully! (ID: {response.get('id', 'unknown')})")
            return True
            
        except Exception as e:
            print(f"❌ Error sending test email: {str(e)}")
            return False


def get_email_notifier():
    """Factory function to get the appropriate email notifier based on configuration"""
    load_dotenv()
    email_provider = os.getenv('EMAIL_PROVIDER', 'smtp').lower()
    
    if email_provider == 'resend':
        print("📧 Using Resend for email delivery")
        return ResendEmailNotifier()
    else:
        print("📧 Using SMTP for email delivery")
        return EmailNotifier()


def test_email_system():
    """Test the email notification system"""
    try:
        notifier = get_email_notifier()
        print("🧪 Testing email system...")
        
        # Send test email
        success = notifier.send_test_email()
        if success:
            print("✅ Email system is working correctly!")
        else:
            print("❌ Email system test failed")
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n📝 To set up email notifications:")
        print("1. Add these variables to your .env file:")
        print("\n   For Resend (recommended):")
        print("   EMAIL_PROVIDER=resend")
        print("   RESEND_API_KEY=your_resend_api_key")
        print("   EMAIL_USER=digest@yourdomain.com")
        print("   RECIPIENT_EMAIL=recipient@example.com")
        print("   DASHBOARD_BASE_URL=http://localhost:8000")
        print("\n   For SMTP/Gmail:")
        print("   EMAIL_PROVIDER=smtp  # or leave blank")
        print("   EMAIL_USER=your_email@gmail.com")
        print("   EMAIL_APP_PASSWORD=your_gmail_app_password")
        print("   RECIPIENT_EMAIL=recipient@example.com")
        print("   DASHBOARD_BASE_URL=http://localhost:8000")
        print("\n2. For Gmail, create an app password:")
        print("   https://support.google.com/accounts/answer/185833")
        print("\n3. For Resend, get your API key:")
        print("   https://resend.com/api-keys")

if __name__ == "__main__":
    test_email_system()