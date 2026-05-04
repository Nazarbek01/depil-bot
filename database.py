# ============================================================
#  database.py — SQLite async-ready database layer
# ============================================================

import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id   INTEGER UNIQUE NOT NULL,
                username      TEXT,
                full_name     TEXT,
                phone         TEXT,
                created_at    TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id     INTEGER NOT NULL REFERENCES clients(id),
                service_id    TEXT NOT NULL,
                service_name  TEXT NOT NULL,
                booking_date  TEXT NOT NULL,   -- YYYY-MM-DD
                booking_time  TEXT NOT NULL,   -- HH:MM
                status        TEXT NOT NULL DEFAULT 'active',  -- active | cancelled
                created_at    TEXT DEFAULT (datetime('now','localtime')),
                cancelled_at  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_bookings_date
                ON bookings(booking_date, booking_time, status);

            CREATE INDEX IF NOT EXISTS idx_bookings_client
                ON bookings(client_id, status);
        """)
    logger.info("Database initialised at %s", DB_PATH)


# ──────────────────────────────────────────────
# Clients
# ──────────────────────────────────────────────

def upsert_client(telegram_id: int, username: Optional[str],
                  full_name: Optional[str], phone: Optional[str] = None) -> int:
    """Создаёт или обновляет клиента. Возвращает client.id."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM clients WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE clients
                   SET username = ?, full_name = ?,
                       phone = COALESCE(?, phone)
                   WHERE telegram_id = ?""",
                (username, full_name, phone, telegram_id)
            )
            return existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO clients (telegram_id, username, full_name, phone)
                   VALUES (?, ?, ?, ?)""",
                (telegram_id, username, full_name, phone)
            )
            return cur.lastrowid


def update_client_phone(telegram_id: int, phone: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE clients SET phone = ? WHERE telegram_id = ?",
            (phone, telegram_id)
        )


def get_client(telegram_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None


# ──────────────────────────────────────────────
# Bookings
# ──────────────────────────────────────────────

def get_booked_times(date: str) -> List[str]:
    """Возвращает занятые слоты на дату (строки HH:MM)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT booking_time FROM bookings
               WHERE booking_date = ? AND status = 'active'""",
            (date,)
        ).fetchall()
        return [r["booking_time"] for r in rows]


def create_booking(client_id: int, service_id: str, service_name: str,
                   booking_date: str, booking_time: str) -> int:
    """Создаёт запись. Возвращает booking.id."""
    with get_connection() as conn:
        # Двойная проверка на занятость слота
        conflict = conn.execute(
            """SELECT id FROM bookings
               WHERE booking_date = ? AND booking_time = ? AND status = 'active'""",
            (booking_date, booking_time)
        ).fetchone()
        if conflict:
            raise ValueError("Slot already booked")

        cur = conn.execute(
            """INSERT INTO bookings
               (client_id, service_id, service_name, booking_date, booking_time)
               VALUES (?, ?, ?, ?, ?)""",
            (client_id, service_id, service_name, booking_date, booking_time)
        )
        return cur.lastrowid


def get_client_bookings(telegram_id: int) -> List[Dict[str, Any]]:
    """Активные записи клиента, отсортированные по дате."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT b.id, b.service_name, b.booking_date, b.booking_time
               FROM bookings b
               JOIN clients c ON c.id = b.client_id
               WHERE c.telegram_id = ? AND b.status = 'active'
               ORDER BY b.booking_date, b.booking_time""",
            (telegram_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def cancel_booking(booking_id: int, telegram_id: int) -> bool:
    """Отменяет запись. Возвращает True если успешно."""
    with get_connection() as conn:
        result = conn.execute(
            """UPDATE bookings
               SET status = 'cancelled',
                   cancelled_at = datetime('now','localtime')
               WHERE id = ?
                 AND status = 'active'
                 AND client_id = (
                     SELECT id FROM clients WHERE telegram_id = ?
                 )""",
            (booking_id, telegram_id)
        )
        return result.rowcount > 0


def get_booking_full(booking_id: int) -> Optional[Dict[str, Any]]:
    """Детальная информация о записи (для уведомления администратора)."""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT b.*, c.full_name, c.phone, c.username
               FROM bookings b
               JOIN clients c ON c.id = b.client_id
               WHERE b.id = ?""",
            (booking_id,)
        ).fetchone()
        return dict(row) if row else None
