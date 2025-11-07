"""Test workers listing directly without HTTP."""
from src.lib.db import SessionLocal
from src.api.routes.admin_workers import list_workers

db = SessionLocal()

try:
    print("Testing list_workers function directly...")
    
    # Call the function directly
    result = list_workers(
        page=1,
        page_size=5,
        low_rating=None,
        high_workload=None,
        at_risk=None,
        active_only=True,
        days=30,
        db=db,
    )
    
    print(f"\n[OK] Function executed successfully!")
    print(f"Total workers: {result.total}")
    print(f"Workers returned: {len(result.workers)}")
    print(f"Has next: {result.has_next}")
    
    if result.workers:
        print(f"\nFirst worker:")
        worker = result.workers[0]
        print(f"  ID: {worker.id}")
        print(f"  Name: {worker.name}")
        print(f"  Performance: {worker.performance}")
        
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
