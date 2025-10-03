# backend/notifier.py
import os, asyncio, re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from typing import Optional
import asyncio

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID_RAW = os.getenv("TELEGRAM_ADMIN_ID", "")
ADMIN_CHAT_IDS = []
if ADMIN_CHAT_ID_RAW.strip():
    try:
        # Поддерживаем несколько ID через запятую
        ADMIN_CHAT_IDS = [int(id_str.strip()) for id_str in ADMIN_CHAT_ID_RAW.split(',') if id_str.strip()]
    except ValueError:
        print(f"⚠️ Ошибка парсинга TELEGRAM_ADMIN_ID: {ADMIN_CHAT_ID_RAW}")
        ADMIN_CHAT_IDS = []

# Для обратной совместимости
ADMIN_CHAT_ID = ADMIN_CHAT_IDS[0] if ADMIN_CHAT_IDS else 0
GROUP_CODE = os.getenv("GROUP_CODE", "cg389")

def format_lesson_output(subject_name: str, lesson_type: str, room: str, teacher: str) -> str:
    """Форматирует вывод занятия с аудиторией и преподавателем"""
    details = []
    # Добавляем аудиторию (room теперь уже отфильтрован в scraper.py)
    if room:
        details.append(f"📍 *{room}*")
    # Добавляем преподавателя
    if teacher:
        details.append(f"👨‍🏫 *{teacher}*")
    
    if details:
        return f"*{subject_name}* *({lesson_type})* | {' | '.join(details)}"
    else:
        return f"*{subject_name}* *({lesson_type})*"

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()

# ---- Rate limit helpers ----
def _is_private_chat(message: Message) -> bool:
    chat = message.chat
    return chat and getattr(chat, 'type', '') == 'private'

async def _check_and_increment_limit(message: Message, limit: int = 3) -> bool:
    """Возвращает True, если можно выполнять команду (лимит не превышен)."""
    if _is_private_chat(message):
        return True
    try:
        from datetime import datetime
        from db import get_user_daily_count, increment_user_daily_count
        chat_id = int(message.chat.id)
        user_id = int(message.from_user.id) if message.from_user else 0
        today = datetime.utcnow().strftime('%Y-%m-%d')
        current = get_user_daily_count(chat_id, user_id, today)
        if current >= limit:
            return False
        increment_user_daily_count(chat_id, user_id, today)
        return True
    except Exception as e:
        print(f"RateLimit check error: {e}")
        return True

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not bot:
        await message.answer("❌ Бот не настроен. Проверьте TELEGRAM_BOT_TOKEN")
        return
    
    # Создаем кнопку для открытия Web App
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 ОТКРЫТЬ РАСПИСАНИЕ", 
            web_app={"url": "https://anf1project.ru/schedule"}
        )]
    ])
    
    await message.answer(
        "🚀 Привет! Я бот для отслеживания расписания BIiK.\n\n"
        "📋 Доступные команды:\n"
        "/schedule - Показать расписание\n"
        "/status - Статус скрапера\n"
        "/help - Помощь\n\n"
        "💡 Или нажми кнопку ниже для красивого интерфейса!",
        reply_markup=keyboard
    )

