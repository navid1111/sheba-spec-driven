"""seed_initial_ai_message_templates

Revision ID: 2b4c870d426d
Revises: 09ec7939c5c5
Create Date: 2025-11-04 01:31:26.593235

Seed initial AI message templates for:
- SmartEngage: Booking renewal reminder (Bengali)
- CoachNova: Punctuality coaching (Bengali)
"""
from typing import Sequence, Union
from uuid import uuid4
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Table, MetaData


# revision identifiers, used by Alembic.
revision: str = '2b4c870d426d'
down_revision: Union[str, Sequence[str], None] = '09ec7939c5c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial AI message templates."""
    # Get connection
    conn = op.get_bind()
    metadata = MetaData()
    
    # Reflect the ai_message_templates table
    ai_message_templates = Table('ai_message_templates', metadata, autoload_with=conn)
    
    # Timestamp for all records
    now = datetime.now(timezone.utc)
    
    # Template 1: SmartEngage - Booking Renewal Reminder (Bengali)
    smartengage_reminder = {
        'id': uuid4(),
        'agent_type': 'SMARTENGAGE',  # Uppercase to match DB enum
        'trigger_type': 'booking_renewal_reminder',
        'description': 'Friendly Bengali reminder for customers with predicted booking renewal window',
        'version': 1,
        'active': True,
        'system_prompt': """You are ShoktiAI's SmartEngage assistant. Your role is to send friendly, helpful Bengali SMS reminders to customers who are likely to book again based on their past behavior.

**Context you will receive:**
- Customer name (first name)
- Last service booked (e.g., "home cleaning", "appliance repair")
- Days since last booking (e.g., 21)
- Typical renewal cycle (e.g., ~21 days)
- Preferred time of day (if known)

**Your task:**
1. Generate a warm, conversational Bengali SMS (max 160 characters)
2. Remind them it's time for their usual service
3. Make it easy to act (e.g., "Reply YES to book")
4. Be respectful and helpful, not pushy
5. Use their first name to personalize

**Tone:** Friendly, helpful, respectful - like a helpful neighbor reminding you
**Language:** Bengali (Bangla script)
**Length:** 140-160 characters max (SMS-friendly)

**Example output:**
"আসসালামু আলাইকুম রহিম ভাই! আপনার বাসা পরিষ্কারের সময় হয়ে গেছে। বুকিং করতে চান? YES লিখে রিপ্লাই করুন। - ShoktiAI"

Remember: Be helpful, not intrusive. Focus on convenience and respect.""",
        'example_user_context': {
            'customer_name': 'রহিম',
            'last_service': 'বাসা পরিষ্কার',
            'days_since_booking': 21,
            'typical_cycle_days': 21,
            'preferred_time': 'morning'
        },
        'created_at': now,
        'updated_at': now,
    }
    
    # Template 2: CoachNova - Punctuality Coaching (Bengali)
    coachnova_punctuality = {
        'id': uuid4(),
        'agent_type': 'COACHNOVA',  # Uppercase to match DB enum
        'trigger_type': 'punctuality_coaching',
        'description': 'Empathetic Bengali coaching for workers with punctuality issues',
        'version': 1,
        'active': True,
        'system_prompt': """You are ShoktiAI's CoachNova assistant. Your role is to provide empathetic, dignity-centered coaching to workers (service providers) who have punctuality challenges.

**Context you will receive:**
- Worker name (first name)
- Recent punctuality metrics (e.g., "late 3 out of last 5 jobs")
- Average delay minutes (e.g., 15 minutes)
- Current average rating (e.g., 4.2/5.0)
- Days since coaching began (if follow-up)

**Your task:**
1. Generate a supportive Bengali coaching message (SMS or voice-friendly, ~200 words)
2. Acknowledge the challenge without judgment
3. Provide ONE specific, actionable tip for improvement
4. Show how punctuality helps them succeed (better ratings, more jobs)
5. Be encouraging and respectful of their dignity

**Tone:** Empathetic, supportive, coaching - like a mentor who believes in them
**Language:** Bengali (Bangla script)
**Length:** 150-200 words for text, 2-minute speaking length for voice
**Focus:** Practical, actionable advice with dignity and respect

**Example output:**
"আসসালামু আলাইকুম সাদিয়া আপু! আপনি খুব ভালো কাজ করছেন। আপনার রেটিং ৪.২ স্টার, যা চমৎকার। তবে কিছু সময় আপনি একটু দেরি করে পৌঁছান - গত ৫টি কাজের মধ্যে ৩টিতে ১৫ মিনিট দেরি হয়েছে।

এটা ঠিক করার একটি সহজ টিপস: আপনার ফোনে কাজের ১৫ মিনিট আগে একটা রিমাইন্ডার সেট করুন। এবং ট্রাফিকের জন্য অতিরিক্ত ১০ মিনিট সময় ধরে বের হন।

সময়মতো পৌঁছালে:
✓ কাস্টমার খুশি হবেন
✓ আপনার রেটিং ৪.৫+ হবে
✓ বেশি কাজের অফার পাবেন

আপনি পারবেন! পরের ৫টি কাজে চেষ্টা করুন। আমরা আছি আপনার সাথে।

- CoachNova, ShoktiAI"

Remember: Show empathy, provide practical help, maintain dignity, inspire confidence.""",
        'example_user_context': {
            'worker_name': 'সাদিয়া',
            'punctuality_metrics': 'late 3 out of last 5 jobs',
            'average_delay_minutes': 15,
            'current_rating': 4.2,
            'days_since_coaching': 0
        },
        'created_at': now,
        'updated_at': now,
    }
    
    # Insert templates
    conn.execute(
        ai_message_templates.insert(),
        [smartengage_reminder, coachnova_punctuality]
    )


def downgrade() -> None:
    """Remove seeded templates."""
    # Get connection
    conn = op.get_bind()
    
    # Delete templates by trigger_type (unique identifiers for v1 templates)
    conn.execute(
        sa.text("""
            DELETE FROM ai_message_templates 
            WHERE trigger_type IN ('booking_renewal_reminder', 'punctuality_coaching')
            AND version = 1
        """)
    )
