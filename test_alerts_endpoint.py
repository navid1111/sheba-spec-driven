"""
Test admin alerts endpoints via HTTP.
"""
import requests


BASE_URL = "http://localhost:8000"


def main():
    print("=" * 60)
    print("Testing /admin/alerts endpoints")
    print("=" * 60)
    
    try:
        # Test 1: Get all alerts (default params)
        print("\n[1] GET /admin/alerts (default)")
        response = requests.get(f"{BASE_URL}/admin/alerts")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total alerts: {data['total']}")
            
            if data['alerts']:
                print("\nFirst alert:")
                first = data['alerts'][0]
                print(f"  Type: {first['type']}")
                print(f"  Severity: {first['severity']}")
                print(f"  Worker: {first['worker_name']}")
                print(f"  Message: {first['message']}")
                
                # Show all alerts summary
                print(f"\nAll {data['total']} alerts:")
                by_type = {}
                by_severity = {}
                
                for alert in data['alerts']:
                    # By type
                    t = alert['type']
                    if t not in by_type:
                        by_type[t] = 0
                    by_type[t] += 1
                    
                    # By severity
                    s = alert['severity']
                    if s not in by_severity:
                        by_severity[s] = 0
                    by_severity[s] += 1
                
                print("\nBy type:")
                for t, count in by_type.items():
                    print(f"  {t}: {count}")
                
                print("\nBy severity:")
                for s, count in by_severity.items():
                    print(f"  {s}: {count}")
            else:
                print("No alerts found (workers may be performing well!)")
        else:
            print(f"Error: {response.text}")
        
        # Test 2: Filter by severity
        print("\n" + "=" * 60)
        print("[2] GET /admin/alerts?severity=high")
        response = requests.get(f"{BASE_URL}/admin/alerts?severity=high")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"High severity alerts: {data['total']}")
        
        # Test 3: Filter by type
        print("\n" + "=" * 60)
        print("[3] GET /admin/alerts?alert_type=burnout")
        response = requests.get(f"{BASE_URL}/admin/alerts?alert_type=burnout")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Burnout alerts: {data['total']}")
            
            if data['alerts']:
                for alert in data['alerts']:
                    print(f"  - {alert['worker_name']}: {alert['message']}")
        
        # Test 4: Different time window
        print("\n" + "=" * 60)
        print("[4] GET /admin/alerts?days=7")
        response = requests.get(f"{BASE_URL}/admin/alerts?days=7")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Alerts (last 7 days): {data['total']}")
        
        print("\n[OK] All endpoint tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to backend server")
        print("Make sure the backend is running: cd backend/src && python -m uvicorn api.app:app --reload")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
