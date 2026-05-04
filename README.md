# 💆 Studio Depil Rina — Telegram Bot

Профессиональный Telegram-бот для записи клиентов на депиляцию.  
Разработан на `python-telegram-bot v20+` с асинхронным кодом и SQLite.

---

## 📁 Структура проекта

```
depil_bot/
├── bot.py                  # Точка входа, регистрация хендлеров
├── config.py               # Все настройки (услуги, расписание, токен)
├── database.py             # SQLite: клиенты и записи
├── keyboards.py            # Все InlineKeyboard-клавиатуры
├── requirements.txt        # Зависимости
├── .env.example            # Пример файла переменных окружения
├── handlers/
│   ├── user_handlers.py    # /start, меню, контакты, мои записи
│   ├── booking_handlers.py # Полный flow записи (ConversationHandler)
│   └── admin_handlers.py   # Отмена записи + уведомления администратора
```

---

## ⚙️ Установка

### 1. Требования

- Python **3.11** или новее
- pip

### 2. Клонирование / распаковка проекта

```bash
cd depil_bot
```

### 3. Виртуальное окружение (рекомендуется)

```bash
python3 -m venv venv
source venv/bin/activate       # Linux / macOS
# или
venv\Scripts\activate          # Windows
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

---

## 🔑 Настройка

### Шаг 1 — Создайте бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Задайте имя и username
4. Скопируйте **токен** (выглядит как `1234567890:ABCDef...`)

### Шаг 2 — Узнайте ваш Chat ID

1. Напишите [@userinfobot](https://t.me/userinfobot)
2. Скопируйте число из поля **Id**

### Шаг 3 — Настройте `config.py`

Откройте `config.py` и замените:

```python
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
#                                         ↑ вставьте ваш токен

ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))
#                                                      ↑ вставьте ваш Chat ID
```

**Либо** (рекомендуется) создайте файл `.env`:

```bash
cp .env.example .env
nano .env          # или откройте в любом редакторе
```

Заполните значения в `.env`:

```
BOT_TOKEN=1234567890:ABCDefGhIJKLmnoPQRSTuvwxyz
ADMIN_CHAT_ID=123456789
```

И установите `python-dotenv`:

```bash
pip install python-dotenv
```

Добавьте в начало `config.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## ▶️ Запуск

```bash
python bot.py
```

При первом запуске автоматически создаётся база данных `depil_studio.db`.

Вы увидите в консоли:
```
2024-01-01 10:00:00 | INFO     | __main__: 🚀 Запуск бота Studio Depil Rina...
2024-01-01 10:00:01 | INFO     | database: Database initialised at depil_studio.db
2024-01-01 10:00:01 | INFO     | __main__: ✅ Bot started. Database ready.
```

---

## 🔄 Запуск как сервис (Linux / systemd)

Создайте файл `/etc/systemd/system/depil_bot.service`:

```ini
[Unit]
Description=Studio Depil Rina Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/depil_bot
ExecStart=/home/ubuntu/depil_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable depil_bot
sudo systemctl start depil_bot
sudo systemctl status depil_bot

# Логи:
sudo journalctl -u depil_bot -f
```

---

## 📋 Редактирование услуг

Все услуги находятся в `config.py` в списке `SERVICES`:

```python
SERVICES = [
    {"id": "armpit", "name": "Подмышки", "price": "от 50 000 сум", "emoji": "💪"},
    # Добавьте свои услуги по тому же шаблону
]
```

**Для добавления услуги** — добавьте новый dict в список.  
**Для изменения цены** — измените значение `"price"`.  
**Для удаления** — удалите строку.

---

## ⏰ Изменение рабочего времени

В `config.py`:

```python
WORK_START_HOUR: int = 10   # Начало рабочего дня (10:00)
WORK_END_HOUR: int = 20     # Конец (последний слот 19:00)
SLOT_DURATION_HOURS: int = 1
BOOKING_DAYS_AHEAD: int = 14  # На сколько дней вперёд открыта запись
```

---

## 📊 Просмотр базы данных

```bash
sqlite3 depil_studio.db

# Просмотр всех записей:
SELECT * FROM bookings ORDER BY booking_date, booking_time;

# Записи за сегодня:
SELECT b.*, c.full_name, c.phone
FROM bookings b JOIN clients c ON c.id = b.client_id
WHERE b.booking_date = date('now','localtime') AND b.status = 'active';

# Все клиенты:
SELECT * FROM clients;
```

---

## 🤖 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск / главное меню |
| `/help` | Справка |
| `/cancel` | Прервать текущий диалог |

---

## ✅ Функционал

### Клиент:
- 📅 Записаться (выбор услуги → дата → время → имя → телефон → подтверждение)
- 🗂 Мои записи — просмотр всех активных записей
- ❌ Отменить запись — с подтверждением
- 📞 Контакты студии

### Администратор:
- 🔔 Уведомление о **новой записи** (имя, телефон, услуга, дата, время, @username)
- ⚠️ Уведомление об **отмене** с информацией о клиенте
- 🟢 Освобождение слота при отмене

### Защита от конфликтов:
- 🔴 Занятые слоты отображаются серым и недоступны для выбора
- Двойная проверка при подтверждении (race condition protection)

---

## 📞 Контакты

**Studio Depil Rina**  
Мастер: Рина  
📱 +998 99 851-73-55  
📍 Ташкент
