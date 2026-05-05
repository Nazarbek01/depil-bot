# ============================================================
#  handlers/admin_handlers.py — Полная админ-панель
# ============================================================

import logging
from datetime import date, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)

MONTHS_RU = [
    "", "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек"
]


def is_admin(user_id: int) -> bool:
    return ADMIN_CHAT_ID and user_id == ADMIN_CHAT_ID


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Записи на сегодня",     callback_data="adm_today")],
        [InlineKeyboardButton("🗓 Записи на другую дату", callback_data="adm_pick_date")],
        [InlineKeyboardButton("🚫 Заблокировать слот",    callback_data="adm_block_pick")],
        [InlineKeyboardButton("📵 Заблокировать день",    callback_data="adm_block_day_pick")],
        [InlineKeyboardButton("✅ Разблокировать слот",   callback_data="adm_unblock_pick")],
        [InlineKeyboardButton("📊 Статистика",            callback_data="adm_stats")],
    ])


# ──────────────────────────────────────────────
# /admin — вход в панель
# ──────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    await update.message.reply_text(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


async def cb_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ──────────────────────────────────────────────
# Записи на сегодня
# ──────────────────────────────────────────────

async def cb_adm_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    today = date.today().isoformat()
    bookings = db.get_bookings_by_date(today)
    await _show_bookings_for_date(query, bookings, today)


async def _show_bookings_for_date(query, bookings, date_str):
    d = date.fromisoformat(date_str)
    date_label = f"{d.day} {MONTHS_RU[d.month]} {d.year}"

    if not bookings:
        await query.edit_message_text(
            f"📅 <b>{date_label}</b>\n\nЗаписей нет.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")]
            ])
        )
        return

    text = f"📅 <b>Записи на {date_label}:</b>\n\n"
    buttons = []
    for b in bookings:
        phone = b.get("phone") or "—"
        username = f"@{b['username']}" if b.get("username") else "—"
        text += (
            f"🕐 <b>{b['booking_time']}</b> — {b['service_name']}\n"
            f"   👤 {b['full_name']} | 📱 {phone} | {username}\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                f"❌ Отменить {b['booking_time']} {b['full_name']}",
                callback_data=f"adm_cancel_{b['id']}"
            )
        ])

    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")])
    await query.edit_message_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(buttons))


# ──────────────────────────────────────────────
# Записи на другую дату — выбор даты
# ──────────────────────────────────────────────

async def cb_adm_pick_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    today = date.today()
    rows = []
    row = []
    for i in range(14):
        d = today + timedelta(days=i)
        label = f"{d.day} {MONTHS_RU[d.month]}"
        row.append(InlineKeyboardButton(label, callback_data=f"adm_date_{d.isoformat()}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")])

    await query.edit_message_text(
        "🗓 Выберите дату:",
        reply_markup=InlineKeyboardMarkup(rows)
    )


async def cb_adm_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    date_str = query.data.replace("adm_date_", "")
    bookings = db.get_bookings_by_date(date_str)
    await _show_bookings_for_date(query, bookings, date_str)


# ──────────────────────────────────────────────
# Отмена любой записи администратором
# ──────────────────────────────────────────────

async def cb_adm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    booking_id = int(query.data.replace("adm_cancel_", ""))
    booking = db.get_booking_full(booking_id)
    if not booking:
        await query.edit_message_text("❌ Запись не найдена.")
        return

    d = date.fromisoformat(booking["booking_date"])
    text = (
        f"⚠️ Отменить запись?\n\n"
        f"👤 {booking['full_name']}\n"
        f"💆 {booking['service_name']}\n"
        f"📅 {d.day} {MONTHS_RU[d.month]} в {booking['booking_time']}\n"
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, отменить", callback_data=f"adm_do_cancel_{booking_id}"),
                InlineKeyboardButton("🔙 Назад", callback_data="adm_menu"),
            ]
        ])
    )


