import asyncio
import os
import tempfile
import time
import zipfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

TOKEN = "8749394795:AAGkfPTC3lkFKCMYT52F9Y1FdHoBztk_b78"
ADMIN_ID = int(os.getenv("ADMIN_ID") or 6667142324)

USERS_FILE = "users.txt"
ISSUED_FILE = "issued_users.txt"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def load_ids(filename: str) -> set[int]:
    if not os.path.exists(filename):
        return set()

    result = set()
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.isdigit():
                result.add(int(line))
    return result

def append_id(filename: str, user_id: int) -> None:
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{user_id}\n")

users = load_ids(USERS_FILE)
issued_users = load_ids(ISSUED_FILE)

waiting_question = set()
admin_reply_map: dict[int, int] = {}
admin_state: dict[int, str] = {}

def add_user(user_id: int) -> None:
    if user_id not in users:
        users.add(user_id)
        append_id(USERS_FILE, user_id)

def was_issued(user_id: int) -> bool:
    return user_id in issued_users

def mark_issued(user_id: int) -> None:
    if user_id not in issued_users:
        issued_users.add(user_id)
        append_id(ISSUED_FILE, user_id)

def build_personal_zip(user_id: int, username: str | None = None) -> str:
    source_zip = Path("dll.zip")

    if not source_zip.exists():
        raise FileNotFoundError("Файл dll.zip не найден")

    temp_dir = Path(tempfile.mkdtemp())
    extract_dir = temp_dir / "content"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip, "r") as zf:
        zf.extractall(extract_dir)

    info_text = (
        f"Buyer ID: {user_id}\n"
        f"Username: @{username if username else 'none'}\n"
        f"Issue time: {int(time.time())}\n"
        f"Redistribution is prohibited.\n"
    )

    (extract_dir / "buyer_info.txt").write_text(info_text, encoding="utf-8")

    output_zip = temp_dir / f"dll_{user_id}.zip"
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in extract_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(extract_dir))

    return str(output_zip)

async def send_product(target_id: int, force: bool = False) -> None:
    if was_issued(target_id) and not force:
        raise ValueError("Этому пользователю товар уже выдавался")

    chat = await bot.get_chat(target_id)
    personal_zip_path = build_personal_zip(target_id, getattr(chat, "username", None))

    zip_file = FSInputFile(personal_zip_path)
    await bot.send_document(
        target_id,
        zip_file,
        caption="✅ Спасибо за покупку! Вот ваш DLL файл:"
    )

    video_path = Path("instruction.mp4")
    if video_path.exists():
        video_file = FSInputFile("instruction.mp4")
        await bot.send_video(
            target_id,
            video_file,
            caption="📄 Видеоинструкция: как использовать DLL"
        )

    if not was_issued(target_id):
        mark_issued(target_id)

async def send_to_admin_with_link(source_message: types.Message, header_text: str) -> None:
    sent_header = await bot.send_message(ADMIN_ID, header_text)

    forwarded = await bot.forward_message(
        ADMIN_ID,
        from_chat_id=source_message.chat.id,
        message_id=source_message.message_id
    )

    admin_reply_map[sent_header.message_id] = source_message.from_user.id
    admin_reply_map[forwarded.message_id] = source_message.from_user.id

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Купить"), KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="🛠 Админ панель")]
    ],
    resize_keyboard=True
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Выдать товар"), KeyboardButton(text="🔁 Повторно выдать")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="📨 Рассылка")],
        [KeyboardButton(text="🏠 Меню пользователя")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    add_user(message.from_user.id)

    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👋 Привет, админ. Открываю админ-панель.",
            reply_markup=admin_keyboard
        )
        return

    await message.answer(
        "👋 Привет!\nDLL стоит 60₽ / 100 голды\nВыберите действие:",
        reply_markup=user_keyboard
    )

@dp.message(Command("admin"))
async def admin_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    await message.answer("🛠 Админ панель", reply_markup=admin_keyboard)

@dp.message(Command("resend"))
async def resend_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /resend user_id")
        return

    target_id = int(parts[1])

    try:
        await send_product(target_id, force=True)
        await message.answer(f"✅ Повторная выдача отправлена пользователю {target_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка повторной выдачи: {e}")

@dp.message(F.text == "🛠 Админ панель")
async def open_admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    await message.answer("🛠 Админ панель", reply_markup=admin_keyboard)

@dp.message(F.text == "🏠 Меню пользователя")
async def open_user_menu(message: types.Message):
    await message.answer("🏠 Меню пользователя открыто.", reply_markup=user_keyboard)

