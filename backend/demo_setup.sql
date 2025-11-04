-- =====================================================
-- ShoktiAI Demo Setup - 3 Customer Scenarios
-- =====================================================
-- User IDs:
-- 1. 229211b0-9cf4-4e36-b707-d593034bfb0f (Fatima - Regular, needs reminder)
-- 2. 201df462-8e81-475b-9b9b-2a2946218312 (Rahim - VIP, with promo)
-- 3. 55a91395-0760-4c57-a7db-ad97f2256917 (Nasrin - New, first reminder)
-- =====================================================

-- First, let's check if these users exist
-- If not, we'll insert them

-- =====================================================
-- SCENARIO 1: Fatima - Regular Customer (Due for Reminder)
-- =====================================================
-- Profile: Regular customer, last booking was 22 days ago for Home Cleaning
-- Expected Email: Standard reminder with personalized greeting

-- Update or Insert User
INSERT INTO users (id, email, name, type, city, area, language_preference, is_active, consent, created_at)
VALUES (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    'fatima.rahman@example.com',
    'Fatima Rahman',
    'customer',
    'Dhaka',
    'Dhanmondi',
    'bn',
    true,
    '{"email": true, "sms": true, "push": true, "marketing": true}'::jsonb,
    NOW() - INTERVAL '6 months'
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name,
    consent = EXCLUDED.consent;

-- Insert Customer Profile
INSERT INTO customers (id, typical_services, last_booking_at, created_at)
VALUES (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    ARRAY['a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d']::uuid[], -- Home Cleaning service
    NOW() - INTERVAL '22 days',
    NOW() - INTERVAL '6 months'
)
ON CONFLICT (id) DO UPDATE SET
    typical_services = EXCLUDED.typical_services,
    last_booking_at = EXCLUDED.last_booking_at;

-- Insert Past Booking (Home Cleaning - Completed 22 days ago)
INSERT INTO bookings (id, customer_id, service_id, status, scheduled_at, finished_at, created_at)
VALUES (
    gen_random_uuid(),
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', -- Home Cleaning
    'COMPLETED',
    NOW() - INTERVAL '22 days 3 hours',
    NOW() - INTERVAL '22 days',
    NOW() - INTERVAL '22 days'
);


-- =====================================================
-- SCENARIO 2: Rahim - VIP Customer (With Promo Code)
-- =====================================================
-- Profile: VIP customer, books frequently, last booking 21 days ago for AC Repair
-- Expected Email: Premium tone with exclusive promo code

-- Update or Insert User
INSERT INTO users (id, email, name, type, city, area, language_preference, is_active, consent, created_at)
VALUES (
    '201df462-8e81-475b-9b9b-2a2946218312',
    'rahim.ahmed@example.com',
    'Rahim Ahmed',
    'customer',
    'Dhaka',
    'Gulshan',
    'bn',
    true,
    '{"email": true, "sms": true, "push": true, "marketing": true}'::jsonb,
    NOW() - INTERVAL '2 years'
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name,
    consent = EXCLUDED.consent;

-- Insert Customer Profile (VIP with multiple typical services)
INSERT INTO customers (id, typical_services, last_booking_at, created_at)
VALUES (
    '201df462-8e81-475b-9b9b-2a2946218312',
    ARRAY['b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d']::uuid[], -- AC Repair + Home Cleaning
    NOW() - INTERVAL '21 days',
    NOW() - INTERVAL '2 years'
)
ON CONFLICT (id) DO UPDATE SET
    typical_services = EXCLUDED.typical_services,
    last_booking_at = EXCLUDED.last_booking_at;

-- Insert Multiple Past Bookings (to show VIP status)
INSERT INTO bookings (id, customer_id, service_id, status, scheduled_at, finished_at, created_at)
VALUES 
    (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'COMPLETED', NOW() - INTERVAL '21 days 2 hours', NOW() - INTERVAL '21 days', NOW() - INTERVAL '21 days'),
    (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 'COMPLETED', NOW() - INTERVAL '45 days', NOW() - INTERVAL '45 days', NOW() - INTERVAL '45 days'),
    (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'COMPLETED', NOW() - INTERVAL '68 days', NOW() - INTERVAL '68 days', NOW() - INTERVAL '68 days');


-- =====================================================
-- SCENARIO 3: Nasrin - New Customer (First Reminder)
-- =====================================================
-- Profile: New customer, first booking was 23 days ago for Plumbing
-- Expected Email: Welcoming tone, encouraging repeat booking

-- Update or Insert User
INSERT INTO users (id, email, name, type, city, area, language_preference, is_active, consent, created_at)
VALUES (
    '55a91395-0760-4c57-a7db-ad97f2256917',
    'nasrin.sultana@example.com',
    'Nasrin Sultana',
    'customer',
    'Dhaka',
    'Mirpur',
    'bn',
    true,
    '{"email": true, "sms": false, "push": true, "marketing": true}'::jsonb,
    NOW() - INTERVAL '1 month'
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name,
    consent = EXCLUDED.consent;

-- Insert Customer Profile (Only one service - new customer)
INSERT INTO customers (id, typical_services, last_booking_at, created_at)
VALUES (
    '55a91395-0760-4c57-a7db-ad97f2256917',
    ARRAY['c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f']::uuid[], -- Plumbing service
    NOW() - INTERVAL '23 days',
    NOW() - INTERVAL '1 month'
)
ON CONFLICT (id) DO UPDATE SET
    typical_services = EXCLUDED.typical_services,
    last_booking_at = EXCLUDED.last_booking_at;

-- Insert First Booking (Plumbing - Completed 23 days ago)
INSERT INTO bookings (id, customer_id, service_id, status, scheduled_at, finished_at, created_at)
VALUES (
    gen_random_uuid(),
    '55a91395-0760-4c57-a7db-ad97f2256917',
    'c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', -- Plumbing
    'COMPLETED',
    NOW() - INTERVAL '23 days 4 hours',
    NOW() - INTERVAL '23 days',
    NOW() - INTERVAL '23 days'
);


-- =====================================================
-- SERVICES SETUP (if they don't exist)
-- =====================================================

INSERT INTO services (id, name, name_bn, category, base_price, duration_minutes, is_active)
VALUES 
    ('a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 'Home Cleaning', 'হোম ক্লিনিং', 'home_services', 1500.00, 120, true),
    ('b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'AC Repair', 'এসি মেরামত', 'electrical', 2000.00, 90, true),
    ('c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 'Plumbing', 'প্লাম্বিং', 'plumbing', 1200.00, 60, true)
ON CONFLICT (id) DO NOTHING;


-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check the setup
SELECT 
    u.id,
    u.name,
    u.email,
    c.last_booking_at,
    c.typical_services,
    EXTRACT(DAY FROM (NOW() - c.last_booking_at)) as days_since_last_booking,
    COUNT(b.id) as total_bookings
FROM users u
JOIN customers c ON u.id = c.id
LEFT JOIN bookings b ON u.id = b.customer_id AND b.status = 'COMPLETED'
WHERE u.id IN (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    '201df462-8e81-475b-9b9b-2a2946218312',
    '55a91395-0760-4c57-a7db-ad97f2256917'
)
GROUP BY u.id, u.name, u.email, c.last_booking_at, c.typical_services
ORDER BY u.name;