# Обработчик команды /schedule
@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    allowed = await _check_and_increment_limit(message, limit=3)
    if not allowed:
        await message.reply("⏳ Лимит 3 запроса в сутки в этом чате. Напиши мне в личку — без ограничений.")
        return
    try:
        from db import list_versions
        from datetime import datetime, timedelta
        items = list_versions(GROUP_CODE, 1)
        if items:
            from json import loads
            data = loads(items[0].payload)
            
            # Определяем на какой день показывать расписание
            now = datetime.now()
            current_hour = now.hour
            
            # Если после 18:00 - показываем завтра
            if current_hour >= 18:
                target_date = now + timedelta(days=1)
                date_text = "завтра"
            else:
                target_date = now
                date_text = "сегодня"
            
            # Форматируем дату для поиска
            target_date_str = target_date.strftime('%d.%m.%Y')
            
            # Группируем по дням
            from collections import defaultdict
            days = defaultdict(list)
            
            for item in data:
                # Извлекаем дату из предмета
                subject = item.get('subject', '')
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', subject)
                if date_match:
                    date_str = date_match.group(1)
                    days[date_str].append(item)
            
            # Ищем расписание на нужный день
            if target_date_str in days:
                schedule_items = days[target_date_str]
                
                # Определяем день недели
                try:
                    date_obj = datetime.strptime(target_date_str, '%d.%m.%Y')
                    weekday = date_obj.strftime('%A').upper()
                    weekday_ru = {
                        'MONDAY': 'ПОНЕДЕЛЬНИК',
                        'TUESDAY': 'ВТОРНИК', 
                        'WEDNESDAY': 'СРЕДА',
                        'THURSDAY': 'ЧЕТВЕРГ',
                        'FRIDAY': 'ПЯТНИЦА',
                        'SATURDAY': 'СУББОТА',
                        'SUNDAY': 'ВОСКРЕСЕНЬЕ'
                    }.get(weekday, weekday)
                    
                    schedule_text = f"📅 РАСПИСАНИЕ НА {date_text.upper()} ({target_date_str})\n"
                    schedule_text += f"🗓 {weekday_ru}\n\n"
                    
                    # Сортируем пары по номеру
                    sorted_items = sorted(schedule_items, key=lambda x: x.get('pair', 0))
                    
                    for item in sorted_items:
                        time = item.get('time', '')
                        subject = item.get('subject', '')
                        room = item.get('room', '')
                        kind = item.get('kind', '')
                        pair = item.get('pair', '')
                        teacher = ''
                        lesson_type = ''
                        
                        # Определяем тип занятия по полю kind
                        if kind == 'Лекция':
                            lesson_type = 'Лекция'
                        elif kind == 'Лабораторная':
                            lesson_type = 'Лабораторная'
                        elif kind == 'Семинар':
                            lesson_type = 'Семинар'
                        elif kind == 'Зачет':
                            lesson_type = 'Зачет'
                        else:
                            # Если kind пустое или любое другое значение - это практика
                            lesson_type = 'Практика'
                        
                        # Извлекаем преподавателя из поля teacher
                        teacher = item.get('teacher', '')
                        
                        # Если поле teacher пустое, пытаемся найти в subject (fallback)
                        if not teacher:
                            if 'Семёнов' in subject:
                                teacher = 'Семёнов В.А.'
                            elif 'Иванов' in subject:
                                teacher = 'Иванов И.И.'
                            elif 'Лумбунова' in subject:
                                teacher = 'Лумбунова Н.Б.'
                            elif 'Извеков' in subject:
                                teacher = 'Извеков Я.О.'
                            elif 'Тюрюханова' in subject:
                                teacher = 'Тюрюханова И.В.'
                            elif 'Елтунова' in subject:
                                teacher = 'Елтунова И.Б.'
                            elif 'Белоусова' in subject:
                                teacher = 'Белоусова М.В.'
                            elif 'Протасов' in subject:
                                teacher = 'Протасов А.Е.'
                            elif 'Убеев' in subject:
                                teacher = 'Убеев А.А.'
                            elif 'Жамбаев' in subject:
                                teacher = 'Жамбаев Б.Ц.'
                        
                        # Очищаем название предмета от технических деталей
                        clean_subject = subject
                        
                        # Убираем дату и день недели из начала (формат: "04.09.2025 Чт-2 | ОС (Практич.) 308 Семёнов В.А.")
                        clean_subject = re.sub(r'^\d{2}\.\d{2}\.\d{4}\s+[А-Яа-я]+-\d+\s*\|\s*', '', clean_subject)
                        
                        # Извлекаем название предмета (первая часть до скобки)
                        subject_parts = clean_subject.split('(')
                        if len(subject_parts) > 1:
                            subject_name = subject_parts[0].strip()
                            # Убираем лишние символы и ссылки
                            subject_name = re.sub(r'[|:]', '', subject_name).strip()
                            subject_name = re.sub(r'\s+', ' ', subject_name).strip()
                        else:
                            subject_name = clean_subject.strip()
                            # Убираем ссылки и лишние пробелы
                            subject_name = re.sub(r'\s+', ' ', subject_name).strip()
                        
                        # Форматируем красиво
                        schedule_text += f"**{pair} пара** {time}\n"
                        schedule_text += format_lesson_output(subject_name, lesson_type, room, teacher)
                        schedule_text += "\n\n"
                    
                    schedule_text += "🔗 ПОСМОТРЕТЬ КАРТОЧКУ: https://biik.ru/rasp/cg389.htm\n"
                    
                except Exception as e:
                    schedule_text = f"❌ Ошибка при обработке даты: {e}"
                
                await message.answer(schedule_text, parse_mode="Markdown")
            else:
                # Если нет расписания на нужный день, показываем ближайшее
                available_dates = sorted(days.keys())
                if available_dates:
                    # Ищем ближайшую дату после текущей
                    target_date_obj = datetime.strptime(target_date_str, '%d.%m.%Y')
                    next_date = None
                    
                    for date_str in available_dates:
                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                        if date_obj >= target_date_obj:
                            next_date = date_str
                            break
                    
                    if next_date:
                        # Показываем расписание на ближайшую дату
                        next_schedule_items = days[next_date]
                        
                        # Определяем день недели для ближайшей даты
                        next_date_obj = datetime.strptime(next_date, '%d.%m.%Y')
                        next_weekday = next_date_obj.strftime('%A').upper()
                        next_weekday_ru = {
                            'MONDAY': 'ПОНЕДЕЛЬНИК',
                            'TUESDAY': 'ВТОРНИК', 
                            'WEDNESDAY': 'СРЕДА',
                            'THURSDAY': 'ЧЕТВЕРГ',
                            'FRIDAY': 'ПЯТНИЦА',
                            'SATURDAY': 'СУББОТА',
                            'SUNDAY': 'ВОСКРЕСЕНЬЕ'
                        }.get(next_weekday, next_weekday)
                        
                        schedule_text = f"📭 Расписания на {date_text} ({target_date_str}) нет.\n\n"
                        schedule_text += f"📅 Ближайшее расписание: {next_date} ({next_weekday_ru})\n\n"
                        
                        # Сортируем пары по номеру
                        sorted_items = sorted(next_schedule_items, key=lambda x: x.get('pair', 0))
                        
                        for item in sorted_items:
                            time = item.get('time', '')
                            subject = item.get('subject', '')
                            room = item.get('room', '')
                            kind = item.get('kind', '')
                            pair = item.get('pair', '')
                            teacher = item.get('teacher', '')
                            lesson_type = ''
                            
                            # Определяем тип занятия по полю kind
                            if kind == 'Лекция':
                                lesson_type = 'Лекция'
                            elif kind == 'Лабораторная':
                                lesson_type = 'Лабораторная'
                            elif kind == 'Семинар':
                                lesson_type = 'Семинар'
                            elif kind == 'Зачет':
                                lesson_type = 'Зачет'
                            else:
                                lesson_type = 'Практика'
                            
                            # Очищаем название предмета
                            clean_subject = subject
                            clean_subject = re.sub(r'^\d{2}\.\d{2}\.\d{4}\s+[А-Яа-я]+-\d+\s*\|\s*', '', clean_subject)
                            
                            # Извлекаем название предмета
                            subject_parts = clean_subject.split('(')
                            if len(subject_parts) > 1:
                                subject_name = subject_parts[0].strip()
                                subject_name = re.sub(r'[|:]', '', subject_name).strip()
                                subject_name = re.sub(r'\s+', ' ', subject_name).strip()
                            else:
                                subject_name = clean_subject.strip()
                                subject_name = re.sub(r'\s+', ' ', subject_name).strip()
                            
                            # Форматируем красиво
                            schedule_text += f"**{pair} пара** {time}\n"
                            schedule_text += format_lesson_output(subject_name, lesson_type, room, teacher)
                            schedule_text += "\n\n"
                        
                        schedule_text += "🔗 ПОСМОТРЕТЬ КАРТОЧКУ: https://biik.ru/rasp/cg389.htm\n"
                        await message.answer(schedule_text, parse_mode="Markdown")
                    else:
                        await message.answer(f"📭 Расписания на {date_text} ({target_date_str}) нет.\n\n"
                                           f"📅 Доступные даты: {', '.join(available_dates)}\n"
                                           f"🔗 https://biik.ru/rasp/cg389.htm")
                else:
                    await message.answer("📭 Расписания пока нет. Ожидается первый прогон скрапера.")
        else:
            await message.answer("📭 Данных о расписании пока нет. Ожидается первый прогон скрапера.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении расписания: {e}")

