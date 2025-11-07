"""Test metrics service directly."""
from src.lib.db import SessionLocal
from src.services.metrics_service import get_metrics_service
from datetime import datetime, timedelta, timezone

db = SessionLocal()
metrics_service = get_metrics_service(db)

print("Testing MetricsService...")

try:
    # Test overview
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    print(f"\n1. Testing get_engagement_by_segment...")
    engagement = metrics_service.get_engagement_by_segment(start_date, end_date)
    print(f"   Total customers: {engagement['total_customers']}")
    print(f"   New: {engagement['new']}")
    
    print(f"\n2. Testing get_conversion_metrics...")
    conversions = metrics_service.get_conversion_metrics(start_date, end_date)
    print(f"   Messages sent: {conversions['messages_sent']}")
    print(f"   Conversion rate: {conversions['conversion_rate']}%")
    
    print(f"\n3. Testing get_worker_performance_summary...")
    workers = metrics_service.get_worker_performance_summary(start_date, end_date)
    print(f"   Total workers: {workers['total_workers']}")
    print(f"   Average rating: {workers['average_rating']}")
    
    print(f"\n4. Testing get_active_alerts_count...")
    alerts = metrics_service.get_active_alerts_count()
    print(f"   Total alerts: {alerts['total']}")
    
    print(f"\n5. Testing get_overview_metrics...")
    overview = metrics_service.get_overview_metrics(start_date, end_date)
    print(f"   Overview keys: {list(overview.keys())}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
