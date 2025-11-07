"""Check all CoachNova messages."""
from src.lib.db import SessionLocal
from src.models.ai_messages import AIMessage
from sqlalchemy import select, desc

db = SessionLocal()
result = db.execute(
    select(AIMessage)
    .where(AIMessage.agent_type == 'coachnova')
    .order_by(desc(AIMessage.created_at))
    .limit(10)
)
msgs = result.scalars().all()
print(f"Found {len(msgs)} CoachNova messages total")
for m in msgs:
    print(f"{m.id} - {m.delivery_status} - {m.created_at}")
db.close()
