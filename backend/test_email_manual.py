"""
Manual test script to verify CoachNova email sending works.
"""
import asyncio
from uuid import uuid4
from src.services.notification_service import EmailNotificationProvider

async def test_email():
    """Test email sending directly."""
    print("Testing email notification provider...")
    
    provider = EmailNotificationProvider()
    
    if not provider.available:
        print("❌ Email provider not available (check SMTP settings)")
        return False
    
    print("✅ Email provider initialized")
    
    test_email = "navidkamal568@gmail.com"  # Same as SMTP username
    test_message = """প্রিয় নাভিদ,

এটি একটি টেস্ট মেসেজ। আপনার CoachNova ইমেল সিস্টেম সঠিকভাবে কাজ করছে।

This is a test message. Your CoachNova email system is working correctly.

শুভকামনা,
শক্তি টিম"""
    
    print(f"Sending test email to {test_email}...")
    
    success = await provider.send(
        to=test_email,
        message=test_message,
        subject="CoachNova Test Email - শক্তি থেকে টেস্ট ইমেল",
        agent_type="coachnova",
        message_type="test",
    )
    
    if success:
        print(f"✅ Email sent successfully to {test_email}")
        print("Check your inbox!")
    else:
        print(f"❌ Failed to send email")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(test_email())
    exit(0 if result else 1)
