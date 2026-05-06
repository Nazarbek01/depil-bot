# ============================================================
#  config.py — Studio Depil Rina · Telegram Bot Configuration
# ============================================================

import os
from dataclasses import dataclass, field
from typing import List

# ──────────────────────────────────────────────
# Токен бота (замените или задайте в .env)
# ──────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ──────────────────────────────────────────────
# Telegram ID администратора / мастера
# Узнать свой ID: @userinfobot
# ──────────────────────────────────────────────
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0")) # ← замените на ваш ID

# ──────────────────────────────────────────────
# База данных
# ──────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "depil_studio.db")

# ──────────────────────────────────────────────
# Информация о студии
# ──────────────────────────────────────────────
STUDIO_NAME: str = "Studio Depil Rina"
MASTER_NAME: str = "Рина"
STUDIO_PHONE: str = "+998 99 851-73-55"
STUDIO_CITY: str = "Ташкент"
STUDIO_INSTAGRAM: str = "@studio_depil_rina"  # опционально

# ──────────────────────────────────────────────
# Рабочее расписание
# ──────────────────────────────────────────────
WORK_START_HOUR: int = 10   # 10:00
WORK_END_HOUR: int = 20     # последний слот в 19:00 (сеанс до 20:00)
SLOT_DURATION_HOURS: int = 1

# Слоты времени (генерируются автоматически)
TIME_SLOTS: List[str] = [
    f"{h:02d}:00" for h in range(WORK_START_HOUR, WORK_END_HOUR)
]

# ──────────────────────────────────────────────
# Услуги — легко редактировать!
# Формат: {"id": "...", "name": "...", "price": "..."}
# ──────────────────────────────────────────────
SERVICES = [
    {"id": "armpit",        "name": "Подмышки",          "price": "от 50 000 сум",  "emoji": "💪"},
    {"id": "bikini_classic","name": "Бикини классика",   "price": "от 80 000 сум",  "emoji": "🌸"},
    {"id": "bikini_deep",   "name": "Бикини глубокое",   "price": "от 120 000 сум", "emoji": "✨"},
    {"id": "legs_full",     "name": "Ноги полностью",    "price": "от 150 000 сум", "emoji": "🦵"},
    {"id": "arms",          "name": "Руки",              "price": "от 90 000 сум",  "emoji": "🙌"},
    {"id": "face",          "name": "Лицо",              "price": "от 60 000 сум",  "emoji": "🧖"},
]

# Сколько дней вперёд доступна запись
BOOKING_DAYS_AHEAD: int = 14
