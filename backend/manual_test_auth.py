"""
Manual Auth Flow Test Script
Demonstrates the complete OTP → JWT authentication flow.
Run this while the server is running on http://127.0.0.1:8000
"""

import httpx
import time

BASE_URL = "http://127.0.0.1:8000"

def test_auth_flow():
    """Test the complete authentication flow."""
    print("🧪 Starting Manual Auth Flow Test\n")
    
    # Step 1: Request OTP
    print("Step 1: Requesting OTP for +8801715914254...")
    response = httpx.post(
        f"{BASE_URL}/auth/request-otp",
        json={"phone_number": "+8801715914254", "user_type": "customer"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    if response.status_code != 200:
        print("❌ Failed to request OTP")
        return
    
    # Step 2: Get OTP from console logs
    print("Step 2: Check the server console for the OTP code")
    print("Look for a line like: 📱 OTP for +8801715914254: 123456")
    otp_code = input("Enter the OTP code from server logs: ").strip()
    
    # Step 3: Verify OTP
    print(f"\nStep 3: Verifying OTP: {otp_code}...")
    response = httpx.post(
        f"{BASE_URL}/auth/verify-otp",
        json={"phone_number": "+8801715914254", "otp_code": otp_code}
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Failed to verify OTP: {response.json()}")
        return
    
    data = response.json()
    print(f"Response: {data}\n")
    
    # Step 4: Decode JWT to verify contents
    token = data["access_token"]
    print(f"✅ Authentication successful!")
    print(f"\nJWT Token (first 50 chars): {token[:50]}...")
    print(f"User ID: {data['user_id']}")
    print(f"User Type: {data['user_type']}")
    print(f"Expires In: {data['expires_in']} seconds ({data['expires_in'] / 3600:.1f} hours)")
    
    # Step 5: Test using the token (optional - when we add protected endpoints)
    print("\n💡 You can now use this token in the Authorization header:")
    print(f"   Authorization: Bearer {token[:30]}...")
    
    print("\n✅ Manual auth flow test completed successfully!")

if __name__ == "__main__":
    try:
        test_auth_flow()
    except httpx.ConnectError:
        print("❌ Cannot connect to server. Make sure it's running on http://127.0.0.1:8000")
        print("   Start with: .venv\\Scripts\\python.exe -m uvicorn src.api.app:app --reload")
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
