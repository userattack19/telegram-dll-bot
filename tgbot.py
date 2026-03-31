import telebot  # библиотека Telegram
import os  # работа с системой
import json  # хранение товаров
import tempfile  # временные файлы
import zipfile  # работа с архивами
import shutil  # удаление файлов
from pathlib import Path  # пути
import time  # время

TOKEN = os.getenv("BOT_TOKEN")  # токен бота
ADMIN_ID = int(os.getenv("ADMIN_ID") or 6667142324)  # ID админа

bot = telebot.TeleBot(TOKEN)  # создаём бота

PRODUCTS_FILE = "products.json"  # файл товаров

# ===== загрузка товаров =====
def load_products():  # функция загрузки
    if not os.path.exists(PRODUCTS_FILE):  # если нет файла
        return {}  # пусто
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:  # открываем
        return json.load(f)  # читаем JSON

def save_products(products):  # сохранение товаров
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:  # открываем
        json.dump(products, f, ensure_ascii=False, indent=2)  # записываем

products = load_products()  # загружаем товары

admin_state = {}  # состояние админа

# ===== создание архива =====
def build_zip(product_path, user_id, username=None):  # создаём уникальный архив
    temp_dir = Path(tempfile.mkdtemp())  # временная папка
    extract_dir = temp_dir / "content"  # папка распаковки
    extract_dir.mkdir()  # создаём папку

    with zipfile.ZipFile(product_path, "r") as zf:  # открываем архив
        zf.extractall(extract_dir)  # распаковываем

    info = f"ID: {user_id}\nUser: @{username}\nTime: {int(time.time())}"  # инфо
    (extract_dir / "info.txt").write_text(info)  # записываем файл

    output = temp_dir / f"product_{user_id}.zip"  # путь нового архива

    with zipfile.ZipFile(output, "w") as zf:  # создаём новый архив
        for file in extract_dir.rglob("*"):  # перебираем файлы
            if file.is_file():  # если файл
                zf.write(file, file.relative_to(extract_dir))  # добавляем

    return str(output)  # возвращаем путь

# ===== отправка товара =====
def send_product(user_id, product_name):  # отправка товара
    product = products.get(product_name)  # получаем товар
    if not product:  # если нет
        raise Exception("Товар не найден")  # ошибка

    try:
        chat = bot.get_chat(user_id)  # получаем чат
        username = chat.username  # username
    except:
        username = None  # если ошибка

    zip_path = build_zip(product["file"], user_id, username)  # создаём архив

    with open(zip_path, "rb") as f:  # открываем
        bot.send_document(user_id, f, caption=f"✅ Ваш товар: {product_name}")  # отправляем

    shutil.rmtree(Path(zip_path).parent, ignore_errors=True)  # удаляем временные файлы

# ===== клавиатуры =====
def user_kb():  # меню пользователя
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)  # создаём клаву
    kb.row("🛒 Товары")  # список товаров
    kb.row("🎮 Кастомный Bluestacks")  # кнопка Bluestacks
    kb.row("🧠 Читы (Undetect)")  # кнопка читов
    kb.row("❓ Вопрос")  # вопрос
    return kb  # возвращаем

def admin_kb():  # меню админа
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)  # клавиатура
    kb.row("➕ Добавить товар")  # добавить товар
    kb.row("📦 Список товаров")  # список товаров
    return kb  # вернуть

# ===== старт =====
@bot.message_handler(commands=['start'])  # команда /start
def start(message):
    if message.from_user.id == ADMIN_ID:  # если админ
        bot.send_message(message.chat.id, "Админ панель", reply_markup=admin_kb())  # админ меню
    else:
        bot.send_message(message.chat.id, "Меню", reply_markup=user_kb())  # пользовательское меню

# ===== список товаров =====
@bot.message_handler(func=lambda m: m.text == "🛒 Товары")  # кнопка товаров
def show_products(message):
    if not products:  # если нет товаров
        bot.send_message(message.chat.id, "❌ Товаров нет")  # сообщение
        return

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)  # клавиатура

    for name in products:  # перебор товаров
        kb.row(f"Купить {name}")  # кнопка покупки

    bot.send_message(message.chat.id, "Выберите товар:", reply_markup=kb)  # отправка

# ===== кастомный Bluestacks =====
@bot.message_handler(func=lambda m: m.text == "🎮 Кастомный Bluestacks")  # кнопка
def bluestacks_handler(message):
    product_name = "Bluestacks"  # имя товара

    if product_name not in products:  # если нет
        bot.send_message(message.chat.id, "❌ Товар недоступен")  # ошибка
        return

    bot.send_message(message.chat.id, "💰 Отправьте скрин оплаты (Bluestacks)")  # инструкция

    bot.send_message(ADMIN_ID, f"🛒 Покупка Bluestacks\nID: {message.from_user.id}")  # админу

# ===== читы =====
@bot.message_handler(func=lambda m: m.text == "🧠 Читы (Undetect)")  # кнопка
def cheats_handler(message):
    product_name = "Cheats"  # имя товара

    if product_name not in products:  # если нет
        bot.send_message(message.chat.id, "❌ Товар недоступен")  # ошибка
        return

    bot.send_message(message.chat.id, "💰 Отправьте скрин оплаты (Читы)")  # инструкция

    bot.send_message(ADMIN_ID, f"🛒 Покупка Cheats\nID: {message.from_user.id}")  # админу

# ===== добавить товар =====
@bot.message_handler(func=lambda m: m.text == "➕ Добавить товар")  # кнопка
def add_product(message):
    if message.from_user.id != ADMIN_ID:  # если не админ
        return

    admin_state["mode"] = "name"  # ждём название
    bot.send_message(message.chat.id, "Введите название товара")  # запрос

# ===== загрузка файла =====
@bot.message_handler(content_types=['document'])  # получение файла
def upload_file(message):
    if message.from_user.id != ADMIN_ID:  # только админ
        return

    if admin_state.get("mode") == "file":  # если ждём файл
        file_info = bot.get_file(message.document.file_id)  # получаем инфо
        downloaded = bot.download_file(file_info.file_path)  # скачиваем

        file_path = message.document.file_name  # имя файла

        with open(file_path, "wb") as f:  # сохраняем
            f.write(downloaded)

        name = admin_state["name"]  # имя товара

        products[name] = {"file": file_path}  # добавляем товар

        save_products(products)  # сохраняем

        bot.send_message(message.chat.id, f"✅ Товар {name} добавлен")  # успех

        admin_state.clear()  # сброс состояния

# ===== текст =====
@bot.message_handler(func=lambda m: True)  # обработка текста
def text_handler(message):
    if message.from_user.id != ADMIN_ID:  # только админ
        return

    if admin_state.get("mode") == "name":  # если ждём название
        admin_state["name"] = message.text  # сохраняем
        admin_state["mode"] = "file"  # ждём файл
        bot.send_message(message.chat.id, "Отправьте ZIP файл")  # просим файл

# ===== запуск =====
print("BOT STARTED")  # вывод в консоль
bot.infinity_polling()  # запуск бота
