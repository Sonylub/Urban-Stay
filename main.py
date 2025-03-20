import logging
import asyncio
import pyodbc
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

router = Router()

# Загрузка переменных окружения и инициализация бота
load_dotenv()
API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(router)

# Функция подключения к базе данных
def connect_to_db():
    try:
        driver = os.getenv("DB_DRIVER")
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        trust_cert = os.getenv("DB_TRUST_CERT")
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

# Функции для проверки и регистрации пользователей
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

def add_user(telegram_id, first_name, last_name, username, admin=0):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Users (telegram_id, first_name, last_name, username, admin) VALUES (?, ?, ?, ?, ?)",
                (telegram_id, first_name, last_name, username, admin)
            )
            conn.commit()
            logging.info(f"Пользователь {first_name} {last_name} (ID: {telegram_id}) добавлен.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при добавлении пользователя: {e}")
        finally:
            conn.close()

def is_admin(telegram_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT admin FROM Users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            admin_status = result and result[0] == 1
            logging.info(f"Проверка админа для ID {telegram_id}: {'Админ' if admin_status else 'Не админ'}")
            return admin_status
        except pyodbc.Error as e:
            logging.error(f"Ошибка проверки админа для ID {telegram_id}: {e}")
            return False
        finally:
            conn.close()
    logging.error(f"Не удалось подключиться к БД для проверки админа ID {telegram_id}")
    return False

# FSM состояния
class RoomState(StatesGroup):
    viewing_rooms = State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()

class DBAdminState(StatesGroup):
    waiting_for_add_user = State()
    waiting_for_edit_user = State()
    waiting_for_delete_user = State()
    waiting_for_add_room = State()
    waiting_for_edit_room = State()
    waiting_for_delete_room = State()
    waiting_for_add_image = State()
    waiting_for_edit_image = State()
    waiting_for_delete_image = State()
    waiting_for_room_edit_gui = State()
    waiting_for_user_edit_gui = State()
    waiting_for_image_edit_gui = State()
    waiting_for_add_guest = State()
    waiting_for_edit_guest = State()
    waiting_for_delete_guest = State()
    waiting_for_guest_edit_gui = State()
    waiting_for_add_service = State()
    waiting_for_edit_service = State()
    waiting_for_delete_service = State()
    waiting_for_add_guest_service = State()
    waiting_for_edit_guest_service = State()
    waiting_for_delete_guest_service = State()
    waiting_for_service_edit_gui = State()
    waiting_for_guest_service_edit_gui = State()

class GuestRegistrationState(StatesGroup):
    waiting_for_room_id = State()
    waiting_for_telegram_id = State()
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_check_in_date = State()
    waiting_for_check_out_date = State()
    waiting_for_comment = State()

class BookingState(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_check_in_date = State()
    waiting_for_check_out_date = State()
    waiting_for_comment = State()

class OrderServiceState(StatesGroup):
    waiting_for_quantity = State()

# Обработчик команды /start с добавленным пунктом "Мои услуги"
@dp.message(Command("start"))
async def start(message: types.Message):
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    username = message.from_user.username or ""
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Доступные номера", callback_data="show_rooms")],
        [InlineKeyboardButton(text="Мои бронирования", callback_data="my_bookings")],
        [InlineKeyboardButton(text="Мои услуги", callback_data="my_services")],
        [InlineKeyboardButton(text="Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="Заказать дополнительные услуги", callback_data="additional_services")],
        [InlineKeyboardButton(text="Техподдержка", callback_data="tech_support")]
    ])
    if not check_user_exists(telegram_id):
        add_user(telegram_id, first_name, last_name, username)
        await message.answer(f"👋 Привет, {first_name}! Вы успешно зарегистрированы.", reply_markup=markup)
    else:
        await message.answer(f"👋 Привет, {first_name}! Рады снова видеть вас.", reply_markup=markup)

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
                await show_category(message.chat.id, state)
            else:
                await message.answer("К сожалению, свободных номеров нет.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении категорий номеров: {e}")
        finally:
            conn.close()

async def show_category(chat_id, state: FSMContext):
    data = await state.get_data()
    categories = data.get('categories', [])
    current_category_index = data.get('current_category_index', 0)
    if not categories:
        logging.error("Нет категорий для отображения.")
        return
    current_category = categories[current_category_index]
    logging.info(f"Отображение категории: {current_category}, индекс: {current_category_index}")
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, description, price FROM Rooms WHERE category = ? AND status = 'available' AND quantity > 0", (current_category,))
            rooms = cursor.fetchall()
            if rooms:
                media = []
                for room in rooms:
                    cursor.execute("SELECT image_url FROM RoomImages WHERE room_id = ?", (room.room_id,))
                    images = [row.image_url for row in cursor.fetchall()]
                    if images:
                        media.append(InputMediaPhoto(
                            media=images[0],
                            caption=f"<b>Категория:</b> {current_category}\n<b>Цена: $</b> {room.price}\n{room.description}",
                            parse_mode="HTML"
                        ))
                        media.extend([InputMediaPhoto(media=img) for img in images[1:]])
                if media:
                    markup = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="<<", callback_data="prev_category"),
                        InlineKeyboardButton(text="Забронировать", callback_data=f"book_{rooms[0].room_id}"),
                        InlineKeyboardButton(text=">>", callback_data="next_category")
                    ]])
                    media_messages = await bot.send_media_group(chat_id, media)
                    media_message_ids = [msg.message_id for msg in media_messages]
                    sent_message = await bot.send_message(chat_id, "Выберите действие👇", reply_markup=markup)
                    await state.update_data(last_text_message_id=sent_message.message_id, media_message_ids=media_message_ids)
                else:
                    logging.warning(f"Нет изображений для категории {current_category}")
                    await bot.send_message(chat_id, "Нет изображений для этой категории.")
            else:
                logging.warning(f"Нет номеров для категории {current_category}")
                await bot.send_message(chat_id, "Нет доступных номеров в этой категории.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении номеров: {e}")
        finally:
            conn.close()

async def update_category(chat_id, state: FSMContext):
    data = await state.get_data()
    media_message_ids = data.get("media_message_ids", [])
    last_text_message_id = data.get("last_text_message_id")
    for message_id in media_message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении медиасообщения {message_id}: {e}")
    if last_text_message_id:
        try:
            await bot.delete_message(chat_id, last_text_message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении текстового сообщения {last_text_message_id}: {e}")
    await show_category(chat_id, state)

# Функции управления БД
async def show_db_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пользователи", callback_data="db_users")],
        [InlineKeyboardButton(text="Номера", callback_data="db_rooms")],
        [InlineKeyboardButton(text="Изображения", callback_data="db_images")],
        [InlineKeyboardButton(text="Гости", callback_data="db_guests")],
        [InlineKeyboardButton(text="Услуги", callback_data="db_services")],
        [InlineKeyboardButton(text="Гостевые услуги", callback_data="db_guest_services")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_apanel")]
    ])
    await bot.send_message(chat_id, "Выберите таблицу для управления:", reply_markup=markup)

async def show_users_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Просмотреть всех", callback_data="view_users")],
        [InlineKeyboardButton(text="Добавить пользователя", callback_data="add_user")],
        [InlineKeyboardButton(text="Выдать админку", callback_data="edit_user")],
        [InlineKeyboardButton(text="Удалить пользователя", callback_data="delete_user_menu")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
    ])
    await bot.send_message(chat_id, "Управление таблицей Users:", reply_markup=markup)

async def show_rooms_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Просмотреть номера", callback_data="view_rooms")],
        [InlineKeyboardButton(text="Добавить номер", callback_data="add_room")],
        [InlineKeyboardButton(text="Редактировать номер", callback_data="edit_room")],
        [InlineKeyboardButton(text="Удалить номер", callback_data="delete_room_menu")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
    ])
    await bot.send_message(chat_id, "Управление таблицей Rooms:", reply_markup=markup)

async def show_images_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Просмотреть изображения", callback_data="view_images")],
        [InlineKeyboardButton(text="Добавить изображение", callback_data="add_image")],
        [InlineKeyboardButton(text="Редактировать изображение", callback_data="edit_image")],
        [InlineKeyboardButton(text="Удалить изображение", callback_data="delete_image_menu")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
    ])
    await bot.send_message(chat_id, "Управление таблицей RoomImages:", reply_markup=markup)

async def show_guests_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Просмотреть гостей", callback_data="view_guests")],
        [InlineKeyboardButton(text="Добавить гостя", callback_data="add_guest")],
        [InlineKeyboardButton(text="Редактировать гостя", callback_data="edit_guest")],
        [InlineKeyboardButton(text="Удалить гостя", callback_data="delete_guest_menu")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
    ])
    await bot.send_message(chat_id, "Управление таблицей Guests:", reply_markup=markup)

async def show_services_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Просмотреть услуги", callback_data="view_services")],
        [InlineKeyboardButton(text="Добавить услугу", callback_data="add_service")],
        [InlineKeyboardButton(text="Редактировать услугу", callback_data="edit_service")],
        [InlineKeyboardButton(text="Удалить услугу", callback_data="delete_service")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
    ])
    await bot.send_message(chat_id, "Управление таблицей Services:", reply_markup=markup)

