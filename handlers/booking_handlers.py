# ============================================================
#  handlers/booking_handlers.py
#  Полный flow записи: услуга → дата → время → имя → телефон → подтверждение
# ============================================================

import logging
import re
from datetime import date

from telegram import Update, ForceReply
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import SERVICES, STUDIO_NAME, MASTER_NAME
from keyboards import (
    services_kb, dates_kb, times_kb, confirm_kb,
    back_to_main_kb, main_menu_kb
)

logger = logging.getLogger(__name__)

# ─── States ────────────────────────────────────
(
    STATE_SERVICE,
    STATE_DATE,
    STATE_TIME,
    STATE_NAME,
    STATE_PHONE,
    STATE_CONFIRM,
) = range(6)

PHONE_RE = re.compile(r"^[\+\d][\d\s\-]{6,15}$")


# ──────────────────────────────────────────────
# Хелпер: найти услугу по id
# ──────────────────────────────────────────────

def _service_by_id(svc_id: str) -> dict | None:
    return next((s for s in SERVICES if s["id"] == svc_id), None)


# ──────────────────────────────────────────────
# Начало записи
# ──────────────────────────────────────────────

async def cb_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.edit_message_text(
        "💆 <b>Запись на депиляцию</b>\n\n"
        "Шаг 1/5 · Выберите <b>услугу</b>:",
        parse_mode="HTML",
        reply_markup=services_kb()
    )
    return STATE_SERVICE


# ──────────────────────────────────────────────
# Выбор услуги
# ──────────────────────────────────────────────

async def cb_select_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    svc_id = query.data.replace("svc_", "")
    svc = _service_by_id(svc_id)
    if not svc:
        await query.answer("Услуга не найдена", show_alert=True)
        return STATE_SERVICE

    context.user_data["service"] = svc

    await query.edit_message_text(
        f"✅ Услуга: <b>{svc['emoji']} {svc['name']}</b>\n"
        f"💰 Стоимость: {svc['price']}\n\n"
        "Шаг 2/5 · Выберите <b>дату</b>:",
        parse_mode="HTML",
        reply_markup=dates_kb()
    )
    return STATE_DATE


# ──────────────────────────────────────────────
# Возврат к выбору услуги
# ──────────────────────────────────────────────

async def cb_back_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "💆 <b>Запись на депиляцию</b>\n\n"
        "Шаг 1/5 · Выберите <b>услугу</b>:",
        parse_mode="HTML",
        reply_markup=services_kb()
    )
    return STATE_SERVICE


# ──────────────────────────────────────────────
# Выбор даты
# ──────────────────────────────────────────────

async def cb_select_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    date_str = query.data.replace("date_", "")
    try:
        selected = date.fromisoformat(date_str)
    except ValueError:
        await query.answer("Неверная дата", show_alert=True)
        return STATE_DATE

    context.user_data["date"] = date_str

    booked = db.get_booked_times(date_str)
    svc = context.user_data.get("service", {})

    # Форматируем дату по-русски
    days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    months_ru = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
                 "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    date_label = f"{days_ru[selected.weekday()]}, {selected.day} {months_ru[selected.month]}"

    await query.edit_message_text(
        f"✅ Услуга: <b>{svc.get('emoji','')} {svc.get('name','')}</b>\n"
        f"📅 Дата: <b>{date_label}</b>\n\n"
        "Шаг 3/5 · Выберите <b>время</b>:\n"
        "🟢 — свободно  🔴 — занято",
        parse_mode="HTML",
        reply_markup=times_kb(booked)
    )
    return STATE_TIME


# ──────────────────────────────────────────────
# Возврат к датам
# ──────────────────────────────────────────────

async def cb_back_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    svc = context.user_data.get("service", {})
    await query.edit_message_text(
        f"✅ Услуга: <b>{svc.get('emoji','')} {svc.get('name','')}</b>\n\n"
        "Шаг 2/5 · Выберите <b>дату</b>:",
        parse_mode="HTML",
        reply_markup=dates_kb()
    )
    return STATE_DATE


# ──────────────────────────────────────────────
# Занятый слот — просто алерт
# ──────────────────────────────────────────────

