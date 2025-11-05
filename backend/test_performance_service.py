"""
Quick test script to validate PerformanceService with seeded worker data.
"""
import asyncio
from uuid import UUID
from src.lib.db import get_db
from src.services.performance_service import PerformanceService

# Seeded worker IDs from run_worker_setup.py
WORKER_JAHANGIR_ID = UUID("a0b1c2d3-e4f5-46a7-98b9-0c1d2e3f4a5b")  # 5 late arrivals
WORKER_SADIA_ID = UUID("7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b")  # 3 late arrivals
WORKER_FEROZ_ID = UUID("9d4e3c2b-1a0f-48b7-bc3a-2a1b0c9d8e7f")  # 0 late arrivals


def test_performance_service():
    """Test PerformanceService.get_signals() with seeded workers."""
    print("🧪 Testing PerformanceService with seeded workers...\n")
    
    # Note: This uses sync get_db, so we'll use sync version
    db = next(get_db())
    
    try:
        # Test Jahangir (5 late arrivals - should be eligible)
        print("1️⃣  Testing Jahangir (5 late arrivals)...")
        signals = PerformanceService.get_signals_sync(WORKER_JAHANGIR_ID, db)
        print(f"   Late arrivals: {signals['late_arrivals_last_7_days']}")
        print(f"   Eligible for coaching: {signals['eligible_for_coaching']}")
        print(f"   Issues: {signals['issues']}")
        assert signals['eligible_for_coaching'] is True, "Jahangir should be eligible"
        assert 'late_arrivals' in signals['issues'], "Should flag late arrivals"
        print("   ✅ PASS\n")
        
        # Test Sadia (3 late arrivals - should be eligible at threshold)
        print("2️⃣  Testing Sadia (3 late arrivals)...")
        signals = PerformanceService.get_signals_sync(WORKER_SADIA_ID, db)
        print(f"   Late arrivals: {signals['late_arrivals_last_7_days']}")
        print(f"   Eligible for coaching: {signals['eligible_for_coaching']}")
        print(f"   Issues: {signals['issues']}")
        assert signals['eligible_for_coaching'] is True, "Sadia should be eligible"
        assert 'late_arrivals' in signals['issues'], "Should flag late arrivals"
        print("   ✅ PASS\n")
        
        # Test Feroz (0 late arrivals - should NOT be eligible)
        print("3️⃣  Testing Feroz (0 late arrivals)...")
        signals = PerformanceService.get_signals_sync(WORKER_FEROZ_ID, db)
        print(f"   Late arrivals: {signals['late_arrivals_last_7_days']}")
        print(f"   Eligible for coaching: {signals['eligible_for_coaching']}")
        print(f"   Issues: {signals['issues']}")
        assert signals['eligible_for_coaching'] is False, "Feroz should NOT be eligible"
        assert len(signals['issues']) == 0, "Should have no issues"
        print("   ✅ PASS\n")
        
        print("🎉 All PerformanceService tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_performance_service()
