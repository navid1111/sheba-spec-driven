"""Reset database to clean state."""
from src.lib.db import engine
from sqlalchemy import text

print("Resetting database...")

with engine.connect() as conn:
    # Drop all enum types
    conn.execute(text("DROP TYPE IF EXISTS user_type CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS agent_type CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS campaign_type CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS campaign_status CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS job_type CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS job_status CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS service_category CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS booking_status CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS message_channel CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS delivery_status CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS event_type CASCADE"))
    
    # Drop all tables
    conn.execute(text("DROP TABLE IF EXISTS reviews CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS bookings CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS ai_messages CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS user_activity_events CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS workers CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS services CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS jobs CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS campaigns CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS ai_message_templates CASCADE"))
    
    # Drop old tables from previous testing
    conn.execute(text("DROP TABLE IF EXISTS invoices CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS revenue CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS playing_with_neon CASCADE"))
    
    conn.commit()
    print("Database reset complete!")
