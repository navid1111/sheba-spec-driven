"""
Manual script to enable coaching consent for a test worker and trigger CoachNova.
"""
import asyncio
from uuid import UUID
from src.lib.db import SessionLocal
from src.models.users import User
from src.models.workers import Worker
from sqlalchemy import select
from datetime import datetime, timezone
import json

def enable_coaching_consent(worker_id: str):
    """Enable coaching consent for a worker."""
    db = SessionLocal()
    
    try:
        # Get user
        stmt = select(User).where(User.id == UUID(worker_id))
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"[FAIL] Worker not found: {worker_id}")
            return False
        
        print(f"Found worker: {user.name} ({user.email})")
        
        # Update consent
        consent = user.consent or {}
        consent['coaching_enabled'] = True
        consent['last_updated'] = datetime.now(timezone.utc).isoformat()
        user.consent = consent
        
        db.commit()
        
        print(f"[OK] Enabled coaching consent for {user.name}")
        print(f"   Consent: {json.dumps(user.consent, indent=2)}")
        return True
        
    finally:
        db.close()

def test_coachnova_trigger(worker_id: str):
    """Test CoachNova endpoint."""
    import httpx
    
    print(f"\n[TEST] Testing CoachNova endpoint for worker {worker_id}...")
    
    url = f"http://localhost:8000/internal/ai/coachnova/run-for-worker/{worker_id}"
    payload = {
        "dry_run": False,
        "force": True,  # Bypass frequency caps
        "locale": "bn"
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(payload, indent=2)}")
    
    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200 and response.json().get('success'):
            print("\n[OK] CoachNova triggered successfully!")
            print("[EMAIL] Check your email inbox for the coaching message!")
        else:
            print(f"\n[FAIL] CoachNova failed: {response.json()}")
            
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")

if __name__ == "__main__":
    # Worker ID from database query
    worker_id = "7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b"
    
    # Step 1: Enable coaching consent
    if enable_coaching_consent(worker_id):
        # Step 2: Test CoachNova endpoint
        test_coachnova_trigger(worker_id)
