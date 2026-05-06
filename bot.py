# ============================================================
#  bot.py — Studio Depil Rina · Telegram Bot
#  Entry point · Python 3.11+ · python-telegram-bot v20+
# ============================================================

import logging
import sys
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from config import BOT_TOKEN
from handlers.user_handlers import (
    cmd_start,
    cmd_help,
    cb_back_main,
    cb_contacts,
    cb_my_bookings,
)
from handlers.booking_handlers import (
    cb_book_start,
    cb_select_service,
    cb_back_services,
    cb_select_date,
    cb_back_dates,
    cb_select_time,
    cb_slot_taken,
    msg_enter_name,
    msg_enter_phone,
    cb_confirm_booking,
    cb_cancel_booking_flow,
    STATE_SERVICE,
    STATE_DATE,
    STATE_TIME,
    STATE_NAME,
    STATE_PHONE,
    STATE_CONFIRM,
)
from handlers.admin_handlers import (
    cmd_admin,
    cb_admin_menu,
    cb_adm_today,
    cb_adm_pick_date,
    cb_adm_date,
    cb_adm_cancel,
    cb_adm_do_cancel,
    cb_adm_block_pick,
    cb_adm_block_date,
    cb_adm_do_block,
    cb_adm_block_day_pick,
    cb_adm_block_day,
    cb_adm_unblock_pick,
    cb_adm_unblock_date,
    cb_adm_do_unblock,
    cb_adm_noop,
    cb_adm_stats,
    cb_cancel_menu,
    cb_cancel_id,
    cb_do_cancel,
    cb_view_booking,
)

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Health check server для Render
# ──────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server on port {port}")
    server.serve_forever()


# ──────────────────────────────────────────────
# ConversationHandler
# ──────────────────────────────────────────────

def build_booking_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_book_start, pattern="^book_start$"),
        ],
        states={
            STATE_SERVICE: [
                CallbackQueryHandler(cb_select_service, pattern=r"^svc_"),
                CallbackQueryHandler(cb_back_main,      pattern="^back_main$"),
            ],
            STATE_DATE: [
                CallbackQueryHandler(cb_select_date,    pattern=r"^date_"),
                CallbackQueryHandler(cb_back_services,  pattern="^back_services$"),
                CallbackQueryHandler(cb_back_main,      pattern="^back_main$"),
            ],
            STATE_TIME: [
                CallbackQueryHandler(cb_select_time,    pattern=r"^time_"),
                CallbackQueryHandler(cb_slot_taken,     pattern="^slot_taken$"),
                CallbackQueryHandler(cb_back_dates,     pattern="^back_dates$"),
                CallbackQueryHandler(cb_back_main,      pattern="^back_main$"),
            ],
            STATE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_enter_name),
            ],
            STATE_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_enter_phone),
            ],
            STATE_CONFIRM: [
                CallbackQueryHandler(cb_confirm_booking,      pattern="^confirm_booking$"),
                CallbackQueryHandler(cb_cancel_booking_flow,  pattern="^cancel_booking_flow$"),
            ],
        },
        fallbacks=[
            CommandHandler("start",  cmd_start),
            CommandHandler("cancel", cb_cancel_booking_flow),
            CallbackQueryHandler(cb_back_main, pattern="^back_main$"),
        ],
        allow_reentry=True,
        name="booking_flow",
        persistent=False,
    )


# ──────────────────────────────────────────────
# Регистрация хендлеров
# ──────────────────────────────────────────────

def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(build_booking_conversation())
    app.add_handler(CallbackQueryHandler(cb_back_main,   pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(cb_contacts,    pattern="^contacts$"))
    app.add_handler(CallbackQueryHandler(cb_my_bookings, pattern="^my_bookings$"))
    app.add_handler(CallbackQueryHandler(cb_cancel_menu, pattern="^cancel_menu$"))
    app.add_handler(CallbackQueryHandler(cb_cancel_id,   pattern=r"^cancel_id_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_do_cancel,   pattern=r"^do_cancel_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_view_booking,pattern=r"^view_booking_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_admin_menu,      pattern="^adm_menu$"))
    app.add_handler(CallbackQueryHandler(cb_adm_today,       pattern="^adm_today$"))
    app.add_handler(CallbackQueryHandler(cb_adm_pick_date,   pattern="^adm_pick_date$"))
    app.add_handler(CallbackQueryHandler(cb_adm_date,        pattern=r"^adm_date_"))
    app.add_handler(CallbackQueryHandler(cb_adm_cancel,      pattern=r"^adm_cancel_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_adm_do_cancel,   pattern=r"^adm_do_cancel_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_adm_block_pick,  pattern="^adm_block_pick$"))
    app.add_handler(CallbackQueryHandler(cb_adm_block_date,  pattern=r"^adm_block_date_"))
    app.add_handler(CallbackQueryHandler(cb_adm_do_block,    pattern=r"^adm_do_block_"))
    app.add_handler(CallbackQueryHandler(cb_adm_block_day_pick, pattern="^adm_block_day_pick$"))
    app.add_handler(CallbackQueryHandler(cb_adm_block_day,   pattern=r"^adm_block_day_"))
    app.add_handler(CallbackQueryHandler(cb_adm_unblock_pick,pattern="^adm_unblock_pick$"))
    app.add_handler(CallbackQueryHandler(cb_adm_unblock_date,pattern=r"^adm_unblock_date_"))
    app.add_handler(CallbackQueryHandler(cb_adm_do_unblock,  pattern=r"^adm_do_unblock_"))
    app.add_handler(CallbackQueryHandler(cb_adm_noop,        pattern="^adm_noop$"))
    app.add_handler(CallbackQueryHandler(cb_adm_stats,       pattern="^adm_stats$"))


# ──────────────────────────────────────────────
# Startup / Shutdown
# ──────────────────────────────────────────────

async def on_startup(app: Application) -> None:
    db.init_db()
    logger.info("✅ Bot started. Database ready.")
    from config import ADMIN_CHAT_ID
    if ADMIN_CHAT_ID:
        try:
            await app.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="✅ <b>Studio Depil Rina Bot</b> запущен!\n\nАдмин-панель: /admin",
                parse_mode="HTML"
            )
        except Exception:
            pass


async def on_shutdown(app: Application) -> None:
    logger.info("🛑 Bot shutting down.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN не задан!")
        sys.exit(1)

    threading.Thread(target=run_health_server, daemon=True).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    register_handlers(app)

    logger.info("🚀 Запуск бота Studio Depil Rina...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
