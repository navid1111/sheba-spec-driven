"""
Debug script to test SmartEngage campaign with detailed logging.
"""
import asyncio
import logging
from uuid import UUID

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.lib.db import SessionLocal
from src.ai.smartengage import get_smartengage_orchestrator

async def test_campaign():
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print("Testing SmartEngage Campaign - Debug Mode")
        print("="*60 + "\n")
        
        orchestrator = get_smartengage_orchestrator(db)
        customer_id = UUID('406bf423-f466-449f-8bdc-037c6f405b33')
        
        print(f"Customer ID: {customer_id}")
        print(f"\nCalling generate_and_send_reminder()...\n")
        
        result = await orchestrator.generate_and_send_reminder(
            customer_id=customer_id,
            promo_code="TEST20"
        )
        
        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(f"Success: {result['success']}")
        print(f"Correlation ID: {result['correlation_id']}")
        
        if 'message_id' in result:
            print(f"Message ID: {result['message_id']}")
        
        if 'reason' in result:
            print(f"Reason: {result['reason']}")
            
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_campaign())
