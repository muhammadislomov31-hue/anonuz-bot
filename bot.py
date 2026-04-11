import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

import os

TOKEN = os.getenv("TOKEN") or "8567827882:AAF74VcAeGdbKUpwWvOn1ixe4Ej4pEZ8-LE"
ADMIN_ID = 5315803004

bot = Bot(token=TOKEN)
dp = Dispatcher()

users = {}
active_chats = {}
waiting_users = []

regions = [
    "Ташкент", "Самарканд", "Бухара", "Фергана",
    "Андижан", "Наманган", "Сурхандарья",
    "Кашкадарья", "Хорезм", "Сырдарья",
    "Джизак", "Навои", "Каракалпакстан"
]

genders = ["Мужчина", "Женщина"]
ages = ["12-15", "16-18", "18+"]


# ================= START / RESTART =================
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=r, callback_data=f"region:{r}")]
            for r in regions
        ]
    )

    users.pop(user_id, None)
    active_chats.pop(user_id, None)

    await message.answer("Выберите ваш регион:", reply_markup=keyboard)


# ================= REGION =================
@dp.callback_query(lambda c: c.data.startswith("region:"))
async def region_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    region = callback.data.split(":")[1]

    users[user_id] = {"region": region}

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=g, callback_data=f"gender:{g}")]
            for g in genders
        ]
    )

    await callback.message.edit_text("Выберите ваш пол:", reply_markup=keyboard)


# ================= GENDER =================
@dp.callback_query(lambda c: c.data.startswith("gender:"))
async def gender_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    gender = callback.data.split(":")[1]

    users[user_id]["gender"] = gender

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=a, callback_data=f"age:{a}")]
            for a in ages
        ]
    )

    await callback.message.edit_text("Выберите ваш возраст:", reply_markup=keyboard)


# ================= AGE =================
@dp.callback_query(lambda c: c.data.startswith("age:"))
async def age_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    age = callback.data.split(":")[1]

    users[user_id]["age"] = age

    await callback.message.edit_text(
        "Регистрация завершена ✅\n\n"
        "Используйте:\n"
        "/next — новый диалог\n"
        "/stop — остановить\n"
        "/start — изменить данные"
    )


# ================= NEXT =================
@dp.message(Command("next"))
async def next_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id not in users:
        await message.answer("Сначала используйте /start")
        return

    # если уже в чате → завершить и искать нового
    if user_id in active_chats:
        await stop_chat(user_id, notify_partner=True)

    # поиск
    for partner_id in waiting_users:
        if partner_id == user_id:
            continue

        if (
            users[partner_id]["region"] == users[user_id]["region"]
            and users[partner_id]["gender"] != users[user_id]["gender"]
            and users[partner_id]["age"] == users[user_id]["age"]
        ):
            waiting_users.remove(partner_id)

            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Next", callback_data="next_btn"),
                        InlineKeyboardButton(text="Stop", callback_data="stop_btn")
                    ]
                ]
            )

            text = "Собеседник найден, приятного общения!"
            await bot.send_message(user_id, text, reply_markup=keyboard)
            await bot.send_message(partner_id, text, reply_markup=keyboard)
            return

    if user_id not in waiting_users:
        waiting_users.append(user_id)

    await message.answer("Ожидаем собеседника...")


# ================= STOP =================
@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    user_id = message.from_user.id

    if user_id not in active_chats:
        await message.answer("Вы не в диалоге.")
        return

    await stop_chat(user_id, notify_partner=True)

    # После стоп даём кнопки Next | Report
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Next", callback_data="next_btn"),
                InlineKeyboardButton(text="Report", callback_data="report_btn")
            ]
        ]
    )
    await message.answer(
        "Диалог остановлен. Теперь вы можете начать новый диалог или отправить жалобу.",
        reply_markup=keyboard
    )


async def stop_chat(user_id, notify_partner=True):
    partner_id = active_chats.get(user_id)
    if not partner_id:
        return

    if notify_partner:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Next", callback_data="next_btn"),
                    InlineKeyboardButton(text="Report", callback_data="report_btn")
                ]
            ]
        )
        await bot.send_message(
            partner_id,
            "Собеседник завершил диалог.",
            reply_markup=keyboard
        )

    active_chats.pop(user_id, None)
    active_chats.pop(partner_id, None)


# ================= BUTTONS =================
@dp.callback_query(lambda c: c.data in ["next_btn", "stop_btn", "report_btn"])
async def buttons_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "report_btn":
        await bot.send_message(
            ADMIN_ID,
            f"🚨 Жалоба\nОт: {user_id}"
        )
        await callback.message.answer("Жалоба отправлена администратору.")
        return

    if callback.data == "stop_btn":
        await stop_command(callback.message)

    if callback.data == "next_btn":
        await next_handler(callback.message)


# ================= RELAY =================
@dp.message()
async def relay_handler(message: types.Message):
    user_id = message.from_user.id
    partner_id = active_chats.get(user_id)

    if not partner_id:
        return

    await bot.copy_message(
        chat_id=partner_id,
        from_chat_id=user_id,
        message_id=message.message_id
    )


# ================= RUN =================
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
