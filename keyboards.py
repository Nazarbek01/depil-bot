# ============================================================
#  keyboards.py — все InlineKeyboard-клавиатуры бота
# ============================================================

from datetime import date, timedelta
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import SERVICES, TIME_SLOTS, BOOKING_DAYS_AHEAD


# ──────────────────────────────────────────────
# Главное меню (для клиентов)
# ──────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Записаться",        callback_data="book_start")],
        [InlineKeyboardButton("🗂 Мои записи",        callback_data="my_bookings")],
        [InlineKeyboardButton("❌ Отменить запись",   callback_data="cancel_menu")],
        [InlineKeyboardButton("📞 Контакты студии",   callback_data="contacts")],
    ])


# ──────────────────────────────────────────────
# Главное меню для администратора (с кнопкой панели)
# ──────────────────────────────────────────────

def admin_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Записаться",        callback_data="book_start")],
        [InlineKeyboardButton("🗂 Мои записи",        callback_data="my_bookings")],
        [InlineKeyboardButton("❌ Отменить запись",   callback_data="cancel_menu")],
        [InlineKeyboardButton("📞 Контакты студии",   callback_data="contacts")],
        [InlineKeyboardButton("👑 Админ-панель",      callback_data="adm_menu")],
    ])


# ──────────────────────────────────────────────
# Услуги
# ──────────────────────────────────────────────

def services_kb() -> InlineKeyboardMarkup:
    rows = []
    for svc in SERVICES:
        label = f"{svc['emoji']} {svc['name']} — {svc['price']}"
        rows.append([InlineKeyboardButton(label, callback_data=f"svc_{svc['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


# ──────────────────────────────────────────────
# Выбор даты
# ──────────────────────────────────────────────

DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "", "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек"
]


def dates_kb() -> InlineKeyboardMarkup:
    today = date.today()
    rows = []
    row: list = []
    for i in range(BOOKING_DAYS_AHEAD):
        d = today + timedelta(days=i)
        day_name = DAYS_RU[d.weekday()]
        label = f"{day_name} {d.day} {MONTHS_RU[d.month]}"
        btn = InlineKeyboardButton(label, callback_data=f"date_{d.isoformat()}")
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_services")])
    return InlineKeyboardMarkup(rows)


# ──────────────────────────────────────────────
# Выбор времени
# ──────────────────────────────────────────────

def times_kb(booked_times: List[str], blocked_times: List[str] = None) -> InlineKeyboardMarkup:
    if blocked_times is None:
        blocked_times = []
    rows = []
    row: list = []
    for slot in TIME_SLOTS:
        if slot in blocked_times:
            label = f"🔒 {slot}"
            btn = InlineKeyboardButton(label, callback_data="slot_taken")
        elif slot in booked_times:
            label = f"🔴 {slot}"
            btn = InlineKeyboardButton(label, callback_data="slot_taken")
        else:
            label = f"🟢 {slot}"
            btn = InlineKeyboardButton(label, callback_data=f"time_{slot}")
        row.append(btn)
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_dates")])
    return InlineKeyboardMarkup(rows)


# ──────────────────────────────────────────────
# Подтверждение записи
# ──────────────────────────────────────────────

def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking"),
            InlineKeyboardButton("❌ Отмена",      callback_data="cancel_booking_flow"),
        ]
    ])


# ──────────────────────────────────────────────
# Список записей клиента
# ──────────────────────────────────────────────

def bookings_list_kb(bookings: list, action_prefix: str = "cancel_id") -> InlineKeyboardMarkup:
    rows = []
    for b in bookings:
        d = date.fromisoformat(b["booking_date"])
        label = (
            f"📌 {b['service_name']} | "
            f"{d.day} {MONTHS_RU[d.month]} {d.year} в {b['booking_time']}"
        )
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{action_prefix}_{b['id']}")
        ])
    rows.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


# ──────────────────────────────────────────────
# Подтверждение отмены
# ──────────────────────────────────────────────

def confirm_cancel_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, отменить",  callback_data=f"do_cancel_{booking_id}"),
            InlineKeyboardButton("🔙 Не отменять",   callback_data="cancel_menu"),
        ]
    ])


# ──────────────────────────────────────────────
# Кнопка "В главное меню"
# ──────────────────────────────────────────────

def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
    ])
