"""
Demo Worker Setup Script

Creates 4 demo workers with realistic profile fields and performance snapshots
so CoachNova (US2) can be exercised in dev/demo environments.

Workers (emails):
 - sadman.hasan.t@gmail.com
 - syedasheq@gmail.com
 - aktersanjida3.1416@gmail.com
 - navidkamal11641@gmail.com

Notes
 - Uses DATABASE_URL from environment (.env). If the URL contains the
   SQLAlchemy driver suffix "+psycopg2", it will be normalized to a plain
   psycopg2 URL for direct connections.
 - Idempotent: uses ON CONFLICT upserts on primary keys.
 - Customer/user tables are not modified beyond inserting/updating these
   worker user records and consent flags.
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Any

import json
from datetime import date

import psycopg2
from psycopg2.extras import Json

try:
    # Optional: load .env if present
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def _normalize_db_url(url: str) -> str:
    """psycopg2.connect() doesn't accept the '+psycopg2' driver suffix."""
    return url.replace("postgresql+psycopg2", "postgresql")


def get_db_url() -> str:
    env_url = os.getenv(
        "DATABASE_URL",
        "postgresql://default:3F5SCcDAbWYM@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require",
    )
    return _normalize_db_url(env_url)


def run() -> None:
    db_url = get_db_url()
    print("🚀 Starting demo worker setup...")
    
    conn = None
    cur = None
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("✅ Connected to database")

        # Deterministic UUIDs for reproducibility
        workers: list[dict[str, Any]] = [
            {
                "id": uuid.UUID("7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b"),
                "email": "sadman.hasan.t@gmail.com",
                "name": "Sadia Akter",
                "skills": ["cleaning", "deep_clean"],
                "years_experience": 3,
                "rating_avg": 4.20,
                "total_jobs_completed": 210,
                "preferred_areas": ["Mohakhali", "Banani"],
                "work_hours": {
                    "mon": ["09:00-18:00"],
                    "tue": ["09:00-18:00"],
                    "wed": ["09:00-18:00"],
                    "thu": ["09:00-18:00"],
                    "fri": ["09:00-14:00"],
                },
                "opt_in_voice": True,
                # Performance snapshot (make eligible: some late arrivals)
                "snapshot": {
                    "jobs_completed_last_7_days": 8,
                    "avg_rating_last_30_days": 4.2,
                    "late_arrivals_last_7_days": 3,
                    "cancellations_by_worker": 0,
                    "hours_worked_last_7_days": 36.5,
                    "workload_score": 62,
                    "burnout_score": 45,
                },
            },
            {
                "id": uuid.UUID("9d4e3c2b-1a0f-48b7-bc3a-2a1b0c9d8e7f"),
                "email": "syedasheq@gmail.com",
                "name": "Feroz Ahmed",
                "skills": ["electrical", "ac_repair"],
                "years_experience": 5,
                "rating_avg": 4.60,
                "total_jobs_completed": 420,
                "preferred_areas": ["Uttara", "Nikunja"],
                "work_hours": {
                    "mon": ["10:00-19:00"],
                    "tue": ["10:00-19:00"],
                    "wed": ["10:00-19:00"],
                    "thu": ["10:00-19:00"],
                    "sat": ["10:00-16:00"],
                },
                "opt_in_voice": False,
                # Strong performer (control)
                "snapshot": {
                    "jobs_completed_last_7_days": 12,
                    "avg_rating_last_30_days": 4.7,
                    "late_arrivals_last_7_days": 0,
                    "cancellations_by_worker": 0,
                    "hours_worked_last_7_days": 44.0,
                    "workload_score": 55,
                    "burnout_score": 30,
                },
            },
            {
                "id": uuid.UUID("f1e2d3c4-b5a6-47a8-9b0c-1d2e3f4a5b6c"),
                "email": "aktersanjida3.1416@gmail.com",
                "name": "Tania Rahman",
                "skills": ["beauty", "makeup"],
                "years_experience": 4,
                "rating_avg": 4.35,
                "total_jobs_completed": 310,
                "preferred_areas": ["Dhanmondi", "Lalmatia"],
                "work_hours": {
                    "sun": ["09:00-17:00"],
                    "mon": ["09:00-17:00"],
                    "tue": ["09:00-17:00"],
                    "thu": ["09:00-17:00"],
                },
                "opt_in_voice": True,
                # Mild issue
                "snapshot": {
                    "jobs_completed_last_7_days": 6,
                    "avg_rating_last_30_days": 4.3,
                    "late_arrivals_last_7_days": 1,
                    "cancellations_by_worker": 1,
                    "hours_worked_last_7_days": 28.0,
                    "workload_score": 48,
                    "burnout_score": 40,
                },
            },
            {
                "id": uuid.UUID("a0b1c2d3-e4f5-46a7-98b9-0c1d2e3f4a5b"),
                "email": "navidkamal11641@gmail.com",
                "name": "Jahangir Alam",
                "skills": ["plumbing"],
                "years_experience": 2,
                "rating_avg": 3.90,
                "total_jobs_completed": 90,
                "preferred_areas": ["Mirpur", "Pallabi"],
                "work_hours": {
                    "mon": ["08:00-16:00"],
                    "tue": ["08:00-16:00"],
                    "fri": ["08:00-12:00"],
                },
                "opt_in_voice": False,
                # Needs coaching (strong candidate)
                "snapshot": {
                    "jobs_completed_last_7_days": 7,
                    "avg_rating_last_30_days": 3.8,
                    "late_arrivals_last_7_days": 5,
                    "cancellations_by_worker": 2,
                    "hours_worked_last_7_days": 30.0,
                    "workload_score": 70,
                    "burnout_score": 65,
                },
            },
        ]

        # 1) Upsert users (type=worker)
        print("📋 Inserting/updating users...")
        for w in workers:
                        cur.execute(
                                """
                                INSERT INTO users (
                                    id, email, name, type, language_preference, is_active, consent, created_at, updated_at
                                )
                                VALUES (%s, %s, %s, 'WORKER', 'bn', TRUE, %s, NOW(), NOW())
                                ON CONFLICT (id) DO UPDATE SET
                                    email = EXCLUDED.email,
                                    name = EXCLUDED.name,
                                    type = EXCLUDED.type,
                                    language_preference = EXCLUDED.language_preference,
                                    is_active = TRUE,
                                    consent = EXCLUDED.consent,
                                    updated_at = NOW()
                                """,
                (
                    str(w["id"]),
                    w["email"],
                    w["name"],
                    Json(
                        {
                            "email_enabled": True,
                            "coaching_enabled": True,
                            "voice_opt_in": bool(w.get("opt_in_voice", False)),
                        }
                    ),
                ),
            )
        conn.commit()
        print("✅ Users upserted")

        # 2) Upsert workers (1:1 id with users)
        print("📋 Inserting/updating workers...")
        for w in workers:
            cur.execute(
                """
                INSERT INTO workers (
                    id, skills, years_experience, rating_avg, total_jobs_completed,
                    preferred_areas, work_hours, is_active, opt_in_voice
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                ON CONFLICT (id) DO UPDATE SET
                    skills = EXCLUDED.skills,
                    years_experience = EXCLUDED.years_experience,
                    rating_avg = EXCLUDED.rating_avg,
                    total_jobs_completed = EXCLUDED.total_jobs_completed,
                    preferred_areas = EXCLUDED.preferred_areas,
                    work_hours = EXCLUDED.work_hours,
                    is_active = TRUE,
                    opt_in_voice = EXCLUDED.opt_in_voice
                """,
                (
                    str(w["id"]),
                    w["skills"],
                    w["years_experience"],
                    w["rating_avg"],
                    w["total_jobs_completed"],
                    w["preferred_areas"],
                    Json(w["work_hours"]),
                    bool(w.get("opt_in_voice", False)),
                ),
            )
        conn.commit()
        print("✅ Workers upserted")

        # 3) Upsert performance snapshots (today)
        print("📋 Inserting performance snapshots for today...")
        # Ensure table exists (early migrations may not include it)
        cur.execute("SELECT to_regclass('public.worker_performance_snapshots')")
        exists = cur.fetchone()[0]
        if not exists:
            print("   ℹ️  Creating worker_performance_snapshots table (missing in current schema)...")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_performance_snapshots (
                  id UUID PRIMARY KEY,
                  worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
                  date DATE NOT NULL,
                  jobs_completed_last_7_days INT NOT NULL DEFAULT 0,
                  avg_rating_last_30_days NUMERIC(3,2),
                  late_arrivals_last_7_days INT NOT NULL DEFAULT 0,
                  cancellations_by_worker INT NOT NULL DEFAULT 0,
                  hours_worked_last_7_days NUMERIC(5,2) NOT NULL DEFAULT 0,
                  workload_score INT NOT NULL,
                  burnout_score INT NOT NULL,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_worker_snapshot ON worker_performance_snapshots(worker_id, date);
                """
            )
            conn.commit()
            print("   ✅ worker_performance_snapshots table created")

        today = date.today()
        for w in workers:
            snap = w["snapshot"]
            cur.execute(
                """
                INSERT INTO worker_performance_snapshots (
                    id, worker_id, date,
                    jobs_completed_last_7_days, avg_rating_last_30_days,
                    late_arrivals_last_7_days, cancellations_by_worker,
                    hours_worked_last_7_days, workload_score, burnout_score
                )
                VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (worker_id, date) DO UPDATE SET
                    jobs_completed_last_7_days = EXCLUDED.jobs_completed_last_7_days,
                    avg_rating_last_30_days = EXCLUDED.avg_rating_last_30_days,
                    late_arrivals_last_7_days = EXCLUDED.late_arrivals_last_7_days,
                    cancellations_by_worker = EXCLUDED.cancellations_by_worker,
                    hours_worked_last_7_days = EXCLUDED.hours_worked_last_7_days,
                    workload_score = EXCLUDED.workload_score,
                    burnout_score = EXCLUDED.burnout_score
                """,
                (
                    str(uuid.uuid4()),
                    str(w["id"]),
                    today,
                    snap["jobs_completed_last_7_days"],
                    snap["avg_rating_last_30_days"],
                    snap["late_arrivals_last_7_days"],
                    snap["cancellations_by_worker"],
                    snap["hours_worked_last_7_days"],
                    snap["workload_score"],
                    snap["burnout_score"],
                ),
            )
        conn.commit()
        print("✅ Performance snapshots upserted")

        print("🎉 Demo worker setup complete: 4 workers ready for CoachNova scenarios.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    run()