# Обработчик команды /status
@dp.message(Command("status"))
async def cmd_status(message: Message):
    allowed = await _check_and_increment_limit(message, limit=3)
    if not allowed:
        await message.reply("⏳ Лимит 3 запроса в сутки в этом чате. Напиши мне в личку — без ограничений.")
        return
    try:
        from db import list_versions
        items = list_versions(GROUP_CODE, 1)
        if items:
            status_text = f"✅ Скрапер работает!\n\n"
            status_text += f"📊 Последнее обновление: {items[0].created_at.strftime('%d.%m.%Y %H:%M')}\n"
            status_text += f"📅 Неделя: {items[0].week_start}\n"
            from json import loads
            status_text += f"🔢 Записей в расписании: {len(loads(items[0].payload))}"
        else:
            status_text = "⏳ Скрапер запущен, но данных пока нет"
        await message.answer(status_text)
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении статуса: {e}")

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    # help не ограничиваем
    help_text = (
        "🤖 **Бот расписания BIiK**\n\n"
        "**Команды:**\n"
        "• `/start` - Начать работу с ботом\n"
        "• `/schedule` - Показать расписание на сегодня/завтра\n"
        "• `/date ДД.ММ.ГГГГ` - Показать расписание на конкретную дату\n"
        "• `/status` - Статус работы скрапера\n"
        "• `/help` - Эта справка\n\n"
        "**Примеры:**\n"
        "• `/schedule` - расписание на сегодня (до 18:00) или завтра (после 18:00)\n"
        "• `/date 04.09.2025` - расписание на 4 сентября 2025\n\n"
        "**Автоматические уведомления:**\n"
        "Бот будет отправлять уведомления при изменениях в расписании.\n\n"
        "**Группа:** cg389\n"
        "**Источник:** https://biik.ru/rasp/cg389.htm"
    )
    await message.answer(help_text, parse_mode="Markdown")

