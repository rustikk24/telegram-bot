import asyncio
import logging
import sqlite3
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

# ================= CONFIG =================
import os
TOKEN = os.getenv("TOKEN")
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

conn.commit()

# ================= ROLE (simple) =================
OWNERS = {123456789}  # <-- вставь свой ID

def is_owner(user_id: int):
    return user_id in OWNERS

# ================= START =================
@dp.message(CommandStart())
async def start(m: Message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.from_user.id,))
    conn.commit()

    await m.answer("👋 Бот работает!")

# ================= CREATE TOURNAMENT =================
tour_state = {}

@dp.message(F.text == "/tour")
async def tour(m: Message):
    if not is_owner(m.from_user.id):
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
        data["price"] = int(m.text)

        dt = datetime.strptime(
            data["date"] + " " + data["time"],
            "%d.%m.%Y %H:%M"
        )

        cursor.execute("""
        INSERT INTO tournaments (name,date,time,price,start_datetime)
        VALUES (?,?,?,?,?)
        """, (data["name"], data["date"], data["time"], data["price"], dt.isoformat()))

        conn.commit()
        del tour_state[m.from_user.id]

        return await m.answer("✅ Турнир создан")

# ================= ROOM =================
@dp.message(F.text.startswith("/room"))
async def room(m: Message):
    if not is_owner(m.from_user.id):
        return

    try:
        link = m.text.split(" ", 1)[1]
    except:
        return await m.answer("❌ Формат: /room ссылка")

    cursor.execute("""
    UPDATE tournaments
    SET room=?
    ORDER BY id DESC
    LIMIT 1
    """, (link,))

    conn.commit()

    await m.answer("🎮 Рума добавлена")

# ================= BROADCAST =================
@dp.message(F.text.startswith("/send"))
async def send_all(m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text.replace("/send", "").strip()

    users = cursor.execute("SELECT user_id FROM users").fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

    await m.answer("📢 Рассылка отправлена")

# ================= RUN BOT =================
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
