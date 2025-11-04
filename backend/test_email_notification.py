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
    test_email = "navidkamal@iut-dhaka.edu"  # Always send to your email for testing
    test_message = """
আসসালামু আলাইকুম!

এটি ShoktiAI থেকে একটি পরীক্ষা বার্তা।

আপনার হোম ক্লিনিং সার্ভিসের জন্য সময় হয়ে গেছে! গত মাসে আপনি আমাদের সেবা নিয়েছিলেন এবং সন্তুষ্ট ছিলেন। আবার বুক করতে নিচের লিংকে ক্লিক করুন।

---

Hello!

This is a test message from ShoktiAI SmartEngage.

It's time for your home cleaning service! Last month you used our service and were satisfied. Click below to book again.

Thank you,
ShoktiAI Team 🎉
"""
    
    print(f"📧 Sending test notification to: {test_email}")
    print(f"   Subject: Test - ShoktiAI SmartEngage Reminder")
    print()
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Test - ShoktiAI SmartEngage Reminder"
        msg["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        msg["To"] = test_email
        
        # Plain text version
        text_part = MIMEText(test_message, "plain")
        
        # HTML version with styling (matching the notification service template)
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">ShoktiAI</h1>
                <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 14px;">SMARTENGAGE • REMINDER</p>
            </div>
            
            <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
                <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
                    <p style="margin: 0; color: #92400e; font-weight: bold;">🧪 TEST MODE</p>
                    <p style="margin: 5px 0 0 0; color: #78350f; font-size: 14px;">
                        This is a test email from the ShoktiAI SmartEngage system.
                    </p>
                </div>
                
                <div style="font-size: 16px; line-height: 1.8;">
                    {test_message.replace(chr(10), '<br>')}
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                        This is an automated message from ShoktiAI. If you wish to unsubscribe, please contact support.
                    </p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
                <p>© 2025 ShoktiAI. All rights reserved.</p>
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
