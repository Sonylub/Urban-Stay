import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router
import pyodbc
import asyncio
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

router = Router()

# Инициализация бота и диспетчера
load_dotenv()
API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(router)

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.ERROR)

# Функция подключения к базе данных
def connect_to_db():
    try:
        # Чтение переменных окружения
        driver = os.getenv("DB_DRIVER")
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        trust_cert = os.getenv("DB_TRUST_CERT")

        # Формирование строки подключения
        conn = pyodbc.connect(
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate={trust_cert}"
        )
        return conn
    except pyodbc.Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None

# Проверка существования пользователя
def check_user_exists(telegram_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM Users WHERE telegram_id = ?", (telegram_id,))
            return cursor.fetchone() is not None
        except pyodbc.Error as e:
            logging.error(f"Ошибка при проверке пользователя: {e}")
        finally:
            conn.close()
    return False

# Добавление нового пользователя
def add_user(telegram_id, first_name, last_name, username):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Users (telegram_id, first_name, last_name, username, admin)
                VALUES (?, ?, ?, ?, 0)
            """, (telegram_id, first_name, last_name, username))
            conn.commit()
            logging.info(f"Пользователь {first_name} {last_name} (ID: {telegram_id}) добавлен.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при добавлении пользователя: {e}")
        finally:
            conn.close()

# Состояния для FSM
class RoomState(StatesGroup):
    viewing_rooms = State()

# Обработка команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    username = message.from_user.username or ""

    if not check_user_exists(telegram_id):
        add_user(telegram_id, first_name, last_name, username)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Доступные номера", callback_data="show_rooms")]
        ])
        await message.answer(f"👋Привет, {first_name}! Вы успешно зарегистрированы.", reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Доступные номера", callback_data="show_rooms")]
        ])
        await message.answer(f"👋Привет, {first_name}! Рады снова видеть вас.", reply_markup=markup)

# Команда /rooms
@dp.message(Command("rooms"))
async def rooms(message: types.Message, state: FSMContext):

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM Rooms WHERE status = 'available' AND quantity > 0")
            categories = [row.category for row in cursor.fetchall()]

            if categories:
                await state.update_data(categories=categories, current_category_index=0)
                logging.info(f"Доступные категории: {categories}")
                await show_category(message.chat.id, state)
            else:
                await message.answer("К сожалению, свободных номеров нет.")
                logging.warning("Нет доступных категорий номеров.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении категорий номеров: {e}")
        finally:
            conn.close()

async def show_category(chat_id, state: FSMContext):
    data = await state.get_data()
    categories = data['categories']
    current_category_index = data['current_category_index']
    current_category = categories[current_category_index]
    logging.info(f"Показываем категорию: {current_category} для пользователя {chat_id}")
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, description, price FROM Rooms WHERE category = ? AND status = 'available'", (current_category,))
            rooms = cursor.fetchall()
            if rooms:
                media = []
                for room in rooms:
                    cursor.execute("SELECT image_url FROM RoomImages WHERE room_id = ?", (room.room_id,))
                    images = [row.image_url for row in cursor.fetchall()]
                    if images:
                        media.append(InputMediaPhoto(media=images[0], caption=f"Категория: {current_category}\nЦена: {room.price} руб.\n{room.description}"))
                        media.extend([InputMediaPhoto(media=img) for img in images[1:]])

                # Формируем адаптивную клавиатуру
                buttons = [
                    InlineKeyboardButton(text="<<", callback_data="prev_category"),
                    InlineKeyboardButton(text="Забронировать", callback_data=f"book_{rooms[0].room_id}"),
                    InlineKeyboardButton(text=">>", callback_data="next_category")
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=[buttons])

                # Отправляем медиагруппу и сохраняем список сообщений
                media_messages = await bot.send_media_group(chat_id, media)
                media_message_ids = [msg.message_id for msg in media_messages]
                

                # Отправляем текстовое сообщение с кнопками
                sent_message = await bot.send_message(chat_id, "Выберите действие👇", reply_markup=markup)

                # Сохраняем идентификаторы сообщений в состоянии
                await state.update_data(last_text_message_id=sent_message.message_id, media_message_ids=media_message_ids)
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении номеров: {e}")
        finally:
            conn.close()

async def update_category(chat_id, state: FSMContext):
    data = await state.get_data()
    media_message_ids = data.get("media_message_ids", [])
    last_text_message_id = data.get("last_text_message_id")

    # Удаляем старые медиасообщения
    for message_id in media_message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении медиасообщения {message_id}: {e}")

    # Удаляем текстовое сообщение с кнопками
    if last_text_message_id:
        try:
            await bot.delete_message(chat_id, last_text_message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении текстового сообщения {last_text_message_id}: {e}")

    # Получаем текущую категорию
    categories = data['categories']
    current_category_index = data['current_category_index']
    current_category = categories[current_category_index]

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT room_id, description, price FROM Rooms WHERE category = ? AND status = 'available'",
                (current_category,)
            )
            rooms = cursor.fetchall()
            if rooms:
                media = []
                for room in rooms:
                    cursor.execute("SELECT image_url FROM RoomImages WHERE room_id = ?", (room.room_id,))
                    images = [row.image_url for row in cursor.fetchall()]
                    if images:
                        media.append(InputMediaPhoto(media=images[0], caption=f"Категория: {current_category}\nЦена: {room.price} руб.\n{room.description}"))
                        media.extend([InputMediaPhoto(media=img) for img in images[1:]])

                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="<<", callback_data="prev_category"),
                        InlineKeyboardButton(text="Забронировать", callback_data=f"book_{rooms[0].room_id}"),
                        InlineKeyboardButton(text=">>", callback_data="next_category")
                    ]
                ])

                # Отправляем новую медиагруппу
                media_messages = await bot.send_media_group(chat_id, media)
                media_message_ids = [msg.message_id for msg in media_messages]

                # Отправляем текстовое сообщение с кнопками
                sent_message = await bot.send_message(chat_id, "Выберите действие👇", reply_markup=markup)

                # Сохраняем новые идентификаторы сообщений в состоянии
                await state.update_data(last_text_message_id=sent_message.message_id, media_message_ids=media_message_ids)
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении номеров: {e}")
        finally:
            conn.close()
            
            
@router.callback_query()
async def handle_callback(callback_query: CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    data = await state.get_data()
    categories = data.get("categories", [])
    current_category_index = data.get("current_category_index", 0)

    try:
        # Обработка навигации по категориям
        if callback_query.data == "prev_category":
            if categories:
                current_category_index = (current_category_index - 1) % len(categories)
                await state.update_data(current_category_index=current_category_index)
                await update_category(chat_id, state)
            else:
                await callback_query.message.answer("Нет доступных категорий.")

        elif callback_query.data == "next_category":
            if categories:
                current_category_index = (current_category_index + 1) % len(categories)
                await state.update_data(current_category_index=current_category_index)
                await update_category(chat_id, state)
            else:
                await callback_query.message.answer("Нет доступных категорий.")

        # Обработка бронирования номера
        elif callback_query.data.startswith("book_"):
            room_id = callback_query.data.split("_")[1]
            if room_id.isdigit():
                room_id = int(room_id)
                logging.info(f"Пользователь {chat_id} пытается забронировать номер с ID: {room_id}.")
                conn = connect_to_db()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE Rooms SET quantity = quantity - 1 WHERE room_id = ? AND quantity > 0", (room_id,))
                        if cursor.rowcount > 0:
                            conn.commit()
                            await callback_query.message.answer(f"Вы успешно забронировали номер с ID: {room_id}.")
                            logging.info(f"Номер с ID: {room_id} успешно забронирован.")
                        else:
                            await callback_query.message.answer("Этот номер уже забронирован или отсутствует.")
                    except Exception as e:
                        logging.error(f"Ошибка при бронировании: {e}")
                        await callback_query.message.answer("Произошла ошибка при бронировании.")
                    finally:
                        conn.close()
            else:
                await callback_query.message.answer("Некорректный ID номера.")

        # Обработка команды показа номеров
        elif callback_query.data == "show_rooms":
            await rooms(callback_query.message, state)

        # Обработка команды массовой рассылки
        elif callback_query.data == "broadcast":
            if is_admin(callback_query.from_user.id):
                await callback_query.message.answer("Введите текст рассылки:")
                await state.set_state(AdminState.waiting_for_broadcast)
            else:
                await callback_query.answer("У вас нет прав администратора.")

    except Exception as e:
        logging.error(f"Ошибка обработки callback: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке запроса.")

    await callback_query.answer()

# Добавляем новое состояние для рассылки
class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_edit = State()

# Обработчик команды /apanel
@dp.message(Command("apanel"))
async def admin_panel(message: types.Message):
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора")
        return
    
    # Создаем клавиатуру админки
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Массовая рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="Просмотреть БД", callback_data="DB")]
    ])
    
    await message.answer("Админ-панель:", reply_markup=markup)


# Обработчик ввода текста рассылки
@dp.message(AdminState.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Получаем всех пользователей из БД
    users = get_all_users()
    
    if not users:
        await message.answer("Нет пользователей для рассылки.")
        return
    
    # Статистика рассылки
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(user["telegram_id"], message.text)
            success += 1
        except Exception as e:
            logging.error(f"Ошибка отправки пользователю {user['telegram_id']}: {e}")
            failed += 1
        await asyncio.sleep(0.1)  # Задержка для избежания рейт-лимита
    
    await message.answer(
        f"Рассылка завершена!\n"
        f"Успешно: {success}\n"
        f"Не доставлено: {failed}"
    )


# Функция проверки админских прав
def is_admin(telegram_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT admin FROM Users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return result and result[0] == 1
        except pyodbc.Error as e:
            logging.error(f"Ошибка проверки админа: {e}")
        finally:
            conn.close()
    return False

# Функция получения всех пользователей
def get_all_users():
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM Users")
            rows = cursor.fetchall()
            # Преобразуем результат в список словарей
            users = [{"telegram_id": row[0]} for row in rows]
            return users
        except pyodbc.Error as e:
            logging.error(f"Ошибка получения пользователей: {e}")
        finally:
            conn.close()
    return []


async def main():
    logging.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())