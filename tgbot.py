import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8749394795:AAGzNQP7S82ddWWqLT4dNzMfDnpOU20E8-I"
ADMIN_ID = 6667142324   # твой telegram id

bot = Bot(token=TOKEN)
dp = Dispatcher()

answered_users = set()

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Купить")],
        [KeyboardButton(text="❓ Задать вопрос")]
    ],
    resize_keyboard=True
)


@dp.message()
async def messages(message: types.Message):

    user_id = message.from_user.id

    # сообщение админа (ответ пользователю)
    if user_id == ADMIN_ID and message.reply_to_message:
        text = message.reply_to_message.text

        if "ID:" in text:
            uid = int(text.split("ID:")[1])
            await bot.send_message(uid, message.text)
        return


    # первое сообщение пользователя
    if user_id not in answered_users:
        answered_users.add(user_id)

        await message.answer(
            "👋 Привет\n\n"
            "Дополнение к игре (DLC)\n"
            "💰 Цена: 120₽ / 65⭐ / 200 голды",
            reply_markup=keyboard
        )
        return


    # купить
    if message.text == "💰 Купить":
        await message.answer(
            "💳 Для покупки напишите админу.\n"
            "После оплаты вам будет выдан файл."
        )

        await bot.send_message(
            ADMIN_ID,
            f"🛒 Пользователь хочет купить\nID:{user_id}"
        )
        return


    # задать вопрос
    if message.text == "❓ Задать вопрос":
        await message.answer("✉️ Напишите ваш вопрос.")

        await bot.send_message(
            ADMIN_ID,
            f"❓ Вопрос от пользователя\nID:{user_id}"
        )
        return


    # обычное сообщение пользователя → пересылаем админу
    await bot.send_message(
        ADMIN_ID,
        f"💬 Сообщение\nID:{user_id}\n\n{message.text}"
    )


async def main():
    await dp.start_polling(bot)

asyncio.run(main())
