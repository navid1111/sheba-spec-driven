# ShoktiAI Platform - Demo Guide
## 3 Customer Scenarios with AI-Generated Bengali Emails

---

## Setup Instructions

### 1. Run the SQL Setup
```bash
# Connect to your Neon database and run:
psql "postgresql://default:3F5SCcDAbWYM@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require" -f demo_setup.sql
```

### 2. Ensure Backend is Running
```bash
cd backend
uvicorn src.api.app:app --reload --port 8000
```

---

## Scenario 1: kamalnavid50 - Regular Customer
**Email**: kamalnavid50@gmail.com  
**User ID**: `229211b0-9cf4-4e36-b707-d593034bfb0f`  
**Profile**: Regular customer, last booked Home Cleaning 22 days ago  
**Expected Message**: Standard friendly reminder in Bengali

### API Request: Send Single Reminder

**Endpoint**: `POST /admin/smartengage/send-single`

**Request Body**:
```json
{
  "customer_id": "229211b0-9cf4-4e36-b707-d593034bfb0f",
  "message_type": "reminder",
  "service_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "promo_code": null,
  "ttl_hours": 48
}
```

**cURL Command**:
```bash
curl -X POST http://localhost:8000/admin/smartengage/send-single \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "229211b0-9cf4-4e36-b707-d593034bfb0f",
    "message_type": "reminder",
    "service_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "promo_code": null,
    "ttl_hours": 48
  }'
```

### Expected Email Content:
**Subject**: আপনার হোম ক্লিনিং সার্ভিসের সময় হয়েছে 🏠

**Body** (Bengali, AI-generated):
```
প্রিয় kamalnavid50,

আশা করি আপনি ভালো আছেন! 

লক্ষ্য করলাম যে আপনি আমাদের হোম ক্লিনিং সার্ভিস ২২ দিন আগে নিয়েছিলেন। 
আপনার বাড়ি পরিষ্কার রাখতে আবার সার্ভিস নেওয়ার সময় হয়ে গেছে।

✨ এখনই বুক করুন এবং একটি পরিচ্ছন্ন, স্বাস্থ্যকর ঘর উপভোগ করুন!

[বুক করতে এখানে ক্লিক করুন]
https://app.sheba.xyz/book?token=eyJhbGci...

ধন্যবাদ,
ShoktiAI Team
```

### Expected API Response:
```json
{
  "success": true,
  "message_id": "uuid-here",
  "customer_id": "229211b0-9cf4-4e36-b707-d593034bfb0f",
  "correlation_id": "uuid-here",
  "channel": "EMAIL",
  "message": "Reminder sent successfully"
}
```

---

## Scenario 2: navidkamal5688 - VIP Customer
**Email**: navidkamal5688@gmail.com  
**User ID**: `201df462-8e81-475b-9b9b-2a2946218312`  
**Profile**: VIP customer with 3 bookings, last booked Plumbing 21 days ago  
**Expected Message**: Premium tone with exclusive 20% promo code

### API Request: Send Single Reminder with Promo

**Endpoint**: `POST /admin/smartengage/send-single`

**Request Body**:
```json
{
  "customer_id": "201df462-8e81-475b-9b9b-2a2946218312",
  "message_type": "reminder",
  "service_id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
  "promo_code": "VIP20",
  "ttl_hours": 72
}
```

**cURL Command**:
```bash
curl -X POST http://localhost:8000/admin/smartengage/send-single \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "201df462-8e81-475b-9b9b-2a2946218312",
    "message_type": "reminder",
    "service_id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    "promo_code": "VIP20",
    "ttl_hours": 72
  }'
```

### Expected Email Content:
**Subject**: বিশেষ অফার: আপনার প্লাম্বিং সার্ভিসের জন্য ২০% ছাড়! 🔧

**Body** (Bengali, AI-generated with premium tone):
```
প্রিয় navidkamal5688 সাহেব,

আপনার প্রতি আমাদের বিশেষ কৃতজ্ঞতা! আপনি আমাদের একজন মূল্যবান গ্রাহক।

আপনি ২১ দিন আগে আমাদের প্লাম্বিং সার্ভিস নিয়েছিলেন। বাড়ির প্লাম্বিং সমস্যা 
প্রতিরোধে নিয়মিত চেক-আপ অত্যন্ত জরুরি।

🎁 আপনার জন্য বিশেষ অফার: ২০% ছাড়!
প্রোমো কোড: VIP20

সমস্যামুক্ত বাড়ি নিশ্চিত করতে এখনই বুক করুন।

[এখনই বুক করুন - ৭২ ঘন্টা অফার]
https://app.sheba.xyz/book?token=eyJhbGci...&promo=VIP20

আপনার সেবায় সর্বদা,
ShoktiAI Team
```

