"""Test admin workers route directly."""
from src.lib.db import SessionLocal
from src.api.routes.admin_workers import _calculate_worker_performance
from datetime import datetime, timedelta, timezone
from uuid import UUID

db = SessionLocal()

try:
    # Get a worker ID from database
    from src.models.workers import Worker
    from sqlalchemy import select
    
    stmt = select(Worker).limit(1)
    result = db.execute(stmt)
    worker = result.scalar_one_or_none()
    
    if not worker:
        print("No workers found in database")
    else:
        print(f"Testing with worker: {worker.id}")
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        performance = _calculate_worker_performance(db, worker.id, start_date, end_date)
        
        print(f"\nPerformance:")
        print(f"  Total bookings: {performance.total_bookings}")
        print(f"  Average rating: {performance.average_rating}")
        print(f"  Review count: {performance.review_count}")
        print(f"  Recent coaching: {performance.recent_coaching}")
        
        print("\n[OK] Performance calculation successful!")
        
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
