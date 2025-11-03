"""Test authentication API with email."""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_request_otp():
    """Test requesting OTP via email."""
    url = f"{BASE_URL}/auth/request-otp"
    
    payload = {
        "email": "navidkamal568@gmail.com"
    }
    
    print(f"🔐 Testing /auth/request-otp")
    print(f"   Email: {payload['email']}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ OTP request successful!")
            print("📧 Check your email for the OTP code")
            return True
        else:
            print(f"\n❌ OTP request failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_verify_otp(email: str, code: str):
    """Test verifying OTP."""
    url = f"{BASE_URL}/auth/verify-otp"
    
    payload = {
        "email": email,
        "code": code
    }
    
    print(f"\n🔒 Testing /auth/verify-otp")
    print(f"   Email: {payload['email']}")
    print(f"   Code: {payload['code']}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ OTP verification successful!")
            print("🎫 JWT token received")
            return True
        else:
            print(f"\n❌ OTP verification failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing ShoktiAI Email Authentication API")
    print("=" * 60)
    print()
    
    # Make sure server is running
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Server is running\n")
        else:
            print("❌ Server health check failed\n")
    except:
        print("❌ Server is not running!")
        print("   Start server with: uvicorn src.main:app --reload")
        exit(1)
    
    # Test OTP request
    if test_request_otp():
        print("\n" + "=" * 60)
        print("Enter the OTP code from your email to test verification:")
        code = input("OTP Code: ").strip()
        
        if code:
            test_verify_otp("navidkamal568@gmail.com", code)
    
    print()
    print("=" * 60)