### Expected API Response:
```json
{
  "success": true,
  "message_id": "uuid-here",
  "customer_id": "201df462-8e81-475b-9b9b-2a2946218312",
  "correlation_id": "uuid-here",
  "channel": "EMAIL",
  "promo_code": "VIP20",
  "message": "Reminder with promo sent successfully"
}
```

---

## Scenario 3: navidkamal568 - New Customer
**Email**: navidkamal568@gmail.com  
**User ID**: `55a91395-0760-4c57-a7db-ad97f2256917`  
**Profile**: New customer, first booking (Plumbing) was 23 days ago  
**Expected Message**: Welcoming tone, encouraging repeat service

### API Request: Send Single Reminder

**Endpoint**: `POST /admin/smartengage/send-single`

**Request Body**:
```json
{
  "customer_id": "55a91395-0760-4c57-a7db-ad97f2256917",
  "message_type": "reminder",
  "service_id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
  "promo_code": "WELCOME10",
  "ttl_hours": 48
}
```

**cURL Command**:
```bash
curl -X POST http://localhost:8000/admin/smartengage/send-single \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "55a91395-0760-4c57-a7db-ad97f2256917",
    "message_type": "reminder",
    "service_id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    "promo_code": "WELCOME10",
    "ttl_hours": 48
  }'
```

### Expected Email Content:
**Subject**: আপনার প্লাম্বিং সার্ভিস - আবার প্রয়োজন হতে পারে 🔧

**Body** (Bengali, AI-generated with welcoming tone):
```
প্রিয় navidkamal568,

ShoktiAI-এ স্বাগতম! আশা করি আমাদের প্লাম্বিং সার্ভিসে আপনি সন্তুষ্ট ছিলেন।

আপনি ২৩ দিন আগে প্রথমবার আমাদের সার্ভিস নিয়েছিলেন। বাড়ির প্লাম্বিং 
সমস্যা প্রতিরোধে নিয়মিত চেক-আপ খুবই গুরুত্বপূর্ণ।

🎉 নতুন গ্রাহক হিসেবে আপনার জন্য ১০% ছাড়!
প্রোমো কোড: WELCOME10

আমরা আপনার বিশ্বস্ত সেবা প্রদানকারী হতে চাই।

[সহজে বুক করুন]
https://app.sheba.xyz/book?token=eyJhbGci...&promo=WELCOME10

ধন্যবাদ ও শুভকামনা,
ShoktiAI Team
```

### Expected API Response:
```json
{
  "success": true,
  "message_id": "uuid-here",
  "customer_id": "55a91395-0760-4c57-a7db-ad97f2256917",
  "correlation_id": "uuid-here",
  "channel": "EMAIL",
  "promo_code": "WELCOME10",
  "message": "Reminder sent successfully"
}
```

---

## Bulk Campaign Example
Send to all 3 customers at once

**Endpoint**: `POST /admin/smartengage/send-bulk`

**Request Body**:
```json
{
  "customer_ids": [
    "229211b0-9cf4-4e36-b707-d593034bfb0f",
    "201df462-8e81-475b-9b9b-2a2946218312",
    "55a91395-0760-4c57-a7db-ad97f2256917"
  ],
  "message_type": "reminder",
  "booking_cadence_days": 21,
  "service_id": null,
  "promo_code": "DEMO15",
  "batch_size": 10,
  "bypass_frequency_caps": true
}
```

**cURL Command**:
```bash
curl -X POST http://localhost:8000/admin/smartengage/send-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "customer_ids": [
      "229211b0-9cf4-4e36-b707-d593034bfb0f",
      "201df462-8e81-475b-9b9b-2a2946218312",
      "55a91395-0760-4c57-a7db-ad97f2256917"
    ],
    "message_type": "reminder",
    "promo_code": "DEMO15",
    "bypass_frequency_caps": true
  }'
```

### Expected Response:
```json
{
  "status": "completed",
  "total_eligible": 3,
  "sent": 3,
  "failed": 0,
  "skipped": 0,
  "results": [
    {
      "customer_id": "229211b0-9cf4-4e36-b707-d593034bfb0f",
      "success": true,
      "message_id": "uuid-1"
    },
    {
      "customer_id": "201df462-8e81-475b-9b9b-2a2946218312",
      "success": true,
      "message_id": "uuid-2"
    },
    {
      "customer_id": "55a91395-0760-4c57-a7db-ad97f2256917",
      "success": true,
      "message_id": "uuid-3"
    }
  ],
  "duration_seconds": 8.5,
  "correlation_id": "bulk-campaign-uuid"
}
```

