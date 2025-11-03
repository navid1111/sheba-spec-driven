"""Test email notifications end-to-end."""
import asyncio
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


async def test_email_notification():
    """Test sending an email notification directly."""
    print("🧪 Testing Email Notification\n")
    
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    
    # Get SMTP settings
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
    smtp_from_name = os.getenv("SMTP_FROM_NAME", "ShoktiAI")
    notification_provider = os.getenv("NOTIFICATION_PROVIDER", "console")
    
    print(f"SMTP Configuration:")
    print(f"  Host: {smtp_host}")
    print(f"  Port: {smtp_port}")
    print(f"  Username: {smtp_username}")
    print(f"  From: {smtp_from_email} ({smtp_from_name})")
    print(f"  Provider: {notification_provider}")
    print()
    
    if notification_provider != "email":
        print("⚠️  Email provider not configured")
        print("   Set NOTIFICATION_PROVIDER=email in .env to test")
        return
    
    if not smtp_username or not smtp_password:
        print("❌ SMTP credentials not configured!")
        return
    
    # Send test notification
    test_email = smtp_from_email  # Send to self for testing
    test_message = "This is a test notification from ShoktiAI Platform. If you're seeing this, email notifications are working! 🎉"
    
    print(f"📧 Sending test notification to: {test_email}")
    print(f"   Message: {test_message[:50]}...")
    print()
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Test Notification from ShoktiAI"
        msg["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        msg["To"] = test_email
        
        # Plain text version
        text_part = MIMEText(test_message, "plain")
        
        # HTML version with styling
        html_content = f"""
        <html>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">ShoktiAI Platform</h1>
            </div>
            <div style="padding: 30px; background-color: #f5f5f5;">
                <div style="background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <p style="color: #333; line-height: 1.6; margin: 0;">{test_message}</p>
                </div>
            </div>
        </body>
        </html>
        """
        html_part = MIMEText(html_content, "html")
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email using SSL (port 465) or STARTTLS (port 587)
        if smtp_port == 465:
            # Use SMTP_SSL for port 465
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            # Use SMTP with STARTTLS for port 587
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        
        print("✅ Email notification sent successfully!")
        print("   Check your inbox (and spam folder)")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_email_notification())