@dp.message(F.text == "💰 Купить")
async def buy_handler(message: types.Message):
    add_user(message.from_user.id)

    await message.answer("💳 После оплаты отправьте сюда скриншот оплаты.")

    await send_to_admin_with_link(
        message,
        f"🛒 Новый покупатель\n"
        f"ID: {message.from_user.id}\n"
        f"Уже выдано: {'Да' if was_issued(message.from_user.id) else 'Нет'}\n\n"
        f"Ответь реплаем:\n"
        f"+ — выдать DLL\n"
        f"обычным текстом — ответить пользователю"
    )

@dp.message(F.text == "❓ Задать вопрос")
async def ask_question_handler(message: types.Message):
    add_user(message.from_user.id)
    waiting_question.add(message.from_user.id)
    await message.answer("✍️ Напишите ваш вопрос одним сообщением.")

@dp.message(F.text == "📦 Выдать товар")
async def give_product_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_state[ADMIN_ID] = "waiting_give_id"
    await message.answer("Введите ID пользователя для выдачи товара.")

@dp.message(F.text == "🔁 Повторно выдать")
async def resend_product_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_state[ADMIN_ID] = "waiting_resend_id"
    await message.answer("Введите ID пользователя для повторной выдачи товара.")

@dp.message(F.text == "📊 Статистика")
async def stats_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        f"📊 Статистика:\n\n"
        f"Всего пользователей: {len(users)}\n"
        f"Выдано товаров: {len(issued_users)}"
    )

@dp.message(F.text == "👥 Пользователи")
async def users_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not users:
        await message.answer("Пользователей пока нет.")
        return

    text = "👥 Пользователи:\n\n" + "\n".join(str(uid) for


uid in sorted(users))
    await message.answer(text[:4000])

@dp.message(F.text == "📨 Рассылка")
async def broadcast_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_state[ADMIN_ID] = "waiting_broadcast"
    await message.answer("Введите текст для рассылки всем пользователям.")

@dp.message(F.photo)
async def photo_handler(message: types.Message):
    add_user(message.from_user.id)

    await send_to_admin_with_link(
        message,
        f"🧾 Пользователь отправил скрин оплаты\n"
        f"ID: {message.from_user.id}\n"
        f"Уже выдано: {'Да' if was_issued(message.from_user.id) else 'Нет'}\n\n"
        f"Ответь реплаем:\n"
        f"+ — выдать DLL\n"
        f"обычным текстом — ответить пользователю"
    )

    await message.answer("✅ Скрин отправлен администратору.")

@dp.message()
async def text_handler(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""

    add_user(user_id)

    if user_id == ADMIN_ID:
        state = admin_state.get(ADMIN_ID)

        if state == "waiting_give_id":
            if not text.isdigit():
                await message.answer("❌ ID должен состоять только из цифр.")
                return

            target_id = int(text)
            try:
                await send_product(target_id, force=False)
                await message.answer(f"✅ Товар выдан пользователю {target_id}")
            except Exception as e:
                await message.answer(f"❌ {e}")

            admin_state.pop(ADMIN_ID, None)
            return

        if state == "waiting_resend_id":
            if not text.isdigit():
                await message.answer("❌ ID должен состоять только из цифр.")
                return

            target_id = int(text)
            try:
                await send_product(target_id, force=True)
                await message.answer(f"✅ Повторная выдача отправлена пользователю {target_id}")
            except Exception as e:
                await message.answer(f"❌ {e}")

            admin_state.pop(ADMIN_ID, None)
            return

        if state == "waiting_broadcast":
            success = 0
            failed = 0

            for uid in users:
                try:
                    await bot.send_message(uid, f"📢 Сообщение от администрации:\n\n{text}")
                    success += 1
                except Exception:
                    failed += 1

            await message.answer(
                f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {failed}"
            )
            admin_state.pop(ADMIN_ID, None)
            return

        if message.reply_to_message:
            replied_message_id = message.reply_to_message.message_id
            target_id = admin_reply_map.get(replied_message_id)

            if target_id:
                if text.strip().lower() in ["+", "/send", "выдать"]:
                    try:
                        await send_product(target_id, force=False)
                        await message.answer(f"✅ Товар выдан пользователю {target_id}")
                    except Exception as e:
                        await message.answer(f"❌ {e}")
                    return

                await bot.send_message(
                    target_id,
                    f"📩 Ответ администратора:\n\n{text}"
                )

                await message.answer(f"✅ Ответ отправлен пользователю {target_id}")
                return

    if user_id in waiting_question:
        waiting_question.remove(user_id)

        await send_to_admin_with_link(
            message,
            f"❓ Вопрос от пользователя\n"
            f"ID: {user_id}\n\n"
            f"Ответьте реплаем обычным текстом, чтобы ответить пользователю"
        )

        await message.answer("✅ Вопрос отправлен администратору")
        return

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