# Обработчик команды /date для показа расписания на конкретную дату
@dp.message(Command("date"))
async def cmd_date(message: Message):
    allowed = await _check_and_increment_limit(message, limit=3)
    if not allowed:
        await message.reply("⏳ Лимит 3 запроса в сутки в этом чате. Напиши мне в личку — без ограничений.")
        return
    try:
        # Извлекаем дату из сообщения (формат: /date 04.09.2025)
        text = message.text.strip()
        date_match = re.search(r'/date\s+(\d{2}\.\d{2}\.\d{4})', text)
        
        if not date_match:
            await message.answer("📅 Использование: /date ДД.ММ.ГГГГ\n"
                               "Пример: /date 04.09.2025")
            return
        
        target_date_str = date_match.group(1)
        
        from db import list_versions
        from datetime import datetime
        items = list_versions(GROUP_CODE, 1)
        if items:
            from json import loads
            data = loads(items[0].payload)
            
            # Группируем по дням
            from collections import defaultdict
            days = defaultdict(list)
            
            for item in data:
                subject = item.get('subject', '')
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', subject)
                if date_match:
                    date_str = date_match.group(1)
                    days[date_str].append(item)
            
            # Ищем расписание на указанную дату
            if target_date_str in days:
                schedule_items = days[target_date_str]
                
                # Определяем день недели
                try:
                    date_obj = datetime.strptime(target_date_str, '%d.%m.%Y')
                    weekday = date_obj.strftime('%A').upper()
                    weekday_ru = {
                        'MONDAY': 'ПОНЕДЕЛЬНИК',
                        'TUESDAY': 'ВТОРНИК', 
                        'WEDNESDAY': 'СРЕДА',
                        'THURSDAY': 'ЧЕТВЕРГ',
                        'FRIDAY': 'ПЯТНИЦА',
                        'SATURDAY': 'СУББОТА',
                        'SUNDAY': 'ВОСКРЕСЕНЬЕ'
                    }.get(weekday, weekday)
                    
                    schedule_text = f"📅 РАСПИСАНИЕ НА {target_date_str}\n"
                    schedule_text += f"🗓 {weekday_ru}\n\n"
                    
                    # Сортируем пары по номеру
                    sorted_items = sorted(schedule_items, key=lambda x: x.get('pair', 0))
                    
                    for item in sorted_items:
                        time = item.get('time', '')
                        subject = item.get('subject', '')
                        room = item.get('room', '')
                        kind = item.get('kind', '')
                        pair = item.get('pair', '')
                        teacher = ''
                        lesson_type = ''
                        
                        # Определяем тип занятия по полю kind
                        if kind == 'Лекция':
                            lesson_type = 'Лекция'
                        elif kind == 'Лаб':
                            lesson_type = 'Лабораторная'
                        elif kind == 'Семинар':
                            lesson_type = 'Семинар'
                        elif kind == 'Зачет':
                            lesson_type = 'Зачет'
                        else:
                            lesson_type = 'Практика'
                        
                        # Извлекаем преподавателя из поля teacher
                        teacher = item.get('teacher', '')
                        
                        # Если поле teacher пустое, пытаемся найти в subject (fallback)
                        if not teacher:
                            if 'Семёнов' in subject:
                                teacher = 'Семёнов В.А.'
                            elif 'Иванов' in subject:
                                teacher = 'Иванов И.И.'
                            elif 'Лумбунова' in subject:
                                teacher = 'Лумбунова Н.Б.'
                            elif 'Извеков' in subject:
                                teacher = 'Извеков Я.О.'
                            elif 'Тюрюханова' in subject:
                                teacher = 'Тюрюханова И.В.'
                            elif 'Елтунова' in subject:
                                teacher = 'Елтунова И.Б.'
                            elif 'Белоусова' in subject:
                                teacher = 'Белоусова М.В.'
                            elif 'Протасов' in subject:
                                teacher = 'Протасов А.Е.'
                            elif 'Убеев' in subject:
                                teacher = 'Убеев А.А.'
                            elif 'Жамбаев' in subject:
                                teacher = 'Жамбаев Б.Ц.'
                        
                        # Очищаем название предмета
                        clean_subject = subject
                        
                        # Убираем дату и день недели из начала (формат: "04.09.2025 Чт-2 | ОС (Практич.) 308 Семёнов В.А.)")
                        clean_subject = re.sub(r'^\d{2}\.\d{2}\.\d{4}\s+[А-Яа-я]+-\d+\s*\|\s*', '', clean_subject)
                        
                        # Извлекаем название предмета (первая часть до скобки)
                        subject_parts = clean_subject.split('(')
                        if len(subject_parts) > 1:
                            subject_name = subject_parts[0].strip()
                            # Убираем лишние символы и ссылки
                            subject_name = re.sub(r'[|:]', '', subject_name).strip()
                            subject_name = re.sub(r'\s+', ' ', subject_name).strip()
                        else:
                            subject_name = clean_subject.strip()
                            # Убираем ссылки и лишние пробелы
                            subject_name = re.sub(r'\s+', ' ', subject_name).strip()
                        
                        # Форматируем красиво
                        schedule_text += f"**{pair} пара** {time}\n"
                        schedule_text += format_lesson_output(subject_name, lesson_type, room, teacher)
                        schedule_text += "\n\n"
                    
                    schedule_text += "🔗 ПОСМОТРЕТЬ КАРТОЧКУ: https://biik.ru/rasp/cg389.htm\n"
                    
                except Exception as e:
                    schedule_text = f"❌ Ошибка при обработке даты: {e}"
                
                await message.answer(schedule_text, parse_mode="Markdown")
            else:
                await message.answer(f"📭 Расписания на {target_date_str} нет.\n\n"
                                   f"📅 Доступные даты: {', '.join(sorted(days.keys()))}\n"
                                   f"🔗 https://biik.ru/rasp/cg389.htm")
        else:
            await message.answer("📭 Данных о расписании пока нет. Ожидается первый прогон скрапера.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении расписания: {e}")

async def notify_change(chat_id: int, text: str):
    await bot.send_message(chat_id, text, disable_web_page_preview=True)

async def notify_admin(text: str):
    if ADMIN_CHAT_IDS:
        for chat_id in ADMIN_CHAT_IDS:
            try:
                await notify_change(chat_id, text)
            except Exception as e:
                print(f"⚠️ Не удалось отправить уведомление в чат {chat_id}: {e}")

async def close():
    await dp.stop_polling()
    await bot.session.close()

# Функция для запуска бота
async def start_bot():
    if not bot or not dp:
        print("⚠️ Telegram бот не настроен (отсутствует токен)")
        return
    try:
        # Установим команды бота на старте (общий scope)
        from aiogram.types import BotCommand
        await bot.set_my_commands([
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="schedule", description="Расписание на сегодня/завтра"),
            BotCommand(command="date", description="Расписание на дату"),
            BotCommand(command="status", description="Статус системы"),
            BotCommand(command="help", description="Помощь")
        ])
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Bot error: {e}")
