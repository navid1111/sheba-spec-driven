-- Setup test user for SmartEngage campaign testing
-- User ID: 406bf423-f466-449f-8bdc-037c6f405b33

-- Step 1: Create/update user record
INSERT INTO users (id, phone, email, type, is_active, created_at, updated_at)
VALUES (
    '406bf423-f466-449f-8bdc-037c6f405b33'::uuid,
    '+8801712345678',
    'navidkamal@iut-dhaka.edu',  -- Your test email
    'CUSTOMER',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    email = 'navidkamal@iut-dhaka.edu',
    is_active = true,
    updated_at = NOW();

-- Step 2: Create/update customer record with marketing consent
INSERT INTO customers (id, preferences, typical_services, last_booking_at)
VALUES (
    '406bf423-f466-449f-8bdc-037c6f405b33'::uuid,
    '{"marketing_consent": true, "email_enabled": true, "sms_enabled": false, "preferred_contact_time": "morning"}'::jsonb,
    ARRAY['home_cleaning', 'plumbing']::varchar[],
    NOW() - INTERVAL '21 days'  -- Last booking 21 days ago (eligible for reminder)
)
ON CONFLICT (id) DO UPDATE SET
    preferences = '{"marketing_consent": true, "email_enabled": true, "sms_enabled": false, "preferred_contact_time": "morning"}'::jsonb,
    last_booking_at = NOW() - INTERVAL '21 days',
    typical_services = ARRAY['home_cleaning', 'plumbing']::varchar[];

-- Step 3: Ensure a service exists for the booking
INSERT INTO services (id, name, name_bn, category, description, base_price, duration_minutes, is_active, created_at, updated_at)
VALUES (
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d'::uuid,
    'Home Cleaning',
    'বাড়ি পরিষ্কার',
    'cleaning',
    'Professional home cleaning service',
    500.0,
    120,
    true,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name_bn = 'বাড়ি পরিষ্কার',
    is_active = true,
    updated_at = NOW();

-- Step 4: Create a COMPLETED booking 21 days ago
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
    'b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e'::uuid,
    '406bf423-f466-449f-8bdc-037c6f405b33'::uuid,
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d'::uuid,
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
    updated_at = NOW();

-- Step 5: Clear any recent AI messages (to pass frequency cap check)
-- Delete messages sent in last 24 hours to allow new campaign
DELETE FROM ai_messages 
WHERE user_id = '406bf423-f466-449f-8bdc-037c6f405b33'::uuid
  AND created_at > NOW() - INTERVAL '24 hours';

-- Verification queries
SELECT 'User record:' as info;
SELECT id, phone, email, type, is_active 
FROM users 
WHERE id = '406bf423-f466-449f-8bdc-037c6f405b33'::uuid;

SELECT 'Customer record:' as info;
SELECT id, preferences, typical_services, last_booking_at 
FROM customers 
WHERE id = '406bf423-f466-449f-8bdc-037c6f405b33'::uuid;

SELECT 'Recent bookings:' as info;
SELECT id, service_id, status, finished_at, 
       NOW() - finished_at as days_since_completion
FROM bookings 
WHERE customer_id = '406bf423-f466-449f-8bdc-037c6f405b33'::uuid
  AND status = 'COMPLETED'
ORDER BY finished_at DESC
LIMIT 5;

SELECT 'Recent AI messages (should be empty or >24h old):' as info;
SELECT id, agent_type, channel, sent_at, created_at,
       NOW() - created_at as age
FROM ai_messages 
WHERE user_id = '406bf423-f466-449f-8bdc-037c6f405b33'::uuid
ORDER BY created_at DESC
LIMIT 5;

-- Show eligibility check
SELECT 'Eligibility criteria check:' as info;
SELECT 
    u.id as user_id,
    u.email,
    c.preferences->>'marketing_consent' as has_consent,
    c.last_booking_at,
    NOW() - c.last_booking_at as days_since_booking,
    CASE 
        WHEN c.preferences->>'marketing_consent' = 'true' 
            AND c.last_booking_at IS NOT NULL
            AND (NOW() - c.last_booking_at) >= INTERVAL '20 days'
            AND (NOW() - c.last_booking_at) <= INTERVAL '22 days'
        THEN '✅ ELIGIBLE'
        ELSE '❌ NOT ELIGIBLE'
    END as eligibility_status
FROM users u
JOIN customers c ON c.id = u.id
WHERE u.id = '406bf423-f466-449f-8bdc-037c6f405b33'::uuid
  AND u.is_active = true;
