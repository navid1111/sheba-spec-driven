-- Demo Update Script for Existing Users
-- This script only adds bookings and service data to existing user IDs
-- Run this if users 229211b0-9cf4-4e36-b707-d593034bfb0f, 201df462-8e81-475b-9b9b-2a2946218312, 55a91395-0760-4c57-a7db-ad97f2256917 already exist

-- First, verify the users exist
SELECT id, name, email FROM users 
WHERE id IN (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    '201df462-8e81-475b-9b9b-2a2946218312',
    '55a91395-0760-4c57-a7db-ad97f2256917'
);

-- Insert Services (if not exist)
INSERT INTO services (id, name, category, description, created_at, updated_at)
VALUES 
    ('a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 'Home Cleaning', 'Cleaning', 'Professional home cleaning service', NOW(), NOW()),
    ('b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'AC Repair', 'Appliance', 'Air conditioner repair and maintenance', NOW(), NOW()),
    ('c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 'Plumbing', 'Home Services', 'Plumbing repair and installation', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Update or insert customer records
INSERT INTO customers (id, last_booking_at, preferences, created_at, updated_at)
VALUES 
    ('229211b0-9cf4-4e36-b707-d593034bfb0f', NOW() - INTERVAL '22 days', '{"preferred_time": "morning"}', NOW(), NOW()),
    ('201df462-8e81-475b-9b9b-2a2946218312', NOW() - INTERVAL '21 days', '{"vip": true, "preferred_time": "afternoon"}', NOW(), NOW()),
    ('55a91395-0760-4c57-a7db-ad97f2256917', NOW() - INTERVAL '23 days', '{"first_time_customer": true}', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    last_booking_at = EXCLUDED.last_booking_at,
    preferences = EXCLUDED.preferences,
    updated_at = NOW();

-- Delete existing bookings for these customers (for clean demo)
DELETE FROM bookings WHERE customer_id IN (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    '201df462-8e81-475b-9b9b-2a2946218312',
    '55a91395-0760-4c57-a7db-ad97f2256917'
);

-- Insert Bookings for Demo

-- Scenario 1: Fatima - Regular customer with 1 past Home Cleaning booking
INSERT INTO bookings (id, customer_id, service_id, status, booking_date, completed_at, created_at, updated_at)
VALUES 
    (gen_random_uuid(), '229211b0-9cf4-4e36-b707-d593034bfb0f', 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 
     'COMPLETED', NOW() - INTERVAL '22 days', NOW() - INTERVAL '22 days', NOW() - INTERVAL '22 days', NOW());

-- Scenario 2: Rahim - VIP customer with 3 bookings (AC Repair is the most recent)
INSERT INTO bookings (id, customer_id, service_id, status, booking_date, completed_at, created_at, updated_at)
VALUES 
    -- First booking: 60 days ago - Home Cleaning
    (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 
     'COMPLETED', NOW() - INTERVAL '60 days', NOW() - INTERVAL '60 days', NOW() - INTERVAL '60 days', NOW()),
    
    -- Second booking: 40 days ago - Plumbing
    (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 
     'COMPLETED', NOW() - INTERVAL '40 days', NOW() - INTERVAL '40 days', NOW() - INTERVAL '40 days', NOW()),
    
    -- Third booking: 21 days ago - AC Repair (most recent)
    (gen_random_uuid(), '201df462-8e81-475b-9b9b-2a2946218312', 'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 
     'COMPLETED', NOW() - INTERVAL '21 days', NOW() - INTERVAL '21 days', NOW() - INTERVAL '21 days', NOW());

-- Scenario 3: Nasrin - New customer with 1 booking (Plumbing, 23 days ago)
INSERT INTO bookings (id, customer_id, service_id, status, booking_date, completed_at, created_at, updated_at)
VALUES 
    (gen_random_uuid(), '55a91395-0760-4c57-a7db-ad97f2256917', 'c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 
     'COMPLETED', NOW() - INTERVAL '23 days', NOW() - INTERVAL '23 days', NOW() - INTERVAL '23 days', NOW());

-- Verification Query
SELECT 
    u.id,
    u.name,
    u.email,
    c.last_booking_at,
    COUNT(b.id) as total_bookings,
    MAX(b.completed_at) as last_completed_booking,
    s.name as last_service,
    EXTRACT(DAY FROM (NOW() - MAX(b.completed_at))) as days_since_last_booking
FROM users u
LEFT JOIN customers c ON u.id = c.id
LEFT JOIN bookings b ON u.id = b.customer_id AND b.status = 'COMPLETED'
LEFT JOIN services s ON b.service_id = s.id
WHERE u.id IN (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    '201df462-8e81-475b-9b9b-2a2946218312',
    '55a91395-0760-4c57-a7db-ad97f2256917'
)
GROUP BY u.id, u.name, u.email, c.last_booking_at, s.name
ORDER BY u.name;

-- Expected output:
-- | id (UUID)                            | name            | email                        | last_booking_at | total_bookings | last_service  | days_since |
-- |--------------------------------------|-----------------|------------------------------|-----------------|----------------|---------------|------------|
-- | 229211b0-9cf4-4e36-b707-d593034bfb0f | Fatima Rahman   | fatima.rahman@example.com    | 22 days ago     | 1              | Home Cleaning | 22         |
-- | 201df462-8e81-475b-9b9b-2a2946218312 | Rahim Ahmed     | rahim.ahmed@example.com      | 21 days ago     | 3              | AC Repair     | 21         |
-- | 55a91395-0760-4c57-a7db-ad97f2256917 | Nasrin Sultana  | nasrin.sultana@example.com   | 23 days ago     | 1              | Plumbing      | 23         |
