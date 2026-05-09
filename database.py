# ============================================================
#  database.py — PostgreSQL database layer (Supabase)
# ============================================================

import psycopg2
import psycopg2.extras
import logging
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id            SERIAL PRIMARY KEY,
                    telegram_id   BIGINT UNIQUE NOT NULL,
                    username      TEXT,
                    full_name     TEXT,
                    phone         TEXT,
                    created_at    TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    id            SERIAL PRIMARY KEY,
                    client_id     INTEGER NOT NULL REFERENCES clients(id),
                    service_id    TEXT NOT NULL,
                    service_name  TEXT NOT NULL,
                    booking_date  TEXT NOT NULL,
                    booking_time  TEXT NOT NULL,
                    status        TEXT NOT NULL DEFAULT 'active',
                    created_at    TIMESTAMP DEFAULT NOW(),
                    cancelled_at  TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS blocked_slots (
                    id            SERIAL PRIMARY KEY,
                    slot_date     TEXT NOT NULL,
                    slot_time     TEXT NOT NULL,
                    UNIQUE(slot_date, slot_time)
                );

                CREATE INDEX IF NOT EXISTS idx_bookings_date
                    ON bookings(booking_date, booking_time, status);

                CREATE INDEX IF NOT EXISTS idx_bookings_client
                    ON bookings(client_id, status);
            """)
        conn.commit()
    logger.info("✅ PostgreSQL database initialised")


# ──────────────────────────────────────────────
# Clients
# ──────────────────────────────────────────────

def upsert_client(telegram_id: int, username: Optional[str],
                  full_name: Optional[str], phone: Optional[str] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM clients WHERE telegram_id = %s", (telegram_id,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """UPDATE clients
                       SET username = %s, full_name = %s,
                           phone = COALESCE(%s, phone)
                       WHERE telegram_id = %s""",
                    (username, full_name, phone, telegram_id)
                )
                conn.commit()
                return existing[0]
            else:
                cur.execute(
                    """INSERT INTO clients (telegram_id, username, full_name, phone)
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                    (telegram_id, username, full_name, phone)
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                return new_id


def update_client_phone(telegram_id: int, phone: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clients SET phone = %s WHERE telegram_id = %s",
                (phone, telegram_id)
            )
        conn.commit()


def get_client(telegram_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM clients WHERE telegram_id = %s", (telegram_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
            row = cur.fetchone()
            return dict(row) if row else None


# ──────────────────────────────────────────────
# Bookings
# ──────────────────────────────────────────────

def get_booked_times(date_str: str) -> List[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT booking_time FROM bookings
                   WHERE booking_date = %s AND status = 'active'""",
                (date_str,)
            )
            return [r[0] for r in cur.fetchall()]


def create_booking(client_id: int, service_id: str, service_name: str,
                   booking_date: str, booking_time: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id FROM bookings
                   WHERE booking_date = %s AND booking_time = %s AND status = 'active'""",
                (booking_date, booking_time)
            )
            if cur.fetchone():
                raise ValueError("Slot already booked")
            cur.execute(
                """INSERT INTO bookings
                   (client_id, service_id, service_name, booking_date, booking_time)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (client_id, service_id, service_name, booking_date, booking_time)
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id


def get_client_bookings(telegram_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT b.id, b.service_name, b.booking_date, b.booking_time
                   FROM bookings b
                   JOIN clients c ON c.id = b.client_id
                   WHERE c.telegram_id = %s AND b.status = 'active'
                   ORDER BY b.booking_date, b.booking_time""",
                (telegram_id,)
            )
            return [dict(r) for r in cur.fetchall()]


def get_bookings_by_date(date_str: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT b.id, b.service_name, b.booking_date, b.booking_time,
                          c.full_name, c.phone, c.username, c.telegram_id, b.client_id
                   FROM bookings b
                   JOIN clients c ON c.id = b.client_id
                   WHERE b.booking_date = %s AND b.status = 'active'
                   ORDER BY b.booking_time""",
                (date_str,)
            )
            return [dict(r) for r in cur.fetchall()]


def cancel_booking(booking_id: int, telegram_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE bookings
                   SET status = 'cancelled', cancelled_at = NOW()
                   WHERE id = %s AND status = 'active'
                     AND client_id = (
                         SELECT id FROM clients WHERE telegram_id = %s
                     )""",
                (booking_id, telegram_id)
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0


def admin_cancel_booking(booking_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE bookings
                   SET status = 'cancelled', cancelled_at = NOW()
                   WHERE id = %s AND status = 'active'""",
                (booking_id,)
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0


def get_booking_full(booking_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT b.*, c.full_name, c.phone, c.username, c.telegram_id
                   FROM bookings b
                   JOIN clients c ON c.id = b.client_id
                   WHERE b.id = %s""",
                (booking_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None


# ──────────────────────────────────────────────
# Blocked slots
# ──────────────────────────────────────────────

def block_slot(slot_date: str, slot_time: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO blocked_slots (slot_date, slot_time) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (slot_date, slot_time)
            )
        conn.commit()


def unblock_slot(slot_date: str, slot_time: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM blocked_slots WHERE slot_date = %s AND slot_time = %s",
                (slot_date, slot_time)
            )
        conn.commit()


def get_blocked_slots(slot_date: str) -> List[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slot_time FROM blocked_slots WHERE slot_date = %s",
                (slot_date,)
            )
            return [r[0] for r in cur.fetchall()]


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────

def get_stats() -> Dict[str, Any]:
    today = date.today().isoformat()
    week_start = (date.today().replace(day=date.today().day - date.today().weekday())).isoformat()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clients")
            total_clients = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM bookings")
            total_bookings = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM bookings WHERE status = 'active'")
            active_bookings = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM bookings WHERE status = 'cancelled'")
            cancelled_bookings = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM bookings WHERE booking_date = %s AND status = 'active'",
                (today,)
            )
            today_bookings = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM bookings WHERE booking_date >= %s AND status = 'active'",
                (week_start,)
            )
            week_bookings = cur.fetchone()[0]

            cur.execute(
                """SELECT service_name, COUNT(*) as cnt FROM bookings
                   WHERE status = 'active'
                   GROUP BY service_name ORDER BY cnt DESC LIMIT 1"""
            )
            top_row = cur.fetchone()
            top_service = top_row[0] if top_row else "—"

    return {
        "total_clients": total_clients,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "cancelled_bookings": cancelled_bookings,
        "today_bookings": today_bookings,
        "week_bookings": week_bookings,
        "top_service": top_service,
    }
