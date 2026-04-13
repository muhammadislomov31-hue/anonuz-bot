import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

TOKEN = os.getenv("8567827882:AAF74VcAeGdbKUpwWvOn1ixe4Ej4pEZ8-LE")

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 5315803004

users = {}
waiting_users = []
active_chats = {}

# ================= КНОПКИ =================

age_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="12–14"), KeyboardButton(text="15–17"), KeyboardButton(text="18+")]],
    resize_keyboard=True
)

gender_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")]],
    resize_keyboard=True
)

regions_list = [
    "Ташкент", "Самарканд", "Бухара", "Фергана", "Андижан", "Наманган",
    "Хорезм", "Кашкадарья", "Сурхандарья", "Джизак", "Навои", "Сырдарья"
]

def region_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=r)] for r in regions_list],
        resize_keyboard=True
    )

start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚀 Начать поиск")]],
    resize_keyboard=True
)

chat_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="▶️ Next"), KeyboardButton(text="⛔ Stop")],
        [KeyboardButton(text="🚨 Report")]
    ],
    resize_keyboard=True
)

# ================= START =================
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Выберите ваш возраст:", reply_markup=age_kb)

# ================= REGISTRATION =================
@dp.message(lambda m: m.text in ["12–14", "15–17", "18+"])
async def age_handler(message: types.Message):
    users[message.from_user.id] = {"age": message.text}
    await message.answer("Выберите ваш пол:", reply_markup=gender_kb)

@dp.message(lambda m: m.text in ["👨 Мужской", "👩 Женский"])
async def gender_handler(message: types.Message):
    users[message.from_user.id]["gender"] = "male" if "Мужской" in message.text else "female"
    await message.answer("Выберите ваш регион:", reply_markup=region_kb())

@dp.message(lambda m: m.text in regions_list)
async def region_handler(message: types.Message):
    users[message.from_user.id]["region"] = message.text
    await message.answer("✅ Регистрация завершена!\n\nНажмите «Начать поиск»", reply_markup=start_kb)

# ================= HELPER =================
def ensure_user(user_id):
    # 🔥 auto-fix if Railway restarted
    if user_id not in users:
        users[user_id] = {
            "age": "18+",
            "gender": "male",
            "region": "Ташкент"
        }

def is_compatible(u1, u2):
    return u1["gender"] != u2["gender"]

# ================= SEARCH =================
@dp.message(lambda m: m.text == "🚀 Начать поиск")
async def search_handler(message: types.Message):
    user_id = message.from_user.id
    ensure_user(user_id)

    if user_id in waiting_users:
        waiting_users.remove(user_id)

    for partner in waiting_users:
        if is_compatible(users[user_id], users[partner]):
            waiting_users.remove(partner)
            active_chats[user_id] = partner
            active_chats[partner] = user_id

            await bot.send_message(user_id, "💬 Собеседник найден!", reply_markup=chat_kb)
            await bot.send_message(partner, "💬 Собеседник найден!", reply_markup=chat_kb)
            return

    waiting_users.append(user_id)
    await message.answer("⏳ Поиск собеседника...", reply_markup=chat_kb)

# ================= NEXT =================
@dp.message(lambda m: m.text == "▶️ Next")
async def next_handler(message: types.Message):
    user_id = message.from_user.id
    ensure_user(user_id)

    if user_id in active_chats:
        partner = active_chats[user_id]
        active_chats.pop(user_id, None)
        active_chats.pop(partner, None)

        await bot.send_message(partner, "🔄 Собеседник переключился.", reply_markup=chat_kb)

    if user_id in waiting_users:
        waiting_users.remove(user_id)

    for partner in waiting_users:
        if is_compatible(users[user_id], users[partner]):
            waiting_users.remove(partner)
            active_chats[user_id] = partner
            active_chats[partner] = user_id

            await bot.send_message(user_id, "💬 Новый собеседник найден!", reply_markup=chat_kb)
            await bot.send_message(partner, "💬 Новый собеседник найден!", reply_markup=chat_kb)
            return

    waiting_users.append(user_id)
    await message.answer("⏳ Ищем нового собеседника...", reply_markup=chat_kb)

# ================= STOP =================
@dp.message(lambda m: m.text == "⛔ Stop")
async def stop_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id in active_chats:
        partner = active_chats[user_id]
        active_chats.pop(user_id, None)
        active_chats.pop(partner, None)
        await bot.send_message(partner, "❌ Диалог завершён.", reply_markup=start_kb)

    if user_id in waiting_users:
        waiting_users.remove(user_id)

    await message.answer("❌ Вы завершили диалог.\n\nНажмите «Начать поиск»", reply_markup=start_kb)

# ================= REPORT =================
@dp.message(lambda m: m.text == "🚨 Report")
async def report_handler(message: types.Message):
    user_id = message.from_user.id
    partner = active_chats.get(user_id)

    if not partner:
        await message.answer("❌ Нет активного диалога.")
        return

    await bot.send_message(ADMIN_ID, f"🚨 Жалоба!\nОт: {user_id}\nНа: {partner}")
    await message.answer("✅ Жалоба отправлена.")

    active_chats.pop(user_id, None)
    active_chats.pop(partner, None)

    await bot.send_message(partner, "⚠️ На вас пожаловались. Диалог завершён.", reply_markup=start_kb)
    await message.answer("❌ Диалог завершён.", reply_markup=start_kb)

# ================= RELAY =================
@dp.message()
async def relay_handler(message: types.Message):
    user_id = message.from_user.id
    partner = active_chats.get(user_id)

    if partner:
        await bot.copy_message(chat_id=partner, from_chat_id=user_id, message_id=message.message_id)

# ================= RUN =================
async def main():
    print("🔥 Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
