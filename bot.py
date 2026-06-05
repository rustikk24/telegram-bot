import asyncio
import logging
import sqlite3
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN is not set")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DB =================

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    date TEXT,
    time TEXT,
    price INTEGER,
    room TEXT,
    start_datetime TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER,
    user_id INTEGER
)
""")

conn.commit()

# ================= ROLES =================

OWNERS = {6279994177}  # твой ID
ADMINS = set()
MODS = set()

def role(user_id):
    if user_id in OWNERS:
        return "owner"
    if user_id in ADMINS:
        return "admin"
    if user_id in MODS:
        return "mod"
    return "user"

def can_manage(user_id):
    return role(user_id) in ["owner", "admin"]

# ================= START =================

@dp.message(CommandStart())
async def start(m: Message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.from_user.id,))
    conn.commit()
    await m.answer("👋 Добро пожаловать! Напиши /join чтобы участвовать в турнире")

# ================= CREATE TOURNAMENT =================

tour_state = {}

@dp.message(F.text == "/tour")
async def tour(m: Message):
    if not can_manage(m.from_user.id):
        return await m.answer("❌ Нет доступа")

    tour_state[m.from_user.id] = {}
    await m.answer("🏆 Введи название турнира")

@dp.message()
async def tour_flow(m: Message):
    if m.from_user.id not in tour_state:
        return

    data = tour_state[m.from_user.id]

    if "name" not in data:
        data["name"] = m.text
        return await m.answer("📅 Дата (DD.MM.YYYY)")

    if "date" not in data:
        data["date"] = m.text
        return await m.answer("⏰ Время (HH:MM)")

    if "time" not in data:
        data["time"] = m.text
        return await m.answer("💰 Цена")

    if "price" not in data:
        try:
            data["price"] = int(m.text)
        except:
            return await m.answer("❌ Введи число")

        dt = datetime.strptime(
            f"{data['date']} {data['time']}",
            "%d.%m.%Y %H:%M"
        )

        cursor.execute("""
        INSERT INTO tournaments (name, date, time, price, start_datetime)
        VALUES (?, ?, ?, ?, ?)
        """, (data["name"], data["date"], data["time"], data["price"], dt.isoformat()))

        conn.commit()
        del tour_state[m.from_user.id]

        return await m.answer("✅ Турнир создан")

# ================= JOIN TOURNAMENT =================

@dp.message(F.text == "/join")
async def join(m: Message):
    cursor.execute("SELECT id, name FROM tournaments ORDER BY id DESC LIMIT 1")
    t = cursor.fetchone()

    if not t:
        return await m.answer("❌ Нет турниров")

    cursor.execute("""
    INSERT INTO participants (tournament_id, user_id)
    VALUES (?, ?)
    """, (t[0], m.from_user.id))

    conn.commit()

    await m.answer(f"✅ Ты записан в турнир: {t[1]}")

# ================= PARTICIPANTS =================

@dp.message(F.text == "/players")
async def players(m: Message):
    cursor.execute("SELECT id FROM tournaments ORDER BY id DESC LIMIT 1")
    t = cursor.fetchone()

    if not t:
        return await m.answer("❌ Нет турнира")

    cursor.execute("""
    SELECT user_id FROM participants WHERE tournament_id=?
    """, (t[0],))

    users = cursor.fetchall()

    text = "👥 Участники:\n"
    for u in users:
        text += f"- {u[0]}\n"

    await m.answer(text)

# ================= ROOM =================

@dp.message(F.text.startswith("/room"))
async def room(m: Message):
    if not can_manage(m.from_user.id):
        return

    try:
        link = m.text.split(" ", 1)[1]
    except:
        return await m.answer("❌ /room ссылка")

    cursor.execute("""
    UPDATE tournaments
    SET room = ?
    ORDER BY id DESC
    LIMIT 1
    """, (link,))

    conn.commit()

    await m.answer("🎮 Рума добавлена")

# ================= BROADCAST =================

@dp.message(F.text.startswith("/send"))
async def send_all(m: Message):
    if not can_manage(m.from_user.id):
        return

    text = m.text.replace("/send", "").strip()

    users = cursor.execute("SELECT user_id FROM users").fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

    await m.answer("📢 Рассылка отправлена")

# ================= MAIN =================

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
    