async def cb_slot_taken(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("🔴 Это время уже занято. Выберите другое!", show_alert=True)
    return STATE_TIME


# ──────────────────────────────────────────────
# Выбор времени
# ──────────────────────────────────────────────

async def cb_select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    time_str = query.data.replace("time_", "")
    context.user_data["time"] = time_str

    # Проверяем, есть ли уже сохранённое имя
    client = db.get_client(update.effective_user.id)
    saved_name = client.get("full_name") if client else None

    svc = context.user_data.get("service", {})
    date_str = context.user_data.get("date", "")

    if saved_name:
        # Предлагаем использовать сохранённое имя
        await query.edit_message_text(
            f"✅ Услуга: <b>{svc.get('emoji','')} {svc.get('name','')}</b>\n"
            f"📅 Дата: <b>{date_str}</b>\n"
            f"⏰ Время: <b>{time_str}</b>\n\n"
            f"Шаг 4/5 · Ваше имя:\n\n"
            f"Введите имя или отправьте <b>«+»</b> чтобы использовать сохранённое: "
            f"<b>{saved_name}</b>",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            f"✅ Услуга: <b>{svc.get('emoji','')} {svc.get('name','')}</b>\n"
            f"📅 Дата: <b>{date_str}</b>\n"
            f"⏰ Время: <b>{time_str}</b>\n\n"
            "Шаг 4/5 · Введите ваше <b>имя</b>:",
            parse_mode="HTML"
        )
    return STATE_NAME


# ──────────────────────────────────────────────
# Ввод имени (текстовое сообщение)
# ──────────────────────────────────────────────

async def msg_enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    # Используем сохранённое имя
    if text == "+":
        client = db.get_client(update.effective_user.id)
        name = client.get("full_name", "") if client else ""
        if not name:
            await update.message.reply_text("❗ Имя не найдено. Введите вручную:")
            return STATE_NAME
    else:
        if len(text) < 2:
            await update.message.reply_text("❗ Имя слишком короткое. Попробуйте снова:")
            return STATE_NAME
        name = text

    context.user_data["client_name"] = name

    # Проверяем сохранённый телефон
    client = db.get_client(update.effective_user.id)
    saved_phone = client.get("phone") if client else None

    if saved_phone:
        await update.message.reply_text(
            f"✅ Имя: <b>{name}</b>\n\n"
            f"Шаг 5/5 · Ваш телефон:\n\n"
            f"Введите телефон или <b>«+»</b> для использования сохранённого: "
            f"<b>{saved_phone}</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"✅ Имя: <b>{name}</b>\n\n"
            "Шаг 5/5 · Введите ваш <b>номер телефона</b>:\n"
            "Например: +998901234567",
            parse_mode="HTML"
        )
    return STATE_PHONE


# ──────────────────────────────────────────────
# Ввод телефона (текстовое сообщение)
# ──────────────────────────────────────────────

async def msg_enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    # Используем сохранённый телефон
    if text == "+":
        client = db.get_client(update.effective_user.id)
        phone = client.get("phone", "") if client else ""
        if not phone:
            await update.message.reply_text("❗ Телефон не найден. Введите вручную:")
            return STATE_PHONE
    else:
        if not PHONE_RE.match(text):
            await update.message.reply_text(
                "❗ Неверный формат телефона.\n"
                "Введите в формате: <b>+998901234567</b>",
                parse_mode="HTML"
            )
            return STATE_PHONE
        phone = text

    context.user_data["client_phone"] = phone

    # Сохраняем телефон клиента
    db.update_client_phone(update.effective_user.id, phone)

    # Показываем итоговую информацию
    svc = context.user_data.get("service", {})
    date_str = context.user_data.get("date", "")
    time_str = context.user_data.get("time", "")
    name = context.user_data.get("client_name", "")

    await update.message.reply_text(
        "📋 <b>Проверьте данные записи:</b>\n\n"
        f"💆 Услуга: <b>{svc.get('emoji','')} {svc.get('name','')}</b>\n"
        f"💰 Стоимость: {svc.get('price','')}\n"
        f"👩 Мастер: <b>{MASTER_NAME}</b>\n"
        f"📅 Дата: <b>{date_str}</b>\n"
        f"⏰ Время: <b>{time_str}</b>\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📱 Телефон: <b>{phone}</b>\n\n"
        "Всё верно?",
        parse_mode="HTML",
        reply_markup=confirm_kb()
    )
    return STATE_CONFIRM


# ──────────────────────────────────────────────
# Подтверждение записи
# ──────────────────────────────────────────────

async def cb_confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    svc = context.user_data.get("service", {})
    date_str = context.user_data.get("date", "")
    time_str = context.user_data.get("time", "")
    name = context.user_data.get("client_name", "")
    phone = context.user_data.get("client_phone", "")

    # Обновляем имя клиента
    client_id = db.upsert_client(
        telegram_id=user.id,
        username=user.username,
        full_name=name,
        phone=phone
    )

    try:
        booking_id = db.create_booking(
            client_id=client_id,
            service_id=svc["id"],
            service_name=svc["name"],
            booking_date=date_str,
            booking_time=time_str
        )
    except ValueError:
        # Слот заняли, пока клиент вводил данные
        await query.edit_message_text(
            "😔 К сожалению, это время только что заняли.\n\n"
            "Пожалуйста, начните запись заново и выберите другое время.",
            reply_markup=main_menu_kb()
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Уведомляем администратора
    await _notify_admin_new_booking(context, booking_id, user)

    await query.edit_message_text(
        "🎉 <b>Запись подтверждена!</b>\n\n"
        f"💆 Услуга: <b>{svc['emoji']} {svc['name']}</b>\n"
        f"👩 Мастер: <b>{MASTER_NAME}</b>\n"
        f"📅 Дата: <b>{date_str}</b>\n"
        f"⏰ Время: <b>{time_str}</b>\n\n"
        "Ждём вас в студии! ✨\n"
        "Если планы изменятся — отмените запись в разделе «Мои записи».",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ──────────────────────────────────────────────
# Отмена потока записи
# ──────────────────────────────────────────────

async def cb_cancel_booking_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.edit_message_text(
        "❌ Запись отменена.\n\n"
        "Вы всегда можете вернуться и записаться снова 😊",
        reply_markup=main_menu_kb()
    )
    return ConversationHandler.END


# ──────────────────────────────────────────────
# Уведомление администратора — новая запись
# ──────────────────────────────────────────────

async def _notify_admin_new_booking(context, booking_id: int, user) -> None:
    from config import ADMIN_CHAT_ID
    if not ADMIN_CHAT_ID:
        return

    booking = db.get_booking_full(booking_id)
    if not booking:
        return

    username_str = f"@{user.username}" if user.username else "без username"

    text = (
        "🔔 <b>Новая запись!</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👤 Имя: <b>{booking['full_name']}</b>\n"
        f"📱 Телефон: <b>{booking['phone']}</b>\n"
        f"💆 Услуга: <b>{booking['service_name']}</b>\n"
        f"📅 Дата: <b>{booking['booking_date']}</b>\n"
        f"⏰ Время: <b>{booking['booking_time']}</b>\n"
        f"💬 Telegram: {username_str}\n"
        "━━━━━━━━━━━━━━━━"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Failed to notify admin: %s", e)
