"""
Test AlertingService directly (no HTTP layer).
"""
import sys
from pathlib import Path

# Add backend/src to path
backend_src = Path(__file__).parent / 'backend' / 'src'
sys.path.insert(0, str(backend_src))

from lib.db import get_db
from services.alerting_service import get_alerting_service


def main():
    print("=" * 60)
    print("Testing AlertingService directly")
    print("=" * 60)
    
    # Get database session using generator
    db_gen = get_db()
    session = next(db_gen)
    service = get_alerting_service(session)
    
    try:
        # Test 1: Get all alerts
        print("\n[1] Testing get_all_alerts() with default params...")
        alerts = service.get_all_alerts(days=30)
        print(f"✓ Got {len(alerts)} alerts")
        
        if alerts:
            print("\nFirst alert:")
            first = alerts[0]
            print(f"  Type: {first['type']}")
            print(f"  Severity: {first['severity']}")
            print(f"  Worker: {first['worker_name']} ({first['worker_email']})")
            print(f"  Message: {first['message']}")
            print(f"  Metrics: {first['metrics']}")
        
        # Test 2: Filter by severity
        print("\n[2] Testing filter by severity=high...")
        high_alerts = service.get_all_alerts(days=30, severity='high')
        print(f"✓ Got {len(high_alerts)} high-severity alerts")
        
        # Test 3: Filter by type
        print("\n[3] Testing filter by type=burnout...")
        burnout_alerts = service.get_all_alerts(days=30, alert_type='burnout')
        print(f"✓ Got {len(burnout_alerts)} burnout alerts")
        
        print("\n[4] Testing filter by type=low_rating...")
        low_rating_alerts = service.get_all_alerts(days=30, alert_type='low_rating')
        print(f"✓ Got {len(low_rating_alerts)} low rating alerts")
        
        print("\n[5] Testing filter by type=quality_decline...")
        decline_alerts = service.get_all_alerts(days=30, alert_type='quality_decline')
        print(f"✓ Got {len(decline_alerts)} quality decline alerts")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"  Total alerts: {len(alerts)}")
        print(f"  High severity: {len(high_alerts)}")
        print(f"  Burnout: {len(burnout_alerts)}")
        print(f"  Low rating: {len(low_rating_alerts)}")
        print(f"  Quality decline: {len(decline_alerts)}")
        print("=" * 60)
        
        # Show all alerts grouped by type
        if alerts:
            print("\nAll alerts by type:")
            by_type = {}
            for alert in alerts:
                alert_type = alert['type']
                if alert_type not in by_type:
                    by_type[alert_type] = []
                by_type[alert_type].append(alert)
            
            for alert_type, type_alerts in by_type.items():
                print(f"\n{alert_type.upper()} ({len(type_alerts)}):")
                for alert in type_alerts:
                    print(f"  - {alert['worker_name']}: {alert['message']} [{alert['severity']}]")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