async def show_guest_services_menu(chat_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Просмотреть все", callback_data="view_guest_services")],
        [InlineKeyboardButton(text="Добавить запись", callback_data="add_guest_service")],
        [InlineKeyboardButton(text="Редактировать запись", callback_data="edit_guest_service")],
        [InlineKeyboardButton(text="Удалить запись", callback_data="delete_guest_service")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
    ])
    await bot.send_message(chat_id, "Управление таблицей GuestServices:", reply_markup=markup)

async def view_db_users(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id, first_name, last_name, username, admin FROM Users")
            users = cursor.fetchall()
            if not users:
                await bot.send_message(chat_id, "Нет пользователей.")
                return
            text = "Список пользователей:\n"
            for user in users:
                admin_status = "👑" if user.admin else ""
                text += f"ID: {user.telegram_id}, Имя: {user.first_name} {user.last_name}, Username: {user.username}, Админ: {admin_status}\n"
            await bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Ошибка при получении пользователей: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def view_db_rooms(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, category, description, price, quantity, status FROM Rooms")
            rows = cursor.fetchall()
            if not rows:
                await bot.send_message(chat_id, "Нет данных по номерам.")
            else:
                text = "Список номеров:\n"
                for row in rows:
                    text += f"ID: {row.room_id}\nКатегория: {row.category}\nЦена: {row.price} руб.\nКоличество: {row.quantity}\nСтатус: {row.status}\n====================\n"
                await bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Ошибка при получении номеров: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных по номерам.")
        finally:
            conn.close()

async def view_db_images(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, image_url FROM RoomImages")
            rows = cursor.fetchall()
            if not rows:
                await bot.send_message(chat_id, "Нет данных по изображениям.")
            else:
                text = "Список изображений:\n"
                for row in rows:
                    text += f"Room ID: {row.room_id}, URL: {row.image_url}\n"
                await bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Ошибка при получении изображений: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных по изображениям.")
        finally:
            conn.close()

async def view_db_guests(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT guest_id, room_id, telegram_id, first_name, last_name, check_in_date, check_out_date FROM Guests")
            guests = cursor.fetchall()
            if not guests:
                await bot.send_message(chat_id, "Нет данных по гостям.")
            else:
                text = "Список гостей:\n"
                for guest in guests:
                    text += f"ID: {guest.guest_id}, Комната: {guest.room_id}, Telegram ID: {guest.telegram_id}, Имя: {guest.first_name} {guest.last_name}, Заезд: {guest.check_in_date}, Выезд: {guest.check_out_date}\n"
                await bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Ошибка при получении гостей: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных по гостям.")
        finally:
            conn.close()

async def view_db_services(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT service_id, name, price, short_description FROM Services")
            services = cursor.fetchall()
            if not services:
                await bot.send_message(chat_id, "Нет услуг.")
                return
            text = "Список услуг:\n"
            for service in services:
                text += f"ID: {service.service_id}, Название: {service.name}, Цена: {service.price} руб., Описание: {service.short_description}\n"
            await bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Ошибка при получении услуг: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def view_db_guest_services(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.first_name, g.last_name, s.name, gs.quantity, gs.order_date, gs.status
                FROM GuestServices gs
                JOIN Guests g ON gs.guest_id = g.guest_id
                JOIN Services s ON gs.service_id = s.service_id
            """)
            records = cursor.fetchall()
            if not records:
                await bot.send_message(chat_id, "Нет данных в таблице GuestServices.")
            else:
                text = "Список гостевых услуг:\n"
                for record in records:
                    text += (f"Гость: {record.first_name} {record.last_name}, Услуга: {record.name}, "
                             f"Количество: {record.quantity}, Дата заказа: {record.order_date}, Статус: {record.status}\n")
                await bot.send_message(chat_id, text)
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении данных GuestServices: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

# Функции для GUI удаления и редактирования
async def show_users_for_delete(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id, first_name FROM Users")
            users = cursor.fetchall()
            if not users:
                await bot.send_message(chat_id, "Нет пользователей для удаления.")
                return
            buttons = [
                [InlineKeyboardButton(text="Удалить по ID", callback_data="delete_user_id")]
            ] + [
                [InlineKeyboardButton(text=f"{user.first_name} (ID: {user.telegram_id})", callback_data=f"delete_user_{user.telegram_id}")]
                for user in users
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите пользователя для удаления:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка пользователей: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_rooms_for_delete(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, category FROM Rooms")
            rooms = cursor.fetchall()
            if not rooms:
                await bot.send_message(chat_id, "Нет номеров для удаления.")
                return
            buttons = [
                [InlineKeyboardButton(text="Удалить по ID", callback_data="delete_room_id")]
            ] + [
                [InlineKeyboardButton(text=f"ID: {room.room_id} - {room.category}", callback_data=f"delete_room_{room.room_id}")]
                for room in rooms
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите номер для удаления:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка номеров: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_guests_for_delete(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT guest_id, first_name, last_name FROM Guests")
            guests = cursor.fetchall()
            if not guests:
                await bot.send_message(chat_id, "Нет гостей для удаления.")
                return
            buttons = [
                [InlineKeyboardButton(text="Удалить по ID", callback_data="delete_guest_id")]
            ] + [
                [InlineKeyboardButton(text=f"ID: {guest.guest_id} - {guest.first_name} {guest.last_name}", callback_data=f"delete_guest_{guest.guest_id}")]
                for guest in guests
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите гостя для удаления:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка гостей: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_rooms_for_image_delete(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT room_id FROM RoomImages")
            rooms = cursor.fetchall()
            if not rooms:
                await bot.send_message(chat_id, "Нет изображений для удаления.")
                return
            buttons = [
                [InlineKeyboardButton(text="Удалить по room_id и URL", callback_data="delete_image_id")]
            ] + [
                [InlineKeyboardButton(text=f"Room ID: {room.room_id}", callback_data=f"select_room_image_{room.room_id}")]
                for room in rooms
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите комнату для удаления изображений:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка комнат: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_images_for_delete(chat_id, room_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT image_url FROM RoomImages WHERE room_id = ?", (room_id,))
            images = cursor.fetchall()
            if not images:
                await bot.send_message(chat_id, f"Нет изображений для комнаты ID {room_id}.")
                return
            buttons = [
                [InlineKeyboardButton(text="Удалить по room_id и URL", callback_data="delete_image_id")]
            ] + [
                [InlineKeyboardButton(text=f"URL: {image.image_url[:20]}...", callback_data=f"delete_image_{room_id}_{image.image_url}")]
                for image in images
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="delete_image_gui")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, f"Выберите изображение для удаления в комнате ID {room_id}:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении изображений для комнаты ID {room_id}: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_services_for_edit(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT service_id, name FROM Services")
            services = cursor.fetchall()
            if not services:
                await bot.send_message(chat_id, "Нет услуг для редактирования.")
                return
            buttons = [
                [InlineKeyboardButton(text=f"ID: {service.service_id} - {service.name}", callback_data=f"edit_service_gui_{service.service_id}")]
                for service in services
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите услугу для редактирования:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка услуг: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_services_for_delete(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT service_id, name FROM Services")
            services = cursor.fetchall()
            if not services:
                await bot.send_message(chat_id, "Нет услуг для удаления.")
                return
            buttons = [
                [InlineKeyboardButton(text=f"ID: {service.service_id} - {service.name}", callback_data=f"delete_service_{service.service_id}")]
                for service in services
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите услугу для удаления:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка услуг: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_guest_services_for_edit(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT guest_id, service_id, order_date, quantity, status FROM GuestServices")
            records = cursor.fetchall()
            if not records:
                await bot.send_message(chat_id, "Нет записей для редактирования.")
                return
            buttons = [
                [InlineKeyboardButton(
                    text=f"Гость: {record.guest_id}, Услуга: {record.service_id}, Дата: {record.order_date}",
                    callback_data=f"edit_gs_{record.guest_id}_{record.service_id}_{record.order_date.isoformat()}"
                )] for record in records
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите запись для редактирования:", reply_markup=markup)
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении списка GuestServices: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_guest_services_for_delete(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT guest_id, service_id, order_date FROM GuestServices")
            records = cursor.fetchall()
            if not records:
                await bot.send_message(chat_id, "Нет записей для удаления.")
                return
            buttons = [
                [InlineKeyboardButton(
                    text=f"Гость: {record.guest_id}, Услуга: {record.service_id}, Дата: {record.order_date}",
                    callback_data=f"delete_gs_{record.guest_id}_{record.service_id}_{record.order_date.isoformat()}"
                )] for record in records
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите запись для удаления:", reply_markup=markup)
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении списка GuestServices: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

# Функции для GUI-редактирования
async def show_rooms_for_edit(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, category FROM Rooms")
            rooms = cursor.fetchall()
            if not rooms:
                await bot.send_message(chat_id, "Нет номеров для редактирования.")
                return
            buttons = [
                [InlineKeyboardButton(text=f"ID: {room.room_id} - {room.category}", callback_data=f"edit_room_gui_{room.room_id}")]
                for room in rooms
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите номер для редактирования:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка номеров: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_users_for_edit(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id, first_name FROM Users")
            users = cursor.fetchall()
            if not users:
                await bot.send_message(chat_id, "Нет пользователей для редактирования.")
                return
            buttons = [
                [InlineKeyboardButton(text=f"{user.first_name} (ID: {user.telegram_id})", callback_data=f"edit_user_gui_{user.telegram_id}")]
                for user in users
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите пользователя для редактирования:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка пользователей: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_images_for_edit(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id, image_url FROM RoomImages")
            images = cursor.fetchall()
            if not images:
                await bot.send_message(chat_id, "Нет изображений для редактирования.")
                return
            buttons = [
                [InlineKeyboardButton(text=f"Room ID: {image.room_id}, URL: {image.image_url}", callback_data=f"edit_image_gui_{image.room_id}_{image.image_url}")]
                for image in images
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите изображение для редактирования:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка изображений: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

async def show_guests_for_edit(chat_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT guest_id, first_name, last_name FROM Guests")
            guests = cursor.fetchall()
            if not guests:
                await bot.send_message(chat_id, "Нет гостей для редактирования.")
                return
            buttons = [
                [InlineKeyboardButton(text=f"ID: {guest.guest_id} - {guest.first_name} {guest.last_name}", callback_data=f"edit_guest_gui_{guest.guest_id}")]
                for guest in guests
            ]
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(chat_id, "Выберите гостя для редактирования:", reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка при получении списка гостей: {e}")
            await bot.send_message(chat_id, "Ошибка при получении данных.")
        finally:
            conn.close()

# Функции для работы с базой данных
def add_user_db(telegram_id, first_name, last_name, username, admin):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Users (telegram_id, first_name, last_name, username, admin) VALUES (?, ?, ?, ?, ?)",
                (telegram_id, first_name, last_name, username, admin)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении пользователя: {e}")
        finally:
            conn.close()
    return False

def edit_user_db(telegram_id, admin):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET admin = ? WHERE telegram_id = ?", (admin, telegram_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при редактировании пользователя: {e}")
        finally:
            conn.close()
    return False

def delete_user_db(telegram_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Users WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при удалении пользователя: {e}")
        finally:
            conn.close()
    return False

def add_room_db(category, description, price, quantity, status):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Rooms (category, description, price, quantity, status) VALUES (?, ?, ?, ?, ?)",
                (category, description, price, quantity, status)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении номера: {e}")
        finally:
            conn.close()
    return False

def edit_room_db(room_id, category, description, price, quantity, status):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Rooms SET category = ?, description = ?, price = ?, quantity = ?, status = ? WHERE room_id = ?",
                (category, description, price, quantity, status, room_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при редактировании номера: {e}")
        finally:
            conn.close()
    return False

def delete_room_db(room_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Rooms WHERE room_id = ?", (room_id,))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при удалении номера: {e}")
        finally:
            conn.close()
    return False

def add_image_db(room_id, image_url):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO RoomImages (room_id, image_url) VALUES (?, ?)",
                (room_id, image_url)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении изображения: {e}")
        finally:
            conn.close()
    return False

def edit_image_db(room_id, old_url, new_url):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE RoomImages SET image_url = ? WHERE room_id = ? AND image_url = ?",
                (new_url, room_id, old_url)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при редактировании изображения: {e}")
        finally:
            conn.close()
    return False

def delete_image_db(room_id, image_url):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM RoomImages WHERE room_id = ? AND image_url = ?", (room_id, image_url))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при удалении изображения: {e}")
        finally:
            conn.close()
    return False

def add_service_db(name, price, short_description, detailed_description):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Services (name, price, short_description, detailed_description) VALUES (?, ?, ?, ?)",
                (name, price, short_description, detailed_description)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении услуги: {e}")
        finally:
            conn.close()
    return False

def edit_service_db(service_id, name, price, short_description, detailed_description):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Services SET name = ?, price = ?, short_description = ?, detailed_description = ? WHERE service_id = ?",
                (name, price, short_description, detailed_description, service_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при редактировании услуги: {e}")
        finally:
            conn.close()
    return False

def delete_service_db(service_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Services WHERE service_id = ?", (service_id,))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при удалении услуги: {e}")
        finally:
            conn.close()
    return False

def add_guest_service_db(guest_id, service_id, quantity, status):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO GuestServices (guest_id, service_id, quantity, order_date, status) VALUES (?, ?, ?, GETDATE(), ?)",
                (guest_id, service_id, quantity, status)
            )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении записи в GuestServices: {e}")
        finally:
            conn.close()
    return False

def edit_guest_service_db(guest_id, service_id, order_date, field, value):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            if field == "quantity":
                cursor.execute(
                    "UPDATE GuestServices SET quantity = ? WHERE guest_id = ? AND service_id = ? AND order_date = ?",
                    (int(value), guest_id, service_id, order_date)
                )
            elif field == "status":
                cursor.execute(
                    "UPDATE GuestServices SET status = ? WHERE guest_id = ? AND service_id = ? AND order_date = ?",
                    (value, guest_id, service_id, order_date)
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при редактировании записи в GuestServices: {e}")
        finally:
            conn.close()
    return False

def delete_guest_service_db(guest_id, service_id, order_date):
    conn = connect_to_db()
    if conn:
        try:
            logging.info(f"Удаление GuestServices: guest_id={guest_id}, service_id={service_id}, order_date={order_date}")
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM GuestServices WHERE guest_id = ? AND service_id = ? AND order_date = ?",
                (guest_id, service_id, order_date)
            )
            conn.commit()
            return cursor.rowcount > 0
        except pyodbc.Error as e:
            logging.error(f"Ошибка при удалении записи из GuestServices: {e}")
            return False
        finally:
            conn.close()
    return False

# Функции для дополнительных услуг
async def show_services_list(message: types.Message, state: FSMContext):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT service_id, name, price, short_description FROM Services")
            services = cursor.fetchall()
            if services:
                buttons = [
                    [InlineKeyboardButton(text=f"{service.name} - {service.price} руб.", callback_data=f"select_service_{service.service_id}")]
                    for service in services
                ]
                buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_main")])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await message.answer("Выберите дополнительную услугу:", reply_markup=markup)
            else:
                await message.answer("Нет доступных дополнительных услуг.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при получении списка услуг: {e}")
            await message.answer("Произошла ошибка при получении списка услуг.")
        finally:
            conn.close()
    else:
        await message.answer("Ошибка подключения к базе данных.")

# Callback-хендлер
@router.callback_query()
async def handle_callback(callback_query: CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    data_state = await state.get_data()
    categories = data_state.get("categories", [])
    current_category_index = data_state.get("current_category_index", 0)
    try:
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
        elif callback_query.data.startswith("book_"):
            room_id = callback_query.data.split("_")[1]
            if room_id.isdigit():
                room_id = int(room_id)
                conn = connect_to_db()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT quantity FROM Rooms WHERE room_id = ? AND status = 'available'", (room_id,))
                        result = cursor.fetchone()
                        if result and result.quantity > 0:
                            await state.update_data(room_id=room_id, telegram_id=callback_query.from_user.id)
                            await callback_query.message.answer("Введите ваше имя:")
                            await state.set_state(BookingState.waiting_for_first_name)
                        else:
                            await callback_query.message.answer("Этот номер уже забронирован или отсутствует.")
                    except pyodbc.Error as e:
                        logging.error(f"Ошибка при проверке комнаты: {e}")
                        await callback_query.message.answer("Произошла ошибка при бронировании.")
                    finally:
                        conn.close()
        elif callback_query.data == "show_rooms":
            await rooms(callback_query.message, state)
        elif callback_query.data == "my_bookings":
            telegram_id = callback_query.from_user.id
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT guest_id, room_id, check_in_date, check_out_date FROM Guests WHERE telegram_id = ?", (telegram_id,))
                    bookings = cursor.fetchall()
                    if not bookings:
                        await callback_query.message.answer("У вас нет активных бронирований.")
                    else:
                        text = "Ваши бронирования:\n"
                        for booking in bookings:
                            text += f"ID брони: {booking.guest_id}, Комната ID: {booking.room_id}, Заезд: {booking.check_in_date}, Выезд: {booking.check_out_date}\n"
                        await callback_query.message.answer(text)
                except pyodbc.Error as e:
                    logging.error(f"Ошибка при получении бронирований: {e}")
                    await callback_query.message.answer("Ошибка при получении данных.")
                finally:
                    conn.close()
        elif callback_query.data == "my_services":
            telegram_id = callback_query.from_user.id
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT guest_id FROM Guests WHERE telegram_id = ? AND check_out_date >= GETDATE()", (telegram_id,))
                    guest = cursor.fetchone()
                    if guest:
                        guest_id = guest.guest_id
                        cursor.execute("""
                            SELECT s.name, gs.quantity, gs.order_date, gs.status
                            FROM GuestServices gs
                            JOIN Services s ON gs.service_id = s.service_id
                            WHERE gs.guest_id = ?
                        """, (guest_id,))
                        services = cursor.fetchall()
                        if services:
                            text = "Ваши заказанные услуги:\n"
                            for service in services:
                                text += f"Услуга: {service.name}, Количество: {service.quantity}, Дата заказа: {service.order_date}, Статус: {service.status}\n"
                            await callback_query.message.answer(text)
                        else:
                            await callback_query.message.answer("У вас нет заказанных услуг.")
                    else:
                        await callback_query.message.answer("У вас нет активных бронирований.")
                except pyodbc.Error as e:
                    logging.error(f"Ошибка при получении услуг: {e}")
                    await callback_query.message.answer("Произошла ошибка при получении данных.")
                finally:
                    conn.close()
        elif callback_query.data == "additional_services":
            telegram_id = callback_query.from_user.id
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT guest_id FROM Guests WHERE telegram_id = ? AND check_out_date >= GETDATE()", (telegram_id,))
                    booking = cursor.fetchone()
                    if booking:
                        await show_services_list(callback_query.message, state)
                    else:
                        await callback_query.message.answer("У вас нет активных бронирований. Пожалуйста, забронируйте номер, чтобы заказать дополнительные услуги.")
                except pyodbc.Error as e:
                    logging.error(f"Ошибка при проверке бронирования: {e}")
                    await callback_query.message.answer("Произошла ошибка при проверке бронирования.")
                finally:
                    conn.close()
            else:
                await callback_query.message.answer("Ошибка подключения к базе данных.")
        elif callback_query.data.startswith("select_service_"):
            service_id = int(callback_query.data.split("_")[2])
            await state.update_data(selected_service_id=service_id)
            await callback_query.message.answer("Введите количество услуг, которые вы хотите заказать:")
            await state.set_state(OrderServiceState.waiting_for_quantity)
        elif callback_query.data == "back_to_main":
            await start(callback_query.message)
        elif callback_query.data in ["reviews", "tech_support"]:
            await callback_query.message.answer("Эта функция находится в разработке.")
        elif callback_query.data == "broadcast":
            if is_admin(callback_query.from_user.id):
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Начать рассылку", callback_data="start_broadcast")],
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_apanel")]
                ])
                await callback_query.message.answer("Выберите действие:", reply_markup=markup)
            else:
                await callback_query.answer("У вас нет прав администратора.")
        elif callback_query.data == "start_broadcast":
            await callback_query.message.answer("Введите текст рассылки:")
            await state.set_state(AdminState.waiting_for_broadcast)
        elif callback_query.data == "DB":
            if is_admin(callback_query.from_user.id):
                await show_db_menu(chat_id)
            else:
                await callback_query.answer("У вас нет прав администратора.")
        elif callback_query.data == "db_users":
            await show_users_menu(chat_id)
        elif callback_query.data == "view_users":
            await view_db_users(chat_id)
        elif callback_query.data == "add_user":
            await callback_query.message.answer("Введите данные нового пользователя в формате:\ntelegram_id, first_name, last_name, username, admin(0 или 1)")
            await state.set_state(DBAdminState.waiting_for_add_user)
        elif callback_query.data == "edit_user":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Через запятую", callback_data="edit_user_text")],
                [InlineKeyboardButton(text="Через GUI", callback_data="edit_user_gui")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ редактирования пользователя:", reply_markup=markup)
        elif callback_query.data == "edit_user_text":
            await callback_query.message.answer("Введите данные для редактирования пользователя в формате:\ntelegram_id, admin(0 или 1)")
            await state.set_state(DBAdminState.waiting_for_edit_user)
        elif callback_query.data == "edit_user_gui":
            await show_users_for_edit(chat_id)
        elif callback_query.data.startswith("edit_user_gui_"):
            telegram_id = callback_query.data.split("_")[3]
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT admin FROM Users WHERE telegram_id = ?", (telegram_id,))
                    result = cursor.fetchone()
                    if result:
                        current_admin = result[0]
                        new_admin = 0 if current_admin == 1 else 1
                        if edit_user_db(telegram_id, new_admin):
                            status_text = "назначен администратором" if new_admin == 1 else "снята админка"
                            await callback_query.message.answer(f"Пользователь {telegram_id} теперь {status_text}.")
                        else:
                            await callback_query.message.answer("Ошибка при редактировании пользователя.")
                    else:
                        await callback_query.message.answer("Пользователь не найден.")
                except Exception as e:
                    logging.error(f"Ошибка при редактировании пользователя: {e}")
                    await callback_query.message.answer("Ошибка при редактировании пользователя.")
                finally:
                    conn.close()
        elif callback_query.data == "delete_user_menu":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Выбрать из списка", callback_data="delete_user_gui")],
                [InlineKeyboardButton(text="Ввести ID", callback_data="delete_user_id")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ удаления пользователя:", reply_markup=markup)
        elif callback_query.data == "delete_user_id":
            await callback_query.message.answer("Введите telegram_id пользователя для удаления:")
            await state.set_state(DBAdminState.waiting_for_delete_user)
        elif callback_query.data == "delete_user_gui":
            await show_users_for_delete(chat_id)
        elif callback_query.data.startswith("delete_user_"):
            telegram_id = callback_query.data.split("_")[2]
            if delete_user_db(telegram_id):
                await callback_query.message.answer(f"Пользователь {telegram_id} удалён.")
            else:
                await callback_query.message.answer("Ошибка при удалении пользователя.")
        elif callback_query.data == "db_rooms":
            await show_rooms_menu(chat_id)
        elif callback_query.data == "view_rooms":
            await view_db_rooms(chat_id)
        elif callback_query.data == "add_room":
            await callback_query.message.answer("Введите данные нового номера в формате:\ncategory, description, price, quantity, status")
            await state.set_state(DBAdminState.waiting_for_add_room)
        elif callback_query.data == "edit_room":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Через запятую", callback_data="edit_room_text")],
                [InlineKeyboardButton(text="Через GUI", callback_data="edit_room_gui")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ редактирования номера:", reply_markup=markup)
        elif callback_query.data == "edit_room_text":
            await callback_query.message.answer("Введите данные для редактирования номера в формате:\nroom_id, category, description, price, quantity, status")
            await state.set_state(DBAdminState.waiting_for_edit_room)
        elif callback_query.data == "edit_room_gui":
            await show_rooms_for_edit(chat_id)
        elif callback_query.data.startswith("edit_room_gui_"):
            room_id = callback_query.data.split("_")[3]
            await state.update_data(edit_room_id=room_id)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Категория", callback_data="edit_room_category")],
                [InlineKeyboardButton(text="Описание", callback_data="edit_room_description")],
                [InlineKeyboardButton(text="Цена", callback_data="edit_room_price")],
                [InlineKeyboardButton(text="Количество", callback_data="edit_room_quantity")],
                [InlineKeyboardButton(text="Статус", callback_data="edit_room_status")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer(f"Выберите поле для редактирования номера ID {room_id}:", reply_markup=markup)
        elif callback_query.data == "edit_room_category":
            await callback_query.message.answer("Введите новую категорию:")
            await state.set_state(DBAdminState.waiting_for_room_edit_gui)
            await state.update_data(edit_field="category")
        elif callback_query.data == "edit_room_description":
            await callback_query.message.answer("Введите новое описание:")
            await state.set_state(DBAdminState.waiting_for_room_edit_gui)
            await state.update_data(edit_field="description")
        elif callback_query.data == "edit_room_price":
            await callback_query.message.answer("Введите новую цену:")
            await state.set_state(DBAdminState.waiting_for_room_edit_gui)
            await state.update_data(edit_field="price")
        elif callback_query.data == "edit_room_quantity":
            await callback_query.message.answer("Введите новое количество:")
            await state.set_state(DBAdminState.waiting_for_room_edit_gui)
            await state.update_data(edit_field="quantity")
        elif callback_query.data == "edit_room_status":
            await callback_query.message.answer("Введите новый статус:")
            await state.set_state(DBAdminState.waiting_for_room_edit_gui)
            await state.update_data(edit_field="status")
        elif callback_query.data == "delete_room_menu":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Выбрать из списка", callback_data="delete_room_gui")],
                [InlineKeyboardButton(text="Ввести ID", callback_data="delete_room_id")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ удаления номера:", reply_markup=markup)
        elif callback_query.data == "delete_room_id":
            await callback_query.message.answer("Введите room_id номера для удаления:")
            await state.set_state(DBAdminState.waiting_for_delete_room)
        elif callback_query.data == "delete_room_gui":
            await show_rooms_for_delete(chat_id)
        elif callback_query.data.startswith("delete_room_"):
            room_id = callback_query.data.split("_")[2]
            if delete_room_db(room_id):
                await callback_query.message.answer(f"Номер {room_id} удалён.")
            else:
                await callback_query.message.answer("Ошибка при удалении номера.")
        elif callback_query.data == "db_images":
            await show_images_menu(chat_id)
        elif callback_query.data == "view_images":
            await view_db_images(chat_id)
        elif callback_query.data == "add_image":
            await callback_query.message.answer("Введите данные нового изображения в формате:\nroom_id, image_url")
            await state.set_state(DBAdminState.waiting_for_add_image)
        elif callback_query.data == "edit_image":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Через запятую", callback_data="edit_image_text")],
                [InlineKeyboardButton(text="Через GUI", callback_data="edit_image_gui")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ редактирования изображения:", reply_markup=markup)
        elif callback_query.data == "edit_image_text":
            await callback_query.message.answer("Введите данные для редактирования изображения в формате:\nroom_id, old_image_url, new_image_url")
            await state.set_state(DBAdminState.waiting_for_edit_image)
        elif callback_query.data == "edit_image_gui":
            await show_images_for_edit(chat_id)
        elif callback_query.data.startswith("edit_image_gui_"):
            parts = callback_query.data.split("_")
            room_id = parts[3]
            old_url = "_".join(parts[4:])
            await state.update_data(edit_image_room_id=room_id, edit_image_old_url=old_url)
            await callback_query.message.answer(f"Введите новый URL для изображения комнаты ID {room_id}:")
            await state.set_state(DBAdminState.waiting_for_image_edit_gui)
        elif callback_query.data == "delete_image_menu":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Выбрать из списка", callback_data="delete_image_gui")],
                [InlineKeyboardButton(text="Ввести room_id и URL", callback_data="delete_image_id")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ удаления изображения:", reply_markup=markup)
        elif callback_query.data == "delete_image_id":
            await callback_query.message.answer("Введите данные для удаления изображения в формате:\nroom_id, image_url")
            await state.set_state(DBAdminState.waiting_for_delete_image)
        elif callback_query.data == "delete_image_gui":
            await show_rooms_for_image_delete(chat_id)
        elif callback_query.data.startswith("select_room_image_"):
            room_id = callback_query.data.split("_")[3]
            await show_images_for_delete(chat_id, room_id)
        elif callback_query.data.startswith("delete_image_"):
            parts = callback_query.data.split("_", 3)
            room_id = parts[2]
            image_url = parts[3]
            if delete_image_db(room_id, image_url):
                await callback_query.message.answer(f"Изображение {image_url} для комнаты ID {room_id} удалено.")
            else:
                await callback_query.message.answer("Ошибка при удалении изображения.")
        elif callback_query.data == "db_guests":
            await show_guests_menu(chat_id)
        elif callback_query.data == "view_guests":
            await view_db_guests(chat_id)
        elif callback_query.data == "add_guest":
            await callback_query.message.answer("Введите данные нового гостя в формате:\nroom_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment")
            await state.set_state(DBAdminState.waiting_for_add_guest)
        elif callback_query.data == "edit_guest":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Через запятую", callback_data="edit_guest_text")],
                [InlineKeyboardButton(text="Через GUI", callback_data="edit_guest_gui")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ редактирования гостя:", reply_markup=markup)
        elif callback_query.data == "edit_guest_text":
            await callback_query.message.answer("Введите данные для редактирования гостя в формате:\nguest_id, field1=value1, field2=value2, ...")
            await state.set_state(DBAdminState.waiting_for_edit_guest)
        elif callback_query.data == "edit_guest_gui":
            await show_guests_for_edit(chat_id)
        elif callback_query.data.startswith("edit_guest_gui_"):
            guest_id = callback_query.data.split("_")[3]
            await state.update_data(edit_guest_id=guest_id)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Room ID", callback_data="edit_guest_room_id")],
                [InlineKeyboardButton(text="Telegram ID", callback_data="edit_guest_telegram_id")],
                [InlineKeyboardButton(text="Имя", callback_data="edit_guest_first_name")],
                [InlineKeyboardButton(text="Фамилия", callback_data="edit_guest_last_name")],
                [InlineKeyboardButton(text="Email", callback_data="edit_guest_email")],
                [InlineKeyboardButton(text="Телефон", callback_data="edit_guest_phone")],
                [InlineKeyboardButton(text="Дата заезда", callback_data="edit_guest_check_in_date")],
                [InlineKeyboardButton(text="Дата выезда", callback_data="edit_guest_check_out_date")],
                [InlineKeyboardButton(text="Комментарий", callback_data="edit_guest_comment")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer(f"Выберите поле для редактирования гостя ID {guest_id}:", reply_markup=markup)
        elif callback_query.data == "edit_guest_room_id":
            await callback_query.message.answer("Введите новый room_id:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="room_id")
        elif callback_query.data == "edit_guest_telegram_id":
            await callback_query.message.answer("Введите новый telegram_id:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="telegram_id")
        elif callback_query.data == "edit_guest_first_name":
            await callback_query.message.answer("Введите новое имя:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="first_name")
        elif callback_query.data == "edit_guest_last_name":
            await callback_query.message.answer("Введите новую фамилию:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="last_name")
        elif callback_query.data == "edit_guest_email":
            await callback_query.message.answer("Введите новый email:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="email")
        elif callback_query.data == "edit_guest_phone":
            await callback_query.message.answer("Введите новый телефон:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="phone")
        elif callback_query.data == "edit_guest_check_in_date":
            await callback_query.message.answer("Введите новую дату заезда (ГГГГ-ММ-ДД):")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="check_in_date")
        elif callback_query.data == "edit_guest_check_out_date":
            await callback_query.message.answer("Введите новую дату выезда (ГГГГ-ММ-ДД):")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="check_out_date")
        elif callback_query.data == "edit_guest_comment":
            await callback_query.message.answer("Введите новый комментарий:")
            await state.set_state(DBAdminState.waiting_for_guest_edit_gui)
            await state.update_data(edit_field="comment")
        elif callback_query.data == "delete_guest_menu":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Выбрать из списка", callback_data="delete_guest_gui")],
                [InlineKeyboardButton(text="Ввести ID", callback_data="delete_guest_id")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ удаления гостя:", reply_markup=markup)
        elif callback_query.data == "delete_guest_id":
            await callback_query.message.answer("Введите guest_id для удаления:")
            await state.set_state(DBAdminState.waiting_for_delete_guest)
        elif callback_query.data == "delete_guest_gui":
            await show_guests_for_delete(chat_id)
        elif callback_query.data.startswith("delete_guest_"):
            guest_id = callback_query.data.split("_")[2]
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Guests WHERE guest_id = ?", (guest_id,))
                    conn.commit()
                    if cursor.rowcount > 0:
                        await callback_query.message.answer(f"Гость {guest_id} удалён.")
                    else:
                        await callback_query.message.answer("Гость с таким ID не найден.")
                except pyodbc.Error as e:
                    logging.error(f"Ошибка при удалении гостя: {e}")
                    await callback_query.message.answer("Ошибка при удалении гостя.")
                finally:
                    conn.close()
        elif callback_query.data == "db_services":
            await show_services_menu(chat_id)
        elif callback_query.data == "view_services":
            await view_db_services(chat_id)
        elif callback_query.data == "add_service":
            await callback_query.message.answer("Введите данные новой услуги в формате:\nname, price, short_description, detailed_description")
            await state.set_state(DBAdminState.waiting_for_add_service)
        elif callback_query.data == "edit_service":
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Через запятую", callback_data="edit_service_text")],
                [InlineKeyboardButton(text="Через GUI", callback_data="edit_service_gui")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer("Выберите способ редактирования услуги:", reply_markup=markup)
        elif callback_query.data == "edit_service_text":
            await callback_query.message.answer("Введите ID услуги и новые данные в формате:\nservice_id, name, price, short_description, detailed_description")
            await state.set_state(DBAdminState.waiting_for_edit_service)
        elif callback_query.data == "edit_service_gui":
            await show_services_for_edit(chat_id)
        elif callback_query.data.startswith("edit_service_gui_"):
            service_id = callback_query.data.split("_")[3]
            await state.update_data(edit_service_id=service_id)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Название", callback_data="edit_service_name")],
                [InlineKeyboardButton(text="Цена", callback_data="edit_service_price")],
                [InlineKeyboardButton(text="Краткое описание", callback_data="edit_service_short_desc")],
                [InlineKeyboardButton(text="Подробное описание", callback_data="edit_service_detailed_desc")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
            ])
            await callback_query.message.answer(f"Выберите поле для редактирования услуги ID {service_id}:", reply_markup=markup)
        elif callback_query.data == "edit_service_name":
            await callback_query.message.answer("Введите новое название:")
            await state.set_state(DBAdminState.waiting_for_service_edit_gui)
            await state.update_data(edit_field="name")
        elif callback_query.data == "edit_service_price":
            await callback_query.message.answer("Введите новую цену:")
            await state.set_state(DBAdminState.waiting_for_service_edit_gui)
            await state.update_data(edit_field="price")
        elif callback_query.data == "edit_service_short_desc":
            await callback_query.message.answer("Введите новое краткое описание:")
            await state.set_state(DBAdminState.waiting_for_service_edit_gui)
            await state.update_data(edit_field="short_description")
        elif callback_query.data == "edit_service_detailed_desc":
            await callback_query.message.answer("Введите новое подробное описание:")
            await state.set_state(DBAdminState.waiting_for_service_edit_gui)
            await state.update_data(edit_field="detailed_description")
        elif callback_query.data == "delete_service":
            await show_services_for_delete(chat_id)
        elif callback_query.data.startswith("delete_service_"):
            service_id = callback_query.data.split("_")[2]
            if delete_service_db(service_id):
                await callback_query.message.answer(f"Услуга ID {service_id} удалена.")
            else:
                await callback_query.message.answer("Ошибка при удалении услуги.")
        elif callback_query.data == "db_guest_services":
            await show_guest_services_menu(chat_id)
        elif callback_query.data == "view_guest_services":
            await view_db_guest_services(chat_id)
        elif callback_query.data == "add_guest_service":
            await callback_query.message.answer("Введите данные для добавления в GuestServices в формате:\nguest_id, service_id, quantity, status")
            await state.set_state(DBAdminState.waiting_for_add_guest_service)
        elif callback_query.data == "edit_guest_service":
            await show_guest_services_for_edit(chat_id)
        elif callback_query.data.startswith("edit_gs_"):
            try:
                parts = callback_query.data.split("_")
                logging.info(f"callback_data for edit_gs_: {callback_query.data}")
                if len(parts) >= 5:  # Выбор записи для редактирования
                    guest_id = int(parts[2])
                    service_id = int(parts[3])
                    order_date_str = parts[4]
                    order_date = datetime.fromisoformat(order_date_str)
                    # Сохраняем все три значения в состоянии
                    await state.update_data(
                        edit_guest_id=guest_id,
                        edit_service_id=service_id,
                        edit_order_date=order_date
                    )
                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Количество", callback_data="edit_gs_quantity")],
                        [InlineKeyboardButton(text="Статус", callback_data="edit_gs_status")],
                        [InlineKeyboardButton(text="Назад", callback_data="back_to_DB_menu")]
                    ])
                    await callback_query.message.answer(
                        f"Выберите поле для редактирования записи (Гость: {guest_id}, Услуга: {service_id}, Дата: {order_date}):",
                        reply_markup=markup
                    )
                elif callback_query.data == "edit_gs_quantity":
                    await callback_query.message.answer("Введите новое количество:")
                    await state.set_state(DBAdminState.waiting_for_guest_service_edit_gui)
                    await state.update_data(edit_field="quantity")
                elif callback_query.data == "edit_gs_status":
                    await callback_query.message.answer("Введите новый статус:")
                    await state.set_state(DBAdminState.waiting_for_guest_service_edit_gui)
                    await state.update_data(edit_field="status")
                else:
                    raise ValueError("Неизвестная команда редактирования")
            except (ValueError, IndexError) as e:
                logging.error(f"Ошибка разбора callback_data для редактирования: {e}")
                await callback_query.message.answer("Некорректный запрос на редактирование.")
        elif callback_query.data == "edit_gs_quantity":
            await callback_query.message.answer("Введите новое количество:")
            await state.set_state(DBAdminState.waiting_for_guest_service_edit_gui)
            await state.update_data(edit_field="quantity")
        elif callback_query.data == "edit_gs_status":
            await callback_query.message.answer("Введите новый статус:")
            await state.set_state(DBAdminState.waiting_for_guest_service_edit_gui)
            await state.update_data(edit_field="status")
        elif callback_query.data == "delete_guest_service":
            await show_guest_services_for_delete(chat_id)
        elif callback_query.data.startswith("delete_gs_"):
            try:
                # Разбираем callback_data для получения составного ключа
                parts = callback_query.data.split("_")
                logging.info(f"callback_data for delete_gs_: {callback_query.data}")
                if len(parts) < 5:
                    raise ValueError("Некорректный формат callback_data")
                guest_id = int(parts[2])  # Преобразуем в int
                service_id = int(parts[3])  # Преобразуем в int
                order_date_str = parts[4]
                order_date = datetime.fromisoformat(order_date_str)
                # Вызываем функцию удаления с тремя значениями
                if delete_guest_service_db(guest_id, service_id, order_date):
                    await callback_query.message.answer(
                        f"Запись (Гость: {guest_id}, Услуга: {service_id}, Дата: {order_date}) удалена."
                    )
                else:
                    await callback_query.message.answer("Ошибка при удалении записи.")
            except (ValueError, IndexError) as e:
                logging.error(f"Ошибка разбора callback_data для удаления: {e}")
                await callback_query.message.answer("Некорректный запрос на удаление.")
            except pyodbc.Error as e:
                logging.error(f"Ошибка базы данных при удалении GuestServices: {e}")
                await callback_query.message.answer("Ошибка базы данных при удалении.")
        elif callback_query.data == "back_to_apanel":
            await admin_panel(callback_query.message)
        elif callback_query.data == "admin_panel":
            await admin_panel(callback_query.message)
        elif callback_query.data == "back_to_DB_menu":
            await show_db_menu(chat_id)
        elif callback_query.data == "skip_email":
            await state.update_data(email=None)
            await callback_query.message.answer("Введите ваш телефон (или пропустите):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_phone")]]))
            await state.set_state(BookingState.waiting_for_phone)
        elif callback_query.data == "skip_phone":
            await state.update_data(phone=None)
            await callback_query.message.answer("Введите дату заезда (в формате ГГГГ-ММ-ДД):")
            await state.set_state(BookingState.waiting_for_check_in_date)
        elif callback_query.data == "skip_comment":
            await finalize_booking(callback_query.message, state, None)
    except Exception as e:
        logging.error(f"Ошибка обработки callback: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке запроса.")
    await callback_query.answer()

# Обработчики для операций с таблицей Users
@dp.message(DBAdminState.waiting_for_add_user)
async def process_add_user(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 5:
            await message.answer("Неверный формат. Ожидается: telegram_id, first_name, last_name, username, admin(0 или 1)")
            return
        telegram_id, first_name, last_name, username, admin = parts
        telegram_id = int(telegram_id)
        admin = int(admin)
        if add_user_db(telegram_id, first_name, last_name, username, admin):
            await message.answer("Пользователь успешно добавлен.")
        else:
            await message.answer("Ошибка при добавлении пользователя.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для добавления пользователя: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_edit_user)
async def process_edit_user(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 2:
            await message.answer("Неверный формат. Ожидается: telegram_id, admin(0 или 1)")
            return
        telegram_id, admin = parts
        telegram_id = int(telegram_id)
        admin = int(admin)
        if edit_user_db(telegram_id, admin):
            await message.answer("Пользователь успешно обновлён.")
        else:
            await message.answer("Ошибка при редактировании пользователя.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для редактирования пользователя: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_delete_user)
async def process_delete_user(message: types.Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
        if delete_user_db(telegram_id):
            await message.answer("Пользователь успешно удалён.")
        else:
            await message.answer("Ошибка при удалении пользователя.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для удаления пользователя: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

# Обработчики для операций с таблицей Rooms
@dp.message(DBAdminState.waiting_for_add_room)
async def process_add_room(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 5:
            await message.answer("Неверный формат. Ожидается: category, description, price, quantity, status")
            return
        category, description, price, quantity, status = parts
        price = float(price)
        quantity = int(quantity)
        if add_room_db(category, description, price, quantity, status):
            await message.answer("Номер успешно добавлен.")
        else:
            await message.answer("Ошибка при добавлении номера.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для добавления номера: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_edit_room)
async def process_edit_room(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 6:
            await message.answer("Неверный формат. Ожидается: room_id, category, description, price, quantity, status")
            return
        room_id, category, description, price, quantity, status = parts
        room_id = int(room_id)
        price = float(price)
        quantity = int(quantity)
        if edit_room_db(room_id, category, description, price, quantity, status):
            await message.answer("Номер успешно обновлён.")
        else:
            await message.answer("Ошибка при редактировании номера.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для редактирования номера: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_room_edit_gui)
async def process_room_edit_gui(message: types.Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    room_id = data.get("edit_room_id")
    field = data.get("edit_field")
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            if field == "category":
                cursor.execute("UPDATE Rooms SET category = ? WHERE room_id = ?", (new_value, room_id))
            elif field == "description":
                cursor.execute("UPDATE Rooms SET description = ? WHERE room_id = ?", (new_value, room_id))
            elif field == "price":
                cursor.execute("UPDATE Rooms SET price = ? WHERE room_id = ?", (float(new_value), room_id))
            elif field == "quantity":
                cursor.execute("UPDATE Rooms SET quantity = ? WHERE room_id = ?", (int(new_value), room_id))
            elif field == "status":
                cursor.execute("UPDATE Rooms SET status = ? WHERE room_id = ?", (new_value, room_id))
            conn.commit()
            await message.answer(f"Поле '{field}' для номера ID {room_id} успешно обновлено.")
        except Exception as e:
            logging.error(f"Ошибка при редактировании поля {field} для номера ID {room_id}: {e}")
            await message.answer("Ошибка при редактировании поля.")
        finally:
            conn.close()
    await state.clear()

@dp.message(DBAdminState.waiting_for_delete_room)
async def process_delete_room(message: types.Message, state: FSMContext):
    try:
        room_id = int(message.text.strip())
        if delete_room_db(room_id):
            await message.answer("Номер успешно удалён.")
        else:
            await message.answer("Ошибка при удалении номера.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для удаления номера: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

# Обработчики для операций с таблицей RoomImages
@dp.message(DBAdminState.waiting_for_add_image)
async def process_add_image(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 2:
            await message.answer("Неверный формат. Ожидается: room_id, image_url")
            return
        room_id, image_url = parts
        room_id = int(room_id)
        if add_image_db(room_id, image_url):
            await message.answer("Изображение успешно добавлено.")
        else:
            await message.answer("Ошибка при добавлении изображения.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для добавления изображения: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_edit_image)
async def process_edit_image(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 3:
            await message.answer("Неверный формат. Ожидается: room_id, old_image_url, new_image_url")
            return
        room_id, old_url, new_url = parts
        room_id = int(room_id)
        if edit_image_db(room_id, old_url, new_url):
            await message.answer("Изображение успешно обновлено.")
        else:
            await message.answer("Ошибка при редактировании изображения.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для редактирования изображения: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_image_edit_gui)
async def process_image_edit_gui(message: types.Message, state: FSMContext):
    new_url = message.text.strip()
    data = await state.get_data()
    room_id = data.get("edit_image_room_id")
    old_url = data.get("edit_image_old_url")
    if edit_image_db(room_id, old_url, new_url):
        await message.answer("Изображение успешно обновлено.")
    else:
        await message.answer("Ошибка при редактировании изображения.")
    await state.clear()

@dp.message(DBAdminState.waiting_for_delete_image)
async def process_delete_image(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 2:
            await message.answer("Неверный формат. Ожидается: room_id, image_url")
            return
        room_id, image_url = parts
        room_id = int(room_id)
        if delete_image_db(room_id, image_url):
            await message.answer("Изображение успешно удалено.")
        else:
            await message.answer("Ошибка при удалении изображения.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для удаления изображения: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

# Обработчики для операций с таблицей Guests
@dp.message(DBAdminState.waiting_for_add_guest)
async def process_add_guest(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 9:
            await message.answer("Неверный формат. Ожидается: room_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment")
            return
        room_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment = parts
        room_id = int(room_id)
        telegram_id = int(telegram_id)
        email = email if email else None
        phone = phone if phone else None
        comment = comment if comment else None
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO Guests (room_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment, booking_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                    """,
                    (room_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment)
                )
                conn.commit()
                await message.answer("Гость успешно добавлен.")
            except pyodbc.Error as e:
                logging.error(f"Ошибка при добавлении гостя: {e}")
                await message.answer("Ошибка при добавлении гостя.")
            finally:
                conn.close()
        else:
            await message.answer("Ошибка подключения к базе данных.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для добавления гостя: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_edit_guest)
async def process_edit_guest(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) < 2:
            await message.answer("Неверный формат. Ожидается: guest_id, field1=value1, field2=value2, ...")
            return
        guest_id = int(parts[0])
        updates = {}
        for part in parts[1:]:
            if "=" not in part:
                await message.answer(f"Неверный формат для обновления: {part}")
                return
            field, value = part.split("=", 1)
            field = field.strip()
            value = value.strip() or None
            if field not in ["room_id", "telegram_id", "first_name", "last_name", "email", "phone", "check_in_date", "check_out_date", "comment"]:
                await message.answer(f"Недопустимое поле: {field}")
                return
            updates[field] = value
        if not updates:
            await message.answer("Нет полей для обновления.")
            return
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                set_clause = ", ".join([f"{field} = ?" for field in updates])
                values = list(updates.values()) + [guest_id]
                query = f"UPDATE Guests SET {set_clause} WHERE guest_id = ?"
                cursor.execute(query, values)
                conn.commit()
                if cursor.rowcount > 0:
                    await message.answer("Гость успешно обновлён.")
                else:
                    await message.answer("Гость с таким ID не найден.")
            except pyodbc.Error as e:
                logging.error(f"Ошибка при редактировании гостя: {e}")
                await message.answer("Ошибка при редактировании гостя.")
            finally:
                conn.close()
        else:
            await message.answer("Ошибка подключения к базе данных.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для редактирования гостя: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_guest_edit_gui)
async def process_guest_edit_gui(message: types.Message, state: FSMContext):
    new_value = message.text.strip() or None
    data = await state.get_data()
    guest_id = data.get("edit_guest_id")
    field = data.get("edit_field")
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            if field == "room_id":
                cursor.execute("UPDATE Guests SET room_id = ? WHERE guest_id = ?", (int(new_value), guest_id))
            elif field == "telegram_id":
                cursor.execute("UPDATE Guests SET telegram_id = ? WHERE guest_id = ?", (int(new_value), guest_id))
            elif field == "first_name":
                cursor.execute("UPDATE Guests SET first_name = ? WHERE guest_id = ?", (new_value, guest_id))
            elif field == "last_name":
                cursor.execute("UPDATE Guests SET last_name = ? WHERE guest_id = ?", (new_value, guest_id))
            elif field == "email":
                cursor.execute("UPDATE Guests SET email = ? WHERE guest_id = ?", (new_value, guest_id))
            elif field == "phone":
                cursor.execute("UPDATE Guests SET phone = ? WHERE guest_id = ?", (new_value, guest_id))
            elif field == "check_in_date":
                cursor.execute("UPDATE Guests SET check_in_date = ? WHERE guest_id = ?", (new_value, guest_id))
            elif field == "check_out_date":
                cursor.execute("UPDATE Guests SET check_out_date = ? WHERE guest_id = ?", (new_value, guest_id))
            elif field == "comment":
                cursor.execute("UPDATE Guests SET comment = ? WHERE guest_id = ?", (new_value, guest_id))
            conn.commit()
            await message.answer(f"Поле '{field}' для гостя ID {guest_id} успешно обновлено.")
        except Exception as e:
            logging.error(f"Ошибка при редактировании поля {field} для гостя ID {guest_id}: {e}")
            await message.answer("Ошибка при редактировании поля.")
        finally:
            conn.close()
    await state.clear()

@dp.message(DBAdminState.waiting_for_delete_guest)
async def process_delete_guest(message: types.Message, state: FSMContext):
    try:
        guest_id = int(message.text.strip())
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Guests WHERE guest_id = ?", (guest_id,))
                conn.commit()
                if cursor.rowcount > 0:
                    await message.answer("Гость успешно удалён.")
                else:
                    await message.answer("Гость с таким ID не найден.")
            except pyodbc.Error as e:
                logging.error(f"Ошибка при удалении гостя: {e}")
                await message.answer("Ошибка при удалении гостя.")
            finally:
                conn.close()
        else:
            await message.answer("Ошибка подключения к базе данных.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для удаления гостя: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

# Обработчики для операций с таблицей Services
@dp.message(DBAdminState.waiting_for_add_service)
async def process_add_service(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 4:
            await message.answer("Неверный формат. Ожидается: name, price, short_description, detailed_description")
            return
        name, price, short_description, detailed_description = parts
        price = float(price)
        if add_service_db(name, price, short_description, detailed_description):
            await message.answer("Услуга успешно добавлена.")
        else:
            await message.answer("Ошибка при добавлении услуги.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для добавления услуги: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_edit_service)
async def process_edit_service(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 5:
            await message.answer("Неверный формат. Ожидается: service_id, name, price, short_description, detailed_description")
            return
        service_id, name, price, short_description, detailed_description = parts
        service_id = int(service_id)
        price = float(price)
        if edit_service_db(service_id, name, price, short_description, detailed_description):
            await message.answer("Услуга успешно обновлена.")
        else:
            await message.answer("Ошибка при редактировании услуги.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для редактирования услуги: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_service_edit_gui)
async def process_service_edit_gui(message: types.Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    service_id = data.get("edit_service_id")
    field = data.get("edit_field")
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            if field == "name":
                cursor.execute("UPDATE Services SET name = ? WHERE service_id = ?", (new_value, service_id))
            elif field == "price":
                cursor.execute("UPDATE Services SET price = ? WHERE service_id = ?", (float(new_value), service_id))
            elif field == "short_description":
                cursor.execute("UPDATE Services SET short_description = ? WHERE service_id = ?", (new_value, service_id))
            elif field == "detailed_description":
                cursor.execute("UPDATE Services SET detailed_description = ? WHERE service_id = ?", (new_value, service_id))
            conn.commit()
            await message.answer(f"Поле '{field}' для услуги ID {service_id} успешно обновлено.")
        except Exception as e:
            logging.error(f"Ошибка при редактировании поля {field} для услуги ID {service_id}: {e}")
            await message.answer("Ошибка при редактировании поля.")
        finally:
            conn.close()
    await state.clear()

# Обработчики для операций с таблицей GuestServices
@dp.message(DBAdminState.waiting_for_add_guest_service)
async def process_add_guest_service(message: types.Message, state: FSMContext):
    try:
        parts = [part.strip() for part in message.text.split(",")]
        if len(parts) != 4:
            await message.answer("Неверный формат. Ожидается: guest_id, service_id, quantity, status")
            return
        guest_id, service_id, quantity, status = parts
        guest_id = int(guest_id)
        service_id = int(service_id)
        quantity = int(quantity)
        if add_guest_service_db(guest_id, service_id, quantity, status):
            await message.answer("Запись успешно добавлена в GuestServices.")
        else:
            await message.answer("Ошибка при добавлении записи.")
    except Exception as e:
        logging.error(f"Ошибка обработки данных для добавления в GuestServices: {e}")
        await message.answer("Ошибка обработки данных.")
    finally:
        await state.clear()

@dp.message(DBAdminState.waiting_for_guest_service_edit_gui)
async def process_guest_service_edit_gui(message: types.Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    guest_id = data.get("edit_guest_id")
    service_id = data.get("edit_service_id")
    order_date = data.get("edit_order_date")
    field = data.get("edit_field")

    # Проверка наличия всех данных
    if not all([guest_id, service_id, order_date, field]):
        await message.answer("Ошибка: данные для редактирования не найдены.")
        await state.clear()
        return

    try:
        # Преобразование значения в зависимости от поля
        if field == "quantity":
            new_value = int(new_value)  # Убедимся, что quantity — это число
        # Вызов функции с правильными аргументами
        if edit_guest_service_db(guest_id, service_id, order_date, field, new_value):
            await message.answer(f"Поле '{field}' для записи (Гость: {guest_id}, Услуга: {service_id}, Дата: {order_date}) успешно обновлено.")
        else:
            await message.answer("Ошибка при редактировании поля.")
    except ValueError as e:
        await message.answer(f"Ошибка: неверный формат значения для '{field}' ({e}).")
    except pyodbc.Error as e:
        logging.error(f"Ошибка базы данных при редактировании GuestServices: {e}")
        await message.answer("Ошибка базы данных.")
    await state.clear()

# Обработчик заказа дополнительных услуг
@dp.message(OrderServiceState.waiting_for_quantity)
async def process_service_quantity(message: types.Message, state: FSMContext):
    quantity = message.text.strip()
    if not quantity.isdigit() or int(quantity) <= 0:
        await message.answer("Количество должно быть положительным целым числом. Попробуйте еще раз:")
        return
    quantity = int(quantity)
    data = await state.get_data()
    service_id = data['selected_service_id']
    telegram_id = message.from_user.id
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT guest_id FROM Guests WHERE telegram_id = ? AND check_out_date >= GETDATE()", (telegram_id,))
            guest = cursor.fetchone()
            if guest:
                guest_id = guest.guest_id
                cursor.execute(
                    "INSERT INTO GuestServices (guest_id, service_id, quantity, order_date, status) VALUES (?, ?, ?, GETDATE(), 'pending')",
                    (guest_id, service_id, quantity)
                )
                conn.commit()
                await message.answer("Ваш заказ на дополнительную услугу успешно оформлен.")
            else:
                await message.answer("У вас нет активных бронирований для заказа услуг.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при заказе услуги: {e}")
            await message.answer("Произошла ошибка при заказе услуги.")
        finally:
            conn.close()
    else:
        await message.answer("Ошибка подключения к базе данных.")
    await state.clear()

# Обработчик массовой рассылки
@dp.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM Users")
            users = cursor.fetchall()
            for user in users:
                try:
                    await bot.send_message(user.telegram_id, text)
                except Exception as e:
                    logging.error(f"Ошибка при отправке сообщения пользователю {user.telegram_id}: {e}")
            await message.answer("Рассылка завершена.")
        except Exception as e:
            logging.error(f"Ошибка при получении списка пользователей: {e}")
            await message.answer("Ошибка при рассылке.")
        finally:
            conn.close()
    else:
        await message.answer("Ошибка подключения к базе данных.")
    await state.clear()

# Обработчик команды /apanel
@dp.message(Command("apanel"))
async def admin_panel(message: types.Message):
    telegram_id = message.from_user.id
    if not is_admin(telegram_id):
        await message.answer("У вас нет прав администратора")
        return
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Массовая рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="Управление БД", callback_data="DB")]
    ])
    await message.answer("Админ-панель:", reply_markup=markup)

# Обработчики процесса бронирования
@dp.message(BookingState.waiting_for_first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    first_name = message.text.strip()
    if not first_name.isalpha():
        await message.answer("Имя должно содержать только буквы. Попробуйте еще раз:")
        return
    await state.update_data(first_name=first_name)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(BookingState.waiting_for_last_name)

@dp.message(BookingState.waiting_for_last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    last_name = message.text.strip()
    if not last_name.isalpha():
        await message.answer("Фамилия должна содержать только буквы. Попробуйте еще раз:")
        return
    await state.update_data(last_name=last_name)
    await message.answer("Введите ваш email (или пропустите):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_email")]]))
    await state.set_state(BookingState.waiting_for_email)

@dp.message(BookingState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip() or None
    await state.update_data(email=email)
    await message.answer("Введите ваш телефон (или пропустите):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_phone")]]))
    await state.set_state(BookingState.waiting_for_phone)

@dp.message(BookingState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip() or None
    await state.update_data(phone=phone)
    await message.answer("Введите дату заезда (в формате ГГГГ-ММ-ДД):")
    await state.set_state(BookingState.waiting_for_check_in_date)

@dp.message(BookingState.waiting_for_check_in_date)
async def process_check_in_date(message: types.Message, state: FSMContext):
    check_in_date = message.text.strip()
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        today = datetime.today().date()
        one_year_later = today + timedelta(days=365)
        if check_in.date() < today or check_in.date() > one_year_later:
            await message.answer("Дата заезда должна быть от сегодняшнего дня до года вперед. Попробуйте еще раз:")
            return
    except ValueError:
        await message.answer("Неверный формат даты. Используйте ГГГГ-ММ-ДД. Попробуйте еще раз:")
        return
    await state.update_data(check_in_date=check_in_date)
    await message.answer("Введите дату выезда (в формате ГГГГ-ММ-ДД):")
    await state.set_state(BookingState.waiting_for_check_out_date)

@dp.message(BookingState.waiting_for_check_out_date)
async def process_check_out_date(message: types.Message, state: FSMContext):
    check_out_date = message.text.strip()
    try:
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
        data = await state.get_data()
        check_in = datetime.strptime(data['check_in_date'], "%Y-%m-%d")
        today = datetime.today().date()
        one_year_later = today + timedelta(days=365)
        if check_out <= check_in or check_out.date() > one_year_later:
            await message.answer("Дата выезда должна быть позже даты заезда и не более чем через год от сегодняшнего дня. Попробуйте еще раз:")
            return
    except ValueError:
        await message.answer("Неверный формат даты. Используйте ГГГГ-ММ-ДД. Попробуйте еще раз:")
        return
    await state.update_data(check_out_date=check_out_date)
    await message.answer("Введите комментарий (или пропустите):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_comment")]]))
    await state.set_state(BookingState.waiting_for_comment)

@dp.message(BookingState.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text.strip() or None
    await finalize_booking(message, state, comment)

async def finalize_booking(message: types.Message, state: FSMContext, comment: str | None):
    data = await state.get_data()
    room_id = data['room_id']
    telegram_id = data['telegram_id']
    first_name = data['first_name']
    last_name = data['last_name']
    email = data.get('email')
    phone = data.get('phone')
    check_in_date = data['check_in_date']
    check_out_date = data['check_out_date']
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity, category FROM Rooms WHERE room_id = ? AND status = 'available'", (room_id,))
            result = cursor.fetchone()
            if result and result.quantity > 0:
                category = result.category
                cursor.execute(
                    """
                    INSERT INTO Guests (room_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment, booking_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                    """,
                    (room_id, telegram_id, first_name, last_name, email, phone, check_in_date, check_out_date, comment)
                )
                cursor.execute("UPDATE Rooms SET quantity = quantity - 1 WHERE room_id = ?", (room_id,))
                conn.commit()
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_main")],
                    [InlineKeyboardButton(text="Доп услуги", callback_data="additional_services")]
                ])
                await message.answer(
                    "<b>Ваше бронирование успешно завершено.</b>\n\n"
                    "<b>Детали бронирования:</b>\n"
                    f"🏨 <b>Категория номера:</b> {category}\n"
                    f"👤 <b>Имя:</b> {first_name} {last_name}\n"
                    f"📅 <b>Заезд:</b> {check_in_date}\n"
                    f"📅 <b>Выезд:</b> {check_out_date}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                await message.answer("К сожалению, этот номер уже забронирован.")
        except pyodbc.Error as e:
            logging.error(f"Ошибка при бронировании: {e}")
            await message.answer("Произошла ошибка при бронировании.")
        finally:
            conn.close()
    else:
        await message.answer("Ошибка подключения к базе данных.")
    await state.clear()

async def main():
    logging.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())