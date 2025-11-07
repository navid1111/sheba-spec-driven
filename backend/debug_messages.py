"""Debug script to check CoachNova message status."""
from src.lib.db import SessionLocal
from src.models.ai_messages import AIMessage
from sqlalchemy import select, desc
from datetime import datetime, timedelta
import json

db = SessionLocal()
cutoff = datetime.now() - timedelta(minutes=10)
result = db.execute(
    select(AIMessage)
    .where(AIMessage.created_at >= cutoff)
    .where(AIMessage.agent_type == 'coachnova')
    .order_by(desc(AIMessage.created_at))
)
messages = result.scalars().all()

print(f"Found {len(messages)} CoachNova messages in last 10 minutes:\n")
for msg in messages:
    print(f"Message ID: {msg.id}")
    print(f"Status: {msg.delivery_status}")
    print(f"Channel: {msg.channel}")
    print(f"Worker: {msg.user_id}")
    print(f"Created: {msg.created_at}")
    print(f"Sent: {msg.sent_at}")
    if msg.metadata:
        print(f"Metadata: {json.dumps(msg.metadata, indent=2)}")
    print(f"Message text (first 200 chars):\n{msg.message_text[:200]}")
    print("\n" + "="*80 + "\n")

db.close()