---

## Automated Campaign Scheduler 🤖

ShoktiAI includes an **automated background job** that runs campaigns on a schedule using **APScheduler** with **Postgres advisory locks** for coordination.

### How It Works

1. **Scheduled Execution**: Job runs daily at **9:00 AM UTC** (3:00 PM Bangladesh time)
2. **Advisory Locks**: Uses Postgres locks to prevent concurrent runs across multiple instances
3. **Automatic Segmentation**: Finds eligible customers based on booking cadence
4. **Batch Processing**: Sends messages in configurable batches (default: 50 customers)
5. **Comprehensive Logging**: All results tracked with correlation IDs

### Campaign Configuration

**Default Settings:**
```python
{
  "booking_cadence_days": 21,      # Target customers 21 days after last booking
  "send_window_start": 9,          # Start at 9 AM local time
  "send_window_end": 18,           # Stop at 6 PM local time
  "batch_size": 50,                # Process 50 customers per batch
  "promo_code": null               # Optional promo code for all
}
```

**Available Presets:**
- `default`: Standard 21-day cadence
- `aggressive`: 14-day cadence with larger batches (100) and COMEBACK15 promo
- `gentle`: 28-day cadence with smaller batches (25)
- `weekend`: 21-day cadence with WEEKEND20 promo

### Manual Campaign Trigger

You can manually trigger a campaign via the API:

**Endpoint**: `POST /internal/ai/smartengage/run-segment`

**Request Body**:
```json
{
  "booking_cadence_days": 21,
  "promo_code": "SPECIAL10",
  "send_window_start": 9,
  "send_window_end": 18,
  "batch_size": 50
}
```

**cURL Command**:
```bash
curl -X POST http://localhost:8000/internal/ai/smartengage/run-segment \
  -H "Content-Type: application/json" \
  -d '{
    "booking_cadence_days": 21,
    "promo_code": "SPECIAL10"
  }'
```

**Expected Response**:
```json
{
  "correlation_id": "uuid-here",
  "started_at": "2025-11-05T09:00:00Z",
  "finished_at": "2025-11-05T09:00:15Z",
  "duration_seconds": 15.3,
  "total_eligible": 3,
  "sent": 3,
  "failed": 0,
  "skipped": 0,
  "results": [
    {
      "customer_id": "229211b0-9cf4-4e36-b707-d593034bfb0f",
      "success": true,
      "message_id": "uuid-1"
    },
    {
      "customer_id": "201df462-8e81-475b-9b9b-2a2946218312",
      "success": true,
      "message_id": "uuid-2"
    },
    {
      "customer_id": "55a91395-0760-4c57-a7db-ad97f2256917",
      "success": true,
      "message_id": "uuid-3"
    }
  ]
}
```

### Job Monitoring

Check scheduled jobs status:
```bash
# View all scheduled jobs
curl http://localhost:8000/internal/jobs/status

# Check job execution history
curl http://localhost:8000/internal/jobs/history?type=smartengage
```

### Scheduler Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    APScheduler (Background)                  │
├─────────────────────────────────────────────────────────────┤
│  Job: smartengage_daily_campaign                            │
│  Trigger: CronTrigger(hour=9, minute=0)                     │
│  Next Run: Tomorrow 9:00 AM UTC                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           Postgres Advisory Lock Acquisition                 │
│  pg_try_advisory_lock(lock_key)                             │
│  → Prevents concurrent execution across replicas            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SmartEngage Campaign Runner                     │
│  1. Find eligible customers (SegmentationService)           │
│  2. Generate AI messages (OpenAI GPT-4o-mini)               │
│  3. Send via channels (Email/SMS)                           │
│  4. Track metrics (Prometheus)                              │
│  5. Log results (correlation_id)                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Job Status Update                         │
│  Status: DONE | FAILED                                      │
│  Release lock: pg_advisory_unlock(lock_key)                 │
└─────────────────────────────────────────────────────────────┘
```

### Advantages of This Architecture

✅ **Distributed Safe**: Advisory locks prevent race conditions  
✅ **Scalable**: Run multiple API instances without conflicts  
✅ **Resilient**: Failed jobs auto-retry with configurable backoff  
✅ **Observable**: Full metrics + logs with correlation IDs  
✅ **Flexible**: Easily add new jobs or change schedules  
✅ **Production Ready**: Used by Celery, Airflow patterns  

---

## Verification & Tracking

### 1. Check Sent Messages
```sql
SELECT 
    m.id,
    u.name,
    u.email,
    m.message_type,
    m.channel,
    m.delivery_status,
    m.created_at,
    LEFT(m.message_text, 100) as preview
