"""
Manual test script for middleware functionality.
Run this while the server is running on http://127.0.0.1:8000
"""
import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_middleware():
    """Test middleware features manually."""
    print("🧪 Testing Middleware Features\n")
    
    # Test 1: Correlation ID
    print("=" * 60)
    print("Test 1: Correlation ID Generation")
    print("=" * 60)
    response = httpx.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"X-Correlation-ID: {response.headers.get('X-Correlation-ID')}")
    print(f"Response: {response.json()}\n")
    
    # Test 2: Custom Correlation ID
    print("=" * 60)
    print("Test 2: Custom Correlation ID Preservation")
    print("=" * 60)
    custom_id = "test-correlation-123"
    response = httpx.get(
        f"{BASE_URL}/health",
        headers={"X-Correlation-ID": custom_id}
    )
    print(f"Sent: {custom_id}")
    print(f"Received: {response.headers.get('X-Correlation-ID')}")
    print(f"Preserved: {response.headers.get('X-Correlation-ID') == custom_id}\n")
    
    # Test 3: CORS Headers
    print("=" * 60)
    print("Test 3: CORS Headers")
    print("=" * 60)
    response = httpx.get(
        f"{BASE_URL}/health",
        headers={"Origin": "http://localhost:3000"}
    )
    print(f"Access-Control-Allow-Origin: {response.headers.get('access-control-allow-origin')}")
    print(f"Access-Control-Allow-Credentials: {response.headers.get('access-control-allow-credentials')}")
    print()
    
    # Test 4: CORS Preflight
    print("=" * 60)
    print("Test 4: CORS Preflight (OPTIONS)")
    print("=" * 60)
    response = httpx.options(
        f"{BASE_URL}/auth/request-otp",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Access-Control-Allow-Origin: {response.headers.get('access-control-allow-origin')}")
    print(f"Access-Control-Allow-Methods: {response.headers.get('access-control-allow-methods')}")
    print()
    
    # Test 5: Correlation ID on Error
    print("=" * 60)
    print("Test 5: Correlation ID on Error Response")
    print("=" * 60)
    custom_id = "error-test-456"
    response = httpx.post(
        f"{BASE_URL}/auth/request-otp",
        json={"phone_number": "invalid"},  # Missing user_type
        headers={"X-Correlation-ID": custom_id}
    )
    print(f"Status: {response.status_code} (validation error expected)")
    print(f"X-Correlation-ID: {response.headers.get('X-Correlation-ID')}")
    print(f"Error preserved correlation ID: {response.headers.get('X-Correlation-ID') == custom_id}\n")
    
    print("=" * 60)
    print("✅ All middleware features tested!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_middleware()
    except httpx.ConnectError:
        print("❌ Cannot connect to server.")
        print("   Start with: cd backend; ..\.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")
