"""Quick test script for Email OTP"""
import asyncio
import sys
sys.path.insert(0, '.')

from src.services.otp_provider import EmailOTPProvider

async def test_email():
    """Test sending email OTP"""
    try:
        provider = EmailOTPProvider()
        print("✅ Email provider initialized")
        
        result = await provider.send_otp("navidkamal568@gmail.com", "123456")
        
        if result:
            print("✅ Email sent successfully!")
            print("📧 Check your inbox at navidkamal568@gmail.com")
        else:
            print("❌ Failed to send email")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_email())
