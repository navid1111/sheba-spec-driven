import psycopg2

DATABASE_URL = "postgresql://default:3F5SCcDAbWYM@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("📋 Checking booking_status enum values:")
cur.execute("SELECT unnest(enum_range(NULL::booking_status))")
for row in cur.fetchall():
    print(f"   - {row[0]}")

print("\n📋 Checking payment_status enum values:")
cur.execute("SELECT unnest(enum_range(NULL::payment_status))")
for row in cur.fetchall():
    print(f"   - {row[0]}")

print("\n📋 Checking service_category enum values:")
cur.execute("SELECT unnest(enum_range(NULL::service_category))")
for row in cur.fetchall():
    print(f"   - {row[0]}")

cur.close()
conn.close()
