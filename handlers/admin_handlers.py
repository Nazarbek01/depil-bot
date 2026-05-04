# ============================================================
#  handlers/admin_handlers.py
#  Отмена записи клиентом + уведомление администратора
# ============================================================

import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_CHAT_ID
from keyboards import (
    bookings_list_kb, confirm_cancel_kb, back_to_main_kb, main_menu_kb
)

logger = logging.getLogger(__name__)

MONTHS_RU = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]


# ──────────────────────────────────────────────
# Меню отмены записи
# ──────────────────────────────────────────────

async def cb_cancel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    bookings = db.get_client_bookings(user.id)

    if not bookings:
        await query.edit_message_text(
            "📭 У вас нет активных записей для отмены.",
            reply_markup=back_to_main_kb()
        )
        return

    await query.edit_message_text(
        "❌ <b>Выберите запись для отмены:</b>",
        parse_mode="HTML",
        reply_markup=bookings_list_kb(bookings, action_prefix="cancel_id")
    )


# ──────────────────────────────────────────────
# Нажали на конкретную запись для отмены
# ──────────────────────────────────────────────

async def cb_cancel_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    booking_id = int(query.data.replace("cancel_id_", ""))
    booking = db.get_booking_full(booking_id)

    if not booking or booking["status"] != "active":
        await query.edit_message_text(
            "😔 Запись не найдена или уже отменена.",
            reply_markup=back_to_main_kb()
        )
        return

    d = date.fromisoformat(booking["booking_date"])
    date_label = f"{d.day} {MONTHS_RU[d.month]} {d.year}"

    await query.edit_message_text(
        f"❓ <b>Вы уверены, что хотите отменить запись?</b>\n\n"
        f"💆 Услуга: <b>{booking['service_name']}</b>\n"
        f"📅 Дата: <b>{date_label}</b>\n"
        f"⏰ Время: <b>{booking['booking_time']}</b>\n\n"
        "После отмены слот освободится для других клиентов.",
        parse_mode="HTML",
        reply_markup=confirm_cancel_kb(booking_id)
    )


# ──────────────────────────────────────────────
# Подтверждение отмены
# ──────────────────────────────────────────────

async def cb_do_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    booking_id = int(query.data.replace("do_cancel_", ""))

    # Получаем данные до отмены (для уведомления)
    booking = db.get_booking_full(booking_id)

    success = db.cancel_booking(booking_id, user.id)

    if not success:
        await query.edit_message_text(
            "😔 Не удалось отменить запись. Возможно, она уже была отменена.",
            reply_markup=back_to_main_kb()
        )
        return

    # Уведомляем администратора
    if booking:
        await _notify_admin_cancellation(context, booking, user)

    await query.edit_message_text(
        "✅ <b>Запись успешно отменена.</b>\n\n"
        "Слот освобождён. Будем рады видеть вас снова! 😊",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )


# ──────────────────────────────────────────────
# Просмотр записи (из «Мои записи»)
# ──────────────────────────────────────────────

async def cb_view_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали одной записи."""
    query = update.callback_query
    await query.answer()

    booking_id = int(query.data.replace("view_booking_", ""))
    booking = db.get_booking_full(booking_id)

    if not booking or booking["status"] != "active":
        await query.edit_message_text(
            "😔 Запись не найдена или уже отменена.",
            reply_markup=back_to_main_kb()
        )
        return

    d = date.fromisoformat(booking["booking_date"])
    date_label = f"{d.day} {MONTHS_RU[d.month]} {d.year}"

    await query.edit_message_text(
        f"📌 <b>Детали записи</b>\n\n"
        f"💆 Услуга: <b>{booking['service_name']}</b>\n"
        f"📅 Дата: <b>{date_label}</b>\n"
        f"⏰ Время: <b>{booking['booking_time']}</b>\n"
        f"📱 Телефон: <b>{booking['phone'] or 'не указан'}</b>",
        parse_mode="HTML",
        reply_markup=confirm_cancel_kb(booking_id)
    )


# ──────────────────────────────────────────────
# Уведомление администратора — отмена
# ──────────────────────────────────────────────

async def _notify_admin_cancellation(context, booking: dict, user) -> None:
    if not ADMIN_CHAT_ID:
        return

    username_str = f"@{user.username}" if user.username else "без username"

    text = (
        "⚠️ <b>Отмена записи!</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👤 Имя: <b>{booking['full_name']}</b>\n"
        f"📱 Телефон: <b>{booking['phone']}</b>\n"
        f"💆 Услуга: <b>{booking['service_name']}</b>\n"
        f"📅 Дата: <b>{booking['booking_date']}</b>\n"
        f"⏰ Время: <b>{booking['booking_time']}</b>\n"
        f"💬 Telegram: {username_str}\n"
        "━━━━━━━━━━━━━━━━\n"
        "🟢 Слот снова свободен"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Failed to notify admin about cancellation: %s", e)