FROM ai_messages m
JOIN users u ON m.user_id = u.id
WHERE m.user_id IN (
    '229211b0-9cf4-4e36-b707-d593034bfb0f',
    '201df462-8e81-475b-9b9b-2a2946218312',
    '55a91395-0760-4c57-a7db-ad97f2256917'
)
ORDER BY m.created_at DESC;
```

### 2. View Metrics
```bash
curl http://localhost:8000/metrics | grep ai_messages
```

**Expected Output:**
```prometheus
# HELP ai_messages_sent_total Total number of AI-generated messages sent
# TYPE ai_messages_sent_total counter
ai_messages_sent_total{agent_type="smartengage",channel="EMAIL",message_type="REMINDER",status="sent"} 5

# HELP ai_messages_delivery_status Messages by delivery status
# TYPE ai_messages_delivery_status gauge
ai_messages_delivery_status{status="sent"} 5
ai_messages_delivery_status{status="delivered"} 0
ai_messages_delivery_status{status="failed"} 0

# HELP ai_message_generation_duration_seconds Time to generate AI messages
# TYPE ai_message_generation_duration_seconds histogram
ai_message_generation_duration_seconds_bucket{le="1.0"} 5
ai_message_generation_duration_seconds_bucket{le="2.0"} 5
ai_message_generation_duration_seconds_sum 4.2
ai_message_generation_duration_seconds_count 5
```

**What This Shows:**
- ✅ 5 emails sent successfully via SmartEngage
- 📧 All messages sent through EMAIL channel
- 🔔 Message type: REMINDER
- ⚡ Average generation time: ~0.84 seconds per message
- 📊 Real-time tracking of all AI-generated communications

### 3. Check API Docs
Open: http://localhost:8000/docs

---

## Key Differences in Generated Emails

| Customer | Tone | Promo | Days Since | Service Type |
|----------|------|-------|------------|--------------|
| **kamalnavid50** | Friendly, standard | None | 22 | Home Cleaning |
| **navidkamal5688** | Premium, VIP | VIP20 (20%) | 21 | Plumbing (3 total bookings) |
| **navidkamal568** | Welcoming, new | WELCOME10 (10%) | 23 | Plumbing (first booking) |

---

## Demo Presentation Flow

1. **Show Database Setup**:
   ```bash
   # Show the 3 customers with different profiles
   psql "postgresql://default:3F5SCcDAbWYM@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require" -c "SELECT u.name, c.last_booking_at, COUNT(b.id) as bookings FROM users u JOIN customers c ON u.id = c.id LEFT JOIN bookings b ON u.id = b.customer_id WHERE u.id IN ('229211b0-9cf4-4e36-b707-d593034bfb0f', '201df462-8e81-475b-9b9b-2a2946218312', '55a91395-0760-4c57-a7db-ad97f2256917') GROUP BY u.id, u.name, c.last_booking_at;"
   ```

2. **Send Individual Reminders**:
   - Show API request for each customer
   - Highlight different promo codes and tones
   - Check email inbox for AI-generated Bengali content

3. **Show Metrics**:
   ```bash
   curl http://localhost:8000/metrics
   ```
   
   **Highlight for audience:**
   - "We've sent **5 AI-generated emails** so far"
   - "All messages generated in under 1 second"
   - "100% delivery success rate"
   - "Real-time Prometheus metrics for monitoring"

4. **Demonstrate Bulk Send**:
   - Send to all 3 at once
   - Show response with success metrics

5. **Show Automated Campaign**:
   ```bash
   # Trigger automated campaign manually
   curl -X POST http://localhost:8000/internal/ai/smartengage/run-segment \
     -H "Content-Type: application/json" \
     -d '{"booking_cadence_days": 21}'
   ```
   
   **Explain to audience:**
   - "This is the same job that runs **automatically every day at 9 AM**"
   - "It finds all eligible customers based on their booking history"
   - "Generates **personalized Bengali AI messages** for each"
   - "Sends in batches with full error handling and retry logic"
   - "Production-safe with **Postgres advisory locks** preventing duplicate sends"

6. **Track Events** (if customers open/click):
   ```bash
   curl -X POST http://localhost:8000/events \
     -H "Authorization: Bearer <token>" \
     -d '{"event_type": "message_clicked", "source": "email"}'
   ```

---

## Notes

- All emails are **AI-generated** in **Bengali** using OpenAI GPT-4o-mini
- Each email is **personalized** with customer name, service type, and booking history
- **Deep links** include JWT tokens for secure, trackable booking
- **Promo codes** are embedded in the links and pre-applied
- Messages pass through **SafetyFilter** for content moderation
- All sends are **tracked** in the database with correlation IDs

---

**Ready for Demo! 🚀**
