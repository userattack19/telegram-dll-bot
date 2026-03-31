import telebot  # библиотека для работы с Telegram Bot API
import os  # работа с файлами и переменными окружения
import json  # хранение товаров в JSON
import tempfile  # создание временных папок
import zipfile  # работа с zip архивами
import shutil  # удаление файлов
from pathlib import Path  # удобная работа с путями
import time  # для timestamp

TOKEN = os.getenv("BOT_TOKEN")  # получаем токен бота
ADMIN_ID = int(os.getenv("ADMIN_ID") or 6667142324)  # ID админа

bot = telebot.TeleBot(TOKEN)  # создаём бота

USERS_FILE = "users.txt"  # файл пользователей
ISSUED_FILE = "issued_users.txt"  # файл выданных товаров
PRODUCTS_FILE = "products.json"  # файл товаров

# ===== загрузка данных =====

def load_ids(filename):  # загружаем ID из файла
    if not os.path.exists(filename):  # если файла нет
        return set()  # возвращаем пустое множество
    with open(filename, "r") as f:  # открываем файл
        return set(int(x.strip()) for x in f if x.strip().isdigit())  # читаем ID

def append_id(filename, user_id):  # добавляем ID в файл
    with open(filename, "a") as f:  # открываем файл
        f.write(f"{user_id}\n")  # записываем ID

def load_products():  # загрузка товаров
    if not os.path.exists(PRODUCTS_FILE):  # если нет файла
        return {}  # пустой словарь
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)  # читаем JSON

def save_products(products):  # сохранение товаров
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)  # записываем JSON

users = load_ids(USERS_FILE)  # список пользователей
issued_users = load_ids(ISSUED_FILE)  # кому выдано
products = load_products()  # список товаров

waiting_question = set()  # ожидающие вопрос
admin_reply_map = {}  # связь сообщений
admin_state = {}  # состояние админа

# ===== утилиты =====

def add_user(user_id):  # добавляем пользователя
    if user_id not in users:
        users.add(user_id)
        append_id(USERS_FILE, user_id)

def build_zip(product_path, user_id, username=None):  # создаём уникальный архив
    temp_dir = Path(tempfile.mkdtemp())  # создаём временную папку
    extract_dir = temp_dir / "content"  # папка для распаковки
    extract_dir.mkdir()

    with zipfile.ZipFile(product_path, "r") as zf:  # открываем исходный архив
        zf.extractall(extract_dir)  # распаковываем

    # создаём файл с данными покупателя
    info = f"ID: {user_id}\nUser: @{username}\nTime: {int(time.time())}"
    (extract_dir / "info.txt").write_text(info)

    output = temp_dir / f"product_{user_id}.zip"  # путь нового архива

    with zipfile.ZipFile(output, "w") as zf:  # создаём архив
        for file in extract_dir.rglob("*"):  # перебираем файлы
            if file.is_file():
                zf.write(file, file.relative_to(extract_dir))  # добавляем

    return str(output)  # возвращаем путь

def send_product(user_id, product_name):  # отправка товара
    product = products.get(product_name)  # получаем товар
    if not product:
        raise Exception("Товар не найден")

    path = product["file"]  # путь к архиву

    try:
        chat = bot.get_chat(user_id)  # получаем чат
        username = chat.username
    except:
        username = None

    zip_path = build_zip(path, user_id, username)  # создаём персональный архив

    with open(zip_path, "rb") as f:  # открываем файл
        bot.send_document(user_id, f, caption=f"✅ Ваш товар: {product_name}")  # отправляем

    shutil.rmtree(Path(zip_path).parent, ignore_errors=True)  # удаляем временные файлы

# ===== клавиатуры =====

def user_kb():  # меню пользователя
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🛒 Товары")  # кнопка товаров
    kb.row("❓ Вопрос")  # кнопка вопроса
    return kb

def admin_kb():  # меню админа
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить товар")  # добавить товар
    kb.row("📦 Список товаров")  # список
    return kb

# ===== handlers =====

@bot.message_handler(commands=['start'])  # команда старт
def start(message):
    add_user(message.from_user.id)

    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Админка", reply_markup=admin_kb())
    else:
        bot.send_message(message.chat.id, "Меню", reply_markup=user_kb())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить товар")  # добавить товар
def add_product_start(message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_state["mode"] = "add_name"  # ожидаем название
    bot.send_message(message.chat.id, "Введите название товара")

@bot.message_handler(func=lambda m: m.text == "📦 Список товаров")  # список товаров
def list_products(message):
    if not products:
        bot.send_message(message.chat.id, "Нет товаров")
        return

    text = "\n".join(products.keys())  # список
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🛒 Товары")  # пользователь смотрит товары
def show_products(message):
    if not products:
        bot.send_message(message.chat.id, "Товаров нет")
        return

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for name in products:
        kb.row(f"Купить {name}")  # кнопка покупки

    bot.send_message(message.chat.id, "Выберите товар:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text.startswith("Купить "))  # покупка
def buy_product(message):
    product_name = message.text.replace("Купить ", "")

    bot.send_message(message.chat.id, "Отправьте скрин оплаты")

    bot.send_message(
        ADMIN_ID,
        f"Покупка {product_name}\nID: {message.from_user.id}"
    )

@bot.message_handler(content_types=['document'])  # загрузка файла товара
def upload_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    if admin_state.get("mode") == "add_file":
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)

        file_path = f"{message.document.file_name}"

        with open(file_path, "wb") as f:
            f.write(downloaded)

        name = admin_state["product_name"]

        products[name] = {
            "file": file_path
        }

        save_products(products)

        bot.send_message(message.chat.id, f"✅ Товар {name} добавлен")

        admin_state.clear()

@bot.message_handler(func=lambda m: True)  # основной обработчик
def text_handler(message):
    if message.from_user.id != ADMIN_ID:
        return

    if admin_state.get("mode") == "add_name":
        admin_state["product_name"] = message.text
        admin_state["mode"] = "add_file"

        bot.send_message(message.chat.id, "Отправьте ZIP файл товара")