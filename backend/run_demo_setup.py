"""
Demo Update Script - Execute SQL for existing users
Run this to set up bookings and services for the 3 demo customers
"""
import os
import psycopg2
from datetime import datetime, timedelta

# Database connection string
DATABASE_URL = "postgresql://default:3F5SCcDAbWYM@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require"

def run_demo_setup():
    """Execute demo setup SQL commands"""
    print("🚀 Starting demo setup...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("✅ Connected to database")
        
        # Step 1: Verify users exist
        print("\n📋 Step 1: Verifying users exist...")
        cur.execute("""
            SELECT id, name, email FROM users 
            WHERE id IN (
                '229211b0-9cf4-4e36-b707-d593034bfb0f',
                '201df462-8e81-475b-9b9b-2a2946218312',
                '55a91395-0760-4c57-a7db-ad97f2256917'
            )
        """)
        users = cur.fetchall()
        if len(users) == 3:
            print(f"✅ Found all 3 users:")
            for user in users:
                print(f"   - {user[1]} ({user[2]})")
        else:
            print(f"⚠️  Warning: Only found {len(users)} users. Expected 3.")
            for user in users:
                print(f"   - {user[1]} ({user[2]})")
        
        # Step 2: Insert Services
        print("\n📋 Step 2: Creating services...")
        cur.execute("""
            INSERT INTO services (id, name, name_bn, category, description, base_price, duration_minutes, active)
            VALUES 
                ('a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 'Home Cleaning', 'হোম ক্লিনিং', 'CLEANING', 'Professional home cleaning service', 1500.00, 120, true),
                ('b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'AC Repair', 'এসি মেরামত', 'ELECTRICAL', 'Air conditioner repair and maintenance', 2000.00, 90, true),
                ('c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 'Plumbing', 'প্লাম্বিং', 'OTHER', 'Plumbing repair and installation', 1200.00, 60, true)
            ON CONFLICT (id) DO NOTHING
        """)
        conn.commit()
        print("✅ Services created/verified")
        
        # Step 3: Update customer records
        print("\n📋 Step 3: Updating customer records...")
        cur.execute("""
            INSERT INTO customers (id, last_booking_at, typical_services)
            VALUES 
                ('229211b0-9cf4-4e36-b707-d593034bfb0f', NOW() - INTERVAL '22 days', ARRAY['home_cleaning']::varchar[]),
                ('201df462-8e81-475b-9b9b-2a2946218312', NOW() - INTERVAL '21 days', ARRAY['ac_repair', 'home_cleaning']::varchar[]),
                ('55a91395-0760-4c57-a7db-ad97f2256917', NOW() - INTERVAL '23 days', ARRAY['plumbing']::varchar[])
            ON CONFLICT (id) DO UPDATE SET
                last_booking_at = EXCLUDED.last_booking_at,
                typical_services = EXCLUDED.typical_services
        """)
        conn.commit()
        print("✅ Customer records updated")
        
        # Step 3.5: Enable marketing consent for all 3 users
        print("\n📋 Step 3.5: Enabling marketing consent...")
        cur.execute("""
            UPDATE users 
            SET consent = jsonb_set(
                jsonb_set(
                    COALESCE(consent, '{}'::jsonb),
                    '{marketing_consent}',
                    'true'::jsonb
                ),
                '{email_enabled}',
                'true'::jsonb
            )
            WHERE id IN (
                '229211b0-9cf4-4e36-b707-d593034bfb0f',
                '201df462-8e81-475b-9b9b-2a2946218312',
                '55a91395-0760-4c57-a7db-ad97f2256917'
            )
        """)
        affected = cur.rowcount
        conn.commit()
        print(f"✅ Marketing consent enabled for {affected} users")
        
        # Step 4: Clean old bookings
        print("\n📋 Step 4: Cleaning old bookings for demo...")
        cur.execute("""
            DELETE FROM bookings WHERE customer_id IN (
                '229211b0-9cf4-4e36-b707-d593034bfb0f',
                '201df462-8e81-475b-9b9b-2a2946218312',
                '55a91395-0760-4c57-a7db-ad97f2256917'
            )
        """)
        deleted_count = cur.rowcount
        conn.commit()
        print(f"✅ Deleted {deleted_count} old bookings")
        
        # Step 5: Insert demo bookings
        print("\n📋 Step 5: Creating demo bookings...")
        
        # Scenario 1: Fatima - 1 booking
        cur.execute("""
            INSERT INTO bookings (id, customer_id, service_id, status, scheduled_at, finished_at, total_price, payment_status, created_at, updated_at)
            VALUES 
                (gen_random_uuid(), '229211b0-9cf4-4e36-b707-d593034bfb0f', 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 
                 'COMPLETED', NOW() - INTERVAL '22 days', NOW() - INTERVAL '22 days', 1500.00, 'PAID', NOW() - INTERVAL '22 days', NOW())
        """)
        print("   ✅ Fatima: 1 Home Cleaning booking (22 days ago)")
        
        # Scenario 2: Rahim - 3 bookings
        cur.execute("""
            INSERT INTO bookings (id, customer_id, service_id, status, scheduled_at, finished_at, total_price, payment_status, created_at, updated_at)
            VALUES 
                (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 
                 'COMPLETED', NOW() - INTERVAL '60 days', NOW() - INTERVAL '60 days', 1500.00, 'PAID', NOW() - INTERVAL '60 days', NOW()),
                
                (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 
                 'COMPLETED', NOW() - INTERVAL '40 days', NOW() - INTERVAL '40 days', 1200.00, 'PAID', NOW() - INTERVAL '40 days', NOW()),
                
                (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 
                 'COMPLETED', NOW() - INTERVAL '21 days', NOW() - INTERVAL '21 days', 2000.00, 'PAID', NOW() - INTERVAL '21 days', NOW())
        """)
        print("   ✅ Rahim: 3 bookings (VIP customer, last AC Repair 21 days ago)")
        
        # Scenario 3: Nasrin - 1 booking
        cur.execute("""
            INSERT INTO bookings (id, customer_id, service_id, status, scheduled_at, finished_at, total_price, payment_status, created_at, updated_at)
            VALUES 
                (gen_random_uuid(), '55a91395-0760-4c57-a7db-ad97f2256917', 'c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 
                 'COMPLETED', NOW() - INTERVAL '23 days', NOW() - INTERVAL '23 days', 1200.00, 'PAID', NOW() - INTERVAL '23 days', NOW())
        """)
        print("   ✅ Nasrin: 1 Plumbing booking (23 days ago, new customer)")
        
        conn.commit()
        print("\n✅ All bookings created successfully!")
        
        # Step 6: Verification
        print("\n📋 Step 6: Verification - Customer Summary")
        print("=" * 100)
        cur.execute("""
            SELECT 
                u.name,
                u.email,
                COUNT(b.id) as total_bookings,
                MAX(s.name) as last_service,
                EXTRACT(DAY FROM (NOW() - MAX(b.finished_at)))::integer as days_since_last
            FROM users u
            LEFT JOIN customers c ON u.id = c.id
            LEFT JOIN bookings b ON u.id = b.customer_id AND b.status = 'COMPLETED'
            LEFT JOIN services s ON b.service_id = s.id
            WHERE u.id IN (
                '229211b0-9cf4-4e36-b707-d593034bfb0f',
                '201df462-8e81-475b-9b9b-2a2946218312',
                '55a91395-0760-4c57-a7db-ad97f2256917'
            )
            GROUP BY u.id, u.name, u.email
            ORDER BY u.name
        """)
        
        results = cur.fetchall()
        print(f"{'Customer':<20} {'Email':<30} {'Bookings':<10} {'Last Service':<15} {'Days Ago':<10}")
        print("-" * 100)
        for row in results:
            print(f"{row[0]:<20} {row[1]:<30} {row[2]:<10} {row[3]:<15} {row[4]:<10}")
        print("=" * 100)
        
        # Close connection
        cur.close()
        conn.close()
        
        print("\n🎉 Demo setup completed successfully!")
        print("\n📝 Next Steps:")
        print("   1. Check DEMO_GUIDE.md for API request examples")
        print("   2. Use the cURL commands or Postman to test")
        print("   3. See AI-generated Bengali emails in action!")
        print("\n🚀 Ready for demo presentation!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    run_demo_setup()