async def cb_adm_do_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    booking_id = int(query.data.replace("adm_do_cancel_", ""))
    booking = db.get_booking_full(booking_id)
    success = db.admin_cancel_booking(booking_id)

    if success and booking:
        # Уведомляем клиента
        try:
            client = db.get_client_by_id(booking["client_id"])
            if client:
                d = date.fromisoformat(booking["booking_date"])
                await context.bot.send_message(
                    chat_id=client["telegram_id"],
                    text=(
                        f"❌ Ваша запись была отменена администратором.\n\n"
                        f"💆 {booking['service_name']}\n"
                        f"📅 {d.day} {MONTHS_RU[d.month]} в {booking['booking_time']}\n\n"
                        f"Для повторной записи нажмите /start"
                    )
                )
        except Exception:
            pass

        await query.edit_message_text(
            "✅ Запись отменена. Клиент уведомлён.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ В меню", callback_data="adm_menu")]
            ])
        )
    else:
        await query.edit_message_text("❌ Не удалось отменить запись.")


# ──────────────────────────────────────────────
# Блокировка слота
# ──────────────────────────────────────────────

async def cb_adm_block_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    today = date.today()
    rows = []
    row = []
    for i in range(14):
        d = today + timedelta(days=i)
        label = f"{d.day} {MONTHS_RU[d.month]}"
        row.append(InlineKeyboardButton(label, callback_data=f"adm_block_date_{d.isoformat()}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")])

    await query.edit_message_text("🚫 Выберите дату для блокировки:", reply_markup=InlineKeyboardMarkup(rows))


async def cb_adm_block_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    date_str = query.data.replace("adm_block_date_", "")
    context.user_data["block_date"] = date_str
    booked = db.get_booked_times(date_str)
    blocked = db.get_blocked_slots(date_str)

    from config import TIME_SLOTS
    rows = []
    for slot in TIME_SLOTS:
        if slot in blocked:
            label = f"🔒 {slot} (уже заблок.)"
            cb = f"adm_noop"
        elif slot in booked:
            label = f"🔴 {slot} (занят)"
            cb = "adm_noop"
        else:
            label = f"🟢 {slot}"
            cb = f"adm_do_block_{date_str}_{slot}"
        rows.append([InlineKeyboardButton(label, callback_data=cb)])

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_block_pick")])
    await query.edit_message_text("🚫 Выберите слот для блокировки:", reply_markup=InlineKeyboardMarkup(rows))


async def cb_adm_do_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    parts = query.data.replace("adm_do_block_", "").split("_")
    date_str = parts[0]
    time_str = parts[1]

    db.block_slot(date_str, time_str)
    d = date.fromisoformat(date_str)
    await query.edit_message_text(
        f"🔒 Слот {d.day} {MONTHS_RU[d.month]} в {time_str} заблокирован.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В меню", callback_data="adm_menu")]
        ])
    )


# ──────────────────────────────────────────────
# Блокировка всего дня
# ──────────────────────────────────────────────

async def cb_adm_block_day_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    today = date.today()
    rows = []
    row = []
    for i in range(14):
        d = today + timedelta(days=i)
        label = f"{d.day} {MONTHS_RU[d.month]}"
        row.append(InlineKeyboardButton(label, callback_data=f"adm_block_day_{d.isoformat()}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")])
    await query.edit_message_text("📵 Выберите день для полной блокировки:", reply_markup=InlineKeyboardMarkup(rows))


async def cb_adm_block_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    date_str = query.data.replace("adm_block_day_", "")
    from config import TIME_SLOTS
    for slot in TIME_SLOTS:
        db.block_slot(date_str, slot)

    d = date.fromisoformat(date_str)
    await query.edit_message_text(
        f"📵 День {d.day} {MONTHS_RU[d.month]} полностью заблокирован.\nЗапись в этот день недоступна.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В меню", callback_data="adm_menu")]
        ])
    )


# ──────────────────────────────────────────────
# Разблокировка слота
# ──────────────────────────────────────────────

async def cb_adm_unblock_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    today = date.today()
    rows = []
    row = []
    for i in range(14):
        d = today + timedelta(days=i)
        label = f"{d.day} {MONTHS_RU[d.month]}"
        row.append(InlineKeyboardButton(label, callback_data=f"adm_unblock_date_{d.isoformat()}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")])
    await query.edit_message_text("✅ Выберите дату для разблокировки:", reply_markup=InlineKeyboardMarkup(rows))


