"""
Setup test user for SmartEngage campaign testing.
User ID: 406bf423-f466-449f-8bdc-037c6f405b33
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import text

from src.lib.db import get_db
from src.lib.settings import settings

# Test user ID
TEST_USER_ID = UUID("406bf423-f466-449f-8bdc-037c6f405b33")
TEST_SERVICE_ID = UUID("a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d")
TEST_BOOKING_ID = UUID("b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e")

def setup_test_user():
    """Setup test user with proper eligibility criteria."""
    db = next(get_db())
    
    try:
        print(f"Setting up test user: {TEST_USER_ID}")
        print(f"Test email: navidkamal@iut-dhaka.edu")
        print()
        
        # Step 1: Create/update user record
        print("1. Creating/updating user record...")
        db.execute(text("""
            INSERT INTO users (id, phone, email, name, type, language_preference, consent, is_active, created_at, updated_at)
            VALUES (
                :user_id,
                '+8801712345678',
                'navidkamal@iut-dhaka.edu',
                'Navid Kamal',
                'CUSTOMER',
                'bn',
                '{"push": true, "sms": false, "whatsapp": false, "marketing_consent": true, "email_enabled": true}'::jsonb,
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                email = 'navidkamal@iut-dhaka.edu',
                name = 'Navid Kamal',
                consent = '{"push": true, "sms": false, "whatsapp": false, "marketing_consent": true, "email_enabled": true}'::jsonb,
                is_active = true,
                updated_at = NOW()
        """), {"user_id": TEST_USER_ID})
        db.commit()
        print("   ✅ User created/updated with marketing consent")
        
        # Step 2: Create/update customer record
        print("2. Creating/updating customer record...")
        db.execute(text("""
            INSERT INTO customers (id, typical_services, last_booking_at)
            VALUES (
                :user_id,
                ARRAY['home_cleaning', 'plumbing']::varchar[],
                NOW() - INTERVAL '21 days'
            )
            ON CONFLICT (id) DO UPDATE SET
                last_booking_at = NOW() - INTERVAL '21 days',
                typical_services = ARRAY['home_cleaning', 'plumbing']::varchar[]
        """), {"user_id": TEST_USER_ID})
        db.commit()
        print("   ✅ Customer record created/updated")
        
        # Step 3: Create service
        print("3. Creating/updating service...")
        db.execute(text("""
            INSERT INTO services (id, name, name_bn, category, description, base_price, duration_minutes, active)
            VALUES (
                :service_id,
                'Home Cleaning',
                'বাড়ি পরিষ্কার',
                'CLEANING',
                'Professional home cleaning service',
                500.0,
                120,
                true
            )
            ON CONFLICT (id) DO UPDATE SET
                name_bn = 'বাড়ি পরিষ্কার',
                active = true
        """), {"service_id": TEST_SERVICE_ID})
        db.commit()
        print("   ✅ Service created/updated")
        
        # Step 4: Create completed booking 21 days ago
        print("4. Creating completed booking from 21 days ago...")
        db.execute(text("""
            INSERT INTO bookings (
                id, 
                customer_id, 
                service_id, 
                status, 
                scheduled_at, 
                finished_at, 
                total_price, 
                payment_status,
                created_at,
                updated_at
            )
            VALUES (
                :booking_id,
                :customer_id,
                :service_id,
                'COMPLETED',
                NOW() - INTERVAL '21 days',
                NOW() - INTERVAL '21 days',
                500.0,
                'PAID',
                NOW() - INTERVAL '21 days',
                NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                status = 'COMPLETED',
                finished_at = NOW() - INTERVAL '21 days',
                updated_at = NOW()
        """), {
            "booking_id": TEST_BOOKING_ID,
            "customer_id": TEST_USER_ID,
            "service_id": TEST_SERVICE_ID
        })
        db.commit()
        print("   ✅ Booking created/updated")
        
        # Step 5: Clear recent AI messages
        print("5. Clearing recent AI messages (frequency cap check)...")
        result = db.execute(text("""
            DELETE FROM ai_messages 
            WHERE user_id = :user_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """), {"user_id": TEST_USER_ID})
        db.commit()
        print(f"   ✅ Deleted {result.rowcount} recent messages")
        
        # Verification
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)
        
        # Check user
        user = db.execute(text("""
            SELECT id, phone, email, type, is_active 
            FROM users 
            WHERE id = :user_id
        """), {"user_id": TEST_USER_ID}).fetchone()
        print(f"\n📧 User: {user.email} ({user.type})")
        print(f"   Active: {user.is_active}")
        
        # Check customer
        customer = db.execute(text("""
            SELECT id, typical_services, last_booking_at 
            FROM customers 
            WHERE id = :user_id
        """), {"user_id": TEST_USER_ID}).fetchone()
        
        # Check user consent
        user_consent = db.execute(text("""
            SELECT consent
            FROM users
            WHERE id = :user_id
        """), {"user_id": TEST_USER_ID}).fetchone()
        
        print(f"\n👤 Customer:")
        print(f"   Marketing Consent: {user_consent.consent.get('marketing_consent')}")
        print(f"   Email Enabled: {user_consent.consent.get('email_enabled')}")
        print(f"   Last Booking: {customer.last_booking_at}")
        print(f"   Days Since Booking: {(datetime.now(timezone.utc) - customer.last_booking_at.replace(tzinfo=timezone.utc)).days}")
        
        # Check bookings
        bookings = db.execute(text("""
            SELECT id, service_id, status, finished_at
            FROM bookings 
            WHERE customer_id = :customer_id
              AND status = 'COMPLETED'
            ORDER BY finished_at DESC
            LIMIT 5
        """), {"customer_id": TEST_USER_ID}).fetchall()
        print(f"\n📅 Recent Completed Bookings: {len(bookings)}")
        for booking in bookings:
            days_ago = (datetime.now(timezone.utc) - booking.finished_at.replace(tzinfo=timezone.utc)).days
            print(f"   - {booking.id}: {days_ago} days ago")
        
        # Check AI messages
        messages = db.execute(text("""
            SELECT id, agent_type, channel, sent_at, created_at
            FROM ai_messages 
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 5
        """), {"user_id": TEST_USER_ID}).fetchall()
        print(f"\n💬 Recent AI Messages: {len(messages)}")
        if messages:
            for msg in messages:
                hours_ago = (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                print(f"   - {msg.id}: {msg.agent_type} via {msg.channel} ({hours_ago:.1f}h ago)")
        else:
            print("   (none - passed frequency cap check ✅)")
        
        # Eligibility check
        eligibility = db.execute(text("""
            SELECT 
                u.id as user_id,
                u.email,
                u.consent->>'marketing_consent' as has_consent,
                c.last_booking_at,
                EXTRACT(DAY FROM NOW() - c.last_booking_at) as days_since_booking,
                CASE 
                    WHEN u.consent->>'marketing_consent' = 'true' 
                        AND c.last_booking_at IS NOT NULL
                        AND (NOW() - c.last_booking_at) >= INTERVAL '20 days'
                        AND (NOW() - c.last_booking_at) <= INTERVAL '22 days'
                    THEN true
                    ELSE false
                END as is_eligible
            FROM users u
            JOIN customers c ON c.id = u.id
            WHERE u.id = :user_id
              AND u.is_active = true
        """), {"user_id": TEST_USER_ID}).fetchone()
        
        print(f"\n🎯 ELIGIBILITY CHECK:")
        print(f"   Marketing Consent: {'✅' if eligibility.has_consent == 'true' else '❌'}")
        print(f"   Days Since Booking: {int(eligibility.days_since_booking)} (target: 20-22)")
        print(f"   Active User: ✅")
        print(f"   No Recent Messages: ✅")
        print(f"\n   {'✅ ELIGIBLE FOR CAMPAIGN' if eligibility.is_eligible else '❌ NOT ELIGIBLE'}")
        
        print("\n" + "="*60)
        print("✅ Test user setup complete!")
        print("="*60)
        print(f"\nYou can now test the campaign with:")
        print(f"  User ID: {TEST_USER_ID}")
        print(f"  Email: navidkamal@iut-dhaka.edu")
        print(f"\nRun the campaign:")
        print("  POST /internal/ai/smartengage/run-segment")
        print("  Body: {\"booking_cadence_days\": 21}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error setting up test user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    setup_test_user()
