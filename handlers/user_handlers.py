# ============================================================
#  handlers/user_handlers.py
#  /start, главное меню, контакты, мои записи
# ============================================================

import logging
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import STUDIO_NAME, MASTER_NAME, STUDIO_PHONE, STUDIO_CITY, STUDIO_INSTAGRAM
from keyboards import main_menu_kb, bookings_list_kb, back_to_main_kb

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    # Сохраняем / обновляем клиента
    db.upsert_client(
        telegram_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    text = (
        f"✨ Добро пожаловать в <b>{STUDIO_NAME}</b>!\n\n"
        f"💆 Мастер: <b>{MASTER_NAME}</b>\n"
        f"📍 Город: {STUDIO_CITY}\n\n"
        "Я помогу вам записаться на депиляцию, "
        "посмотреть ваши записи или отменить их.\n\n"
        "Выберите действие 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb())


# ──────────────────────────────────────────────
# Callback: back_main
# ──────────────────────────────────────────────

async def cb_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text = (
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие 👇"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu_kb())


# ──────────────────────────────────────────────
# Callback: contacts
# ──────────────────────────────────────────────

async def cb_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text = (
        f"📞 <b>Контакты {STUDIO_NAME}</b>\n\n"
        f"👩 Мастер: <b>{MASTER_NAME}</b>\n"
        f"📱 Телефон: <b>{STUDIO_PHONE}</b>\n"
        f"📍 Город: {STUDIO_CITY}\n"
        f"📸 Instagram: {STUDIO_INSTAGRAM}\n\n"
        "Рабочее время: <b>10:00 – 20:00</b> ежедневно"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_to_main_kb())


# ──────────────────────────────────────────────
# Callback: my_bookings
# ──────────────────────────────────────────────

async def cb_my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    bookings = db.get_client_bookings(user.id)

    if not bookings:
        await query.edit_message_text(
            "📭 У вас пока нет активных записей.\n\n"
            "Нажмите <b>«Записаться»</b> в главном меню.",
            parse_mode="HTML",
            reply_markup=back_to_main_kb()
        )
        return

    text = f"📋 <b>Ваши записи</b> ({len(bookings)} шт.):\n\n"
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=bookings_list_kb(bookings, action_prefix="view_booking")
    )


# ──────────────────────────────────────────────
# /help
# ──────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "• <b>Записаться</b> — выберите услугу, дату и время\n"
        "• <b>Мои записи</b> — список ваших активных записей\n"
        "• <b>Отменить запись</b> — отмена выбранной записи\n"
        "• <b>Контакты</b> — телефон и адрес студии\n\n"
        f"По вопросам: {STUDIO_PHONE}"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb())