async def cb_adm_unblock_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    date_str = query.data.replace("adm_unblock_date_", "")
    blocked = db.get_blocked_slots(date_str)

    if not blocked:
        await query.edit_message_text(
            "Нет заблокированных слотов на эту дату.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")]
            ])
        )
        return

    rows = []
    for slot in blocked:
        rows.append([InlineKeyboardButton(f"🔓 {slot}", callback_data=f"adm_do_unblock_{date_str}_{slot}")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")])
    await query.edit_message_text("✅ Выберите слот для разблокировки:", reply_markup=InlineKeyboardMarkup(rows))


async def cb_adm_do_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    parts = query.data.replace("adm_do_unblock_", "").split("_")
    date_str = parts[0]
    time_str = parts[1]

    db.unblock_slot(date_str, time_str)
    d = date.fromisoformat(date_str)
    await query.edit_message_text(
        f"✅ Слот {d.day} {MONTHS_RU[d.month]} в {time_str} разблокирован.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В меню", callback_data="adm_menu")]
        ])
    )


async def cb_adm_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("Этот слот недоступен.", show_alert=False)


# ──────────────────────────────────────────────
# Статистика
# ──────────────────────────────────────────────

async def cb_adm_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    stats = db.get_stats()
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего клиентов: <b>{stats['total_clients']}</b>\n"
        f"📅 Всего записей: <b>{stats['total_bookings']}</b>\n"
        f"✅ Активных: <b>{stats['active_bookings']}</b>\n"
        f"❌ Отменённых: <b>{stats['cancelled_bookings']}</b>\n\n"
        f"📆 Записей за сегодня: <b>{stats['today_bookings']}</b>\n"
        f"📆 Записей за эту неделю: <b>{stats['week_bookings']}</b>\n\n"
        f"💆 Топ услуга: <b>{stats['top_service']}</b>\n"
    )
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="adm_menu")]
        ])
    )


# ──────────────────────────────────────────────
# Старые хендлеры (для совместимости с bot.py)
# ──────────────────────────────────────────────

async def cb_cancel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню отмены записи для обычных пользователей."""
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    bookings = db.get_client_bookings(telegram_id)

    if not bookings:
        from keyboards import back_to_main_kb
        await query.edit_message_text("У вас нет активных записей.", reply_markup=back_to_main_kb())
        return

    from keyboards import bookings_list_kb
    await query.edit_message_text(
        "Выберите запись для отмены:",
        reply_markup=bookings_list_kb(bookings, action_prefix="cancel_id")
    )


async def cb_cancel_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.replace("cancel_id_", ""))
    booking = db.get_booking_full(booking_id)
    if not booking:
        await query.edit_message_text("Запись не найдена.")
        return
    from keyboards import confirm_cancel_kb
    d = date.fromisoformat(booking["booking_date"])
    await query.edit_message_text(
        f"Отменить запись?\n\n💆 {booking['service_name']}\n📅 {d.day} {MONTHS_RU[d.month]} в {booking['booking_time']}",
        reply_markup=confirm_cancel_kb(booking_id)
    )


async def cb_do_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.replace("do_cancel_", ""))
    success = db.cancel_booking(booking_id, query.from_user.id)

    from keyboards import back_to_main_kb
    if success:
        booking = db.get_booking_full(booking_id)
        if booking and ADMIN_CHAT_ID:
            try:
                d = date.fromisoformat(booking["booking_date"])
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"⚠️ <b>Клиент отменил запись</b>\n\n"
                        f"👤 {booking['full_name']}\n"
                        f"📱 {booking.get('phone', '—')}\n"
                        f"💆 {booking['service_name']}\n"
                        f"📅 {d.day} {MONTHS_RU[d.month]} в {booking['booking_time']}"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await query.edit_message_text("✅ Запись отменена.", reply_markup=back_to_main_kb())
    else:
        await query.edit_message_text("❌ Не удалось отменить.", reply_markup=back_to_main_kb())


async def cb_view_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.replace("view_booking_", ""))
    booking = db.get_booking_full(booking_id)
    if not booking:
        await query.answer("Запись не найдена.", show_alert=True)
        return
    d = date.fromisoformat(booking["booking_date"])
    await query.answer(
        f"{booking['service_name']}\n{d.day} {MONTHS_RU[d.month]} в {booking['booking_time']}",
        show_alert=True
    )
