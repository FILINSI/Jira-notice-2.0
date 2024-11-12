import os
import requests
from jira import JIRA, JIRAError
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError  # Изменено имя импорта для исключения
from telegram.ext import CallbackQueryHandler, ApplicationBuilder, CommandHandler
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
import pytz
import re
import time

# Параметры Jira
JIRA_SERVER = 'https://jira.informatics.ru'  # URL вашего сервера Jira
JIRA_USER = ''  # Ваш логин или email для входа в Jira
JIRA_PASSWORD = ''  # Ваш пароль для входа в Jira

# Параметры Telegram
TELEGRAM_TOKEN = ''  # Токен вашего Telegram бота
TELEGRAM_CHAT_ID = ''  # ID чата или пользователя, куда будут отправляться сообщения

# Добавьте в начало файла после других констант
SUPPORT_STAFF = [
    {"name": "сапп 1", "jira_login": "ivanov"},
    {"name": "сапп 2", "jira_login": "nesterov"},
    {"name": "сапп 3", "jira_login": "bochenkov"},
    # Добавьте других сотрудников по аналогии
]

# Инициализация Jira клиента
jira_options = {'server': JIRA_SERVER}
jira = JIRA(options=jira_options, basic_auth=(JIRA_USER, JIRA_PASSWORD))

# Инициализация Telegram бота
bot = Bot(token=TELEGRAM_TOKEN)

# Словарь для отслеживания статуса задач
task_status = {}

# Глобальная переменная для хранения времени запуска бота
BOT_START_TIME = datetime.now()

# Добавляем глобальную переменную для хранения ID закрепленного сообщения
PINNED_MESSAGE_ID = None

# Глобальные объекты
class DutySystem:
    def __init__(self):
        # Устанавливаем фиксированную начальную дату для графика 2/2
        base_date = datetime(2024, 11, 12).date()  # 11.12.2024
        # Ставим ребят для календаря, заполняем все, как надо
        self.duty_users = {
            "yudin": {
                "name": "Юдин Константин",
                "username": "@yudin",
                "schedule_type": "2/2",
                "start_date": base_date  # Начало смен Юдина
            },
            "obordoev": {
                "name": "Обордоев Вадим",
                "username": "@obordoev",
                "schedule_type": "2/2",
                "start_date": base_date + timedelta(days=2)  # Начало смен Обордоева (через 2 дня)
            },
            "karpuhin": {
                "name": "Карпухин Петр",
                "username": "@karpuhin",
                "schedule_type": "5/2",
                "work_days": [0, 1, 2, 3, 4]
            }
        }
        
        self.duty_schedule = {}

    def is_working_day(self, user_id, date):
        """Проверяет, рабочий ли день у сотрудника"""
        if isinstance(date, datetime):
            date = date.date()
            
        user = self.duty_users.get(user_id)
        if not user:
            return False

        if user["schedule_type"] == "2/2":
            # Для графика 2/2 считаем дни от начальной даты
            days_passed = (date - user["start_date"]).days
            return (days_passed // 2) % 2 == 0

        elif user["schedule_type"] == "5/2":
            # Для графика 5/2 проверяем будний ли день
            return date.weekday() in user["work_days"]

        return False

    async def get_duty_for_date(self, date):
        """Получает дежурного на конкретную дату"""
        if isinstance(date, datetime):
            date = date.date()
            
        date_str = date.strftime('%Y-%m-%d')
        
        # Сначала проверяем ручные назначения
        if date_str in self.duty_schedule:
            return [self.duty_schedule[date_str]]

        duties = []
        
        # Проверяем Карпухина (5/2)
        if date.weekday() in [0, 1, 2, 3, 4]:  # Пн-Пт
            duties.append("karpuhin")
            
        # Проверяем дежурных 2/2
        for user_id in ["yudin", "obordoev"]:
            if self.is_working_day(user_id, date):
                duties.append(user_id)
                
        return duties if duties else None

    async def get_current_duty(self):
        """Получает текущего дежурного"""
        return await self.get_duty_for_date(datetime.now().date())

    async def get_week_schedule(self, start_date=None):
        """Получает расписание на неделю"""
        if not start_date:
            today = datetime.now().date()
            start_date = today - timedelta(days=today.weekday())
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
        
        schedule = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            duty_ids = await self.get_duty_for_date(date)
            
            if duty_ids:
                duty_names = []
                for duty_id in duty_ids:
                    duty_info = self.duty_users[duty_id]
                    duty_names.append(f"{duty_info['name']} ({duty_info['schedule_type']})")
                duty_text = "\n    ".join(duty_names)
            else:
                duty_text = 'Не назначен'
            
            schedule.append({
                'date': date,
                'duty': duty_text
            })
        
        return schedule

    async def set_duty(self, date_str, user_id):
        """Назначает дежурного на дату (ручное назначение)"""
        if user_id in self.duty_users:
            self.duty_schedule[date_str] = user_id
            return True
        return False

# Создаем глобальный экземпляр системы дежурств
duty_system = DutySystem()


def create_task_keyboard(issue_key, is_taken=False):
    """Создает клавиатуру с кнопками для задачи"""
    take_emoji = "✅" if is_taken else "📋"
    take_text = "Взято в работу" if is_taken else "Взять в работу"

    keyboard = [
        [
            InlineKeyboardButton(f"{take_emoji} {take_text}",
                               callback_data=f"take:{issue_key}")
        ],
        [
            InlineKeyboardButton("💬 Комментировать",
                               callback_data=f"comment:{issue_key}"),
            InlineKeyboardButton("👤 Назначить",
                               callback_data=f"assign:{issue_key}")
        ],
        [
            InlineKeyboardButton("📄 Подробности",
                               callback_data=f"details:{issue_key}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_take_action_keyboard(issue_key):
    """Создает клавиатуру с действиями после взятия задачи в работу"""
    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Изменить статус на 'Анализ обращения'",
                callback_data=f"analyze:{issue_key}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔗 Перейти к задаче",
                url=f"{JIRA_SERVER}/browse/{issue_key}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data=f"back:{issue_key}"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_staff_keyboard(issue_key):
    """Создает клавиатуру со списком сотрудников"""
    keyboard = []
    for idx, staff in enumerate(SUPPORT_STAFF):
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {staff['name']}",
                callback_data=f"at:{issue_key}:{idx}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            "🔙 Назад",
            callback_data=f"back:{issue_key}"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


async def send_telegram_message(message, issue_key=None):
    try:
        # Разбиваем строку с ID чатов на список
        chat_ids = TELEGRAM_CHAT_ID.split(',')
        
        # Отправляем сообщение каждому получателю
        for chat_id in chat_ids:
            try:
                if issue_key:
                    # Отправка сообщения с клавиатурой
                    is_taken = task_status.get(issue_key, False)
                    await bot.send_message(
                        chat_id=chat_id.strip(),  # Удаляем лишние пробелы
                        text=message,
                        parse_mode='HTML',
                        reply_markup=create_task_keyboard(issue_key, is_taken)
                    )
                else:
                    # Обычное сообщение без клавиатуры
                    await bot.send_message(
                        chat_id=chat_id.strip(),  # Удаляем лишние пробелы
                        text=message,
                        parse_mode='HTML'
                    )
            except TelegramError as e:
                print(f"Ошибка при отправке сообщения для chat_id {chat_id}: {e}")
                continue  # Продолжаем с следующим получателем даже если текущий не удался
                
    except Exception as e:
        print(f"Общая ошибка при отправке сообщений: {e}")


async def handle_button_click(update, context):
    query = update.callback_query
    try:
        data = query.data.split(':')
        action = data[0]
        issue_key = data[1] if len(data) > 1 else None

        print(f"Получен callback: action={action}, issue_key={issue_key}")  # Отладочный вывод

        if action == 'take':
            current_status = task_status.get(issue_key, False)
            task_status[issue_key] = not current_status

            try:
                issue = jira.issue(issue_key)
                if not current_status:  # Если задача берется в работу
                    await query.message.edit_reply_markup(
                        reply_markup=create_take_action_keyboard(issue_key)
                    )
                    await query.answer("Задача взята в работу")
                else:
                    new_keyboard = create_task_keyboard(issue_key, False)
                    await query.message.edit_reply_markup(reply_markup=new_keyboard)
                    await query.answer("Задача снята с работы")
            except Exception as e:
                print(f"Ошибка при обработке задачи {issue_key}: {e}")
                await query.answer(f"Ошибка при обработке задачи: {str(e)}")

        elif action == 'analyze':
            print(f"Обработка перевода в анализ задачи {issue_key}")
            try:
                issue = jira.issue(issue_key)
                transitions = jira.transitions(issue)
                
                # Получаем текущий статус
                current_status = issue.fields.status.name
                print(f"Текущий статус задачи {issue_key}: {current_status}")
                
                if current_status == "ТИКЕТ СОЗДАН":
                    # Сначала переводим в "Новое обращение"
                    print("Статус 'ТИКЕТ СОЗДАН': выполняем двухшаговый переход")
                    
                    # Шаг 1: Переход в "Новое обращение"
                    transition_id = "271"  # ID перехода в "Новое обращение"
                    print(f"Шаг 1: Переход в 'Новое обращение' (ID: {transition_id})")
                    jira.transition_issue(issue, transition_id)
                    
                    # Получаем обновленные переходы после первого шага
                    transitions = jira.transitions(issue)
                    
                    # Шаг 2: Переход в "Анализ обращения"
                    transition_id = "81"  # ID перехода в "Анализ обращения"
                    print(f"Шаг 2: Переход в 'Анализ обращения' (ID: {transition_id})")
                    jira.transition_issue(issue, transition_id)
                    
                else:
                    # Прямой переход в "Анализ обращения"
                    print(f"Статус '{current_status}': выполняем прямой переход в 'Анализ обращения'")
                    transition_id = "81"
                    jira.transition_issue(issue, transition_id)
                
                # Обновляем UI после всех переходов
                new_keyboard = create_task_keyboard(issue_key, True)
                await query.message.edit_reply_markup(reply_markup=new_keyboard)
                await query.answer("Статус задачи изменен на 'Анализ обращения'")
                print(f"Задача {issue_key} успешно переведена в статус 'Анализ обращения'")
                
            except Exception as e:
                print(f"Ошибка при изменении статуса: {e}")
                await query.answer(f"Ошибка при изменении статуса: {str(e)}")

        elif action == 'comment':
            await query.answer("Функция комментирования в разработке")

        elif action == 'assign':
            new_keyboard = create_staff_keyboard(issue_key)
            await query.message.edit_reply_markup(reply_markup=new_keyboard)
            await query.answer("Выберите сотрудника")

        elif action == 'at':
            try:
                staff_idx = int(data[2])
                if 0 <= staff_idx < len(SUPPORT_STAFF):
                    staff = SUPPORT_STAFF[staff_idx]
                    user_login = staff['jira_login']

                    if not user_login:
                        await query.answer("У сотрудника не указан логин в Jira")
                        return

                    issue = jira.issue(issue_key)
                    jira.assign_issue(issue, user_login)

                    new_keyboard = create_task_keyboard(issue_key)
                    await query.message.edit_reply_markup(reply_markup=new_keyboard)
                    await query.answer(f"Задача {issue_key} назначена на {staff['name']}")
                else:
                    await query.answer("Сотрудник не найден")
            except Exception as e:
                print(f"Ошибка при назначении задачи: {e}")
                await query.answer(f"Ошибка при назначении задачи: {str(e)}")

        elif action == 'back':
            new_keyboard = create_task_keyboard(issue_key, task_status.get(issue_key, False))
            await query.message.edit_reply_markup(reply_markup=new_keyboard)
            await query.answer("Вернулись к основному меню")

        elif action == 'details':
            try:
                issue = jira.issue(issue_key)
                details = f"""
<b>Подробности задачи {issue_key}</b>

Статус: {issue.fields.status.name}
Приоритет: {issue.fields.priority.name}
Создана: {issue.fields.created[:10]}
Автор: {issue.fields.reporter.displayName}
"""
                await bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details,
                    parse_mode='HTML'
                )
                await query.answer()
            except Exception as e:
                print(f"Ошибка при получении деталей: {e}")
                await query.answer(f"Ошибка при получении деталей: {str(e)}")

    except Exception as e:
        print(f"Ошибка при обработке нажатия кнопки: {e}")
        await query.answer(f"Произошла ошибка: {str(e)}")


async def authenticate_and_notify():
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            jira_options = {'server': JIRA_SERVER}
            jira = JIRA(options=jira_options, basic_auth=(JIRA_USER, JIRA_PASSWORD))
            # Проверка подключения к серверу
            server_info = jira.server_info()
            await send_telegram_message("✅ Бот успешно подключн к JIRA\n🔍 Отслеживаю новые задачи...\n\n🔄 Обновление:\n\n - Фикс календаря смен для 2/2 (теперь он будет работать корректно всегда) ")
            return jira

        except JIRAError as e:
            retry_count += 1
            wait_time = 300  # 5 минут

            if "401" in str(e):
                error_msg = " Ошибка аутентификации. Проверьте логин и пароль."
            elif "404" in str(e):
                error_msg = "🔍 Сервер JIRA не найден. Проверьте URL."
            elif "500" in str(e):
                error_msg = "⚠️ Внутренняя ошибка сервера JIRA."
            elif "503" in str(e):
                error_msg = "🔧 Сервер JIRA временно недоступен."
            else:
                error_msg = f"❌ Ошибка подключения к JIRA: {str(e)}"

            await send_telegram_message(
                f"{error_msg}\n"
                f"🔄 Попытка {retry_count} из {max_retries}\n"
                f"⏳ Следующая попытка через {wait_time // 60} минут"
            )

            await asyncio.sleep(wait_time)

        except Exception as e:
            retry_count += 1
            error_msg = f"❌ Неожидання ошибка: {str(e)}"
            await send_telegram_message(
                f"{error_msg}\n"
                f"🔄 Попытка {retry_count} из {max_retries}\n"
                f"⏳ Следующая попытка через 5 минут"
            )
            await asyncio.sleep(300)

    raise Exception("❌ Превышено максимальное количество попыток подключения")


# Хранение ID последних задач, чтобы избегать повторных уведомлений
last_seen_issue_id = None


def create_formatted_message(issue, issue_type="New"):
    try:
        print(f"Создание сообщения для задачи {issue.key}")  # Отладочный вывод
        
        priority = getattr(issue.fields, 'priority', None)
        priority_text = priority.name if priority else "Не указан"

        # Эмодзи для приорита
        priority_emoji = {
            "Бомбит": "💣",
            "Срочный": "🔴",
            "Высокий": "🟠",
            "Нормальный": "🟡",
            "Низкий": "⚪"
        }.get(priority_text, "⚪")

        # Эмодзи для типа задачи
        type_emoji = {
            "Ошибка": "❌",
            "Консультация": "",
            "Задаа": "✅",
            "Доступы": "🔑",
            "Техническая поддержка": "🛠️",
            "Виртуальный класс": "💻",
            "Mark support": "📋",
            "TGBot": "🤖",
            "Инцидент": "⚡"
        }

        reporter = getattr(issue.fields, 'reporter', None)
        reporter_name = reporter.displayName if reporter else "Неизвестный"

        # Получаем тип задачи
        issue_type_name = getattr(issue.fields, 'issuetype', None)
        issue_type_name = issue_type_name.name if issue_type_name else "Неизвестный тип"
        type_emoji_display = type_emoji.get(issue_type_name, "📝")

        # Форматируем описание
        description = issue.fields.description or "Описание отсуттвует"
        description = description.replace('\n', '\n    ')
        if len(description) > 300:
            description = description[:297] + "..."

        message = f"""
╔══ 🎫 НОВАЯ ЗАДАЧА В JIRA 🎫 ══╗

➤ *Название:*
    {issue.fields.summary}

➤ *Тип задачи:*
    {type_emoji_display} {issue_type_name}

➤ *Приоритет:*
    {priority_emoji} {priority_text}

➤ *Создал:*
    {reporter_name}

➤ *Описание:*
    {description}

➤ *Ссылка на задачу:*
    {JIRA_SERVER}/browse/{issue.key}

"""
        print(f"Сообщение создано успешно для {issue.key}")  # Отладочный вывод
        return message
    except Exception as e:
        print(f"Ошибка при создании сообщения: {e}")
        return f"Ошибка при создании сообщения для задачи {issue.key}: {str(e)}"


async def check_new_issues(jira):
    global last_seen_issue_id
    print("Проверка новых задач...")
    
    try:
        chat_ids = [id.strip() for id in TELEGRAM_CHAT_ID.split(',')]
        print(f"Список ID чатов для рассылки: {chat_ids}")
        
        jql_query = 'project = "Поддержка Informatics" AND status in ("Новое обращение", Ожидание, "ТИКЕТ СОЗДАН") and NOT issuetype = "Техническая поддержка " and NOT issuetype = Доступы'
        issues = jira.search_issues(jql_query, maxResults=1)
        
        if not issues:
            print("Задач не найдено")
            return
            
        latest_issue = issues[0]
        current_issue_id = latest_issue.id
        
        # Проверяем, отправляли ли мы уже уведомление об этой задаче
        if last_seen_issue_id == current_issue_id:
            print(f"Задача {latest_issue.key} уже обработана, пропускаем")
            return
            
        print(f"Новая задача: {latest_issue.key} (ID: {current_issue_id})")
        
        # Обновляем ID последней задачи ДО отправки сообщений
        last_seen_issue_id = current_issue_id
        
        # Создаем сообщение один раз
        message = create_formatted_message(latest_issue)
        keyboard = create_task_keyboard(latest_issue.key, False)
        
        # Отправляем сообщение каждому получателю
        for chat_id in chat_ids:
            print(f"Отправка сообщения для chat_id: {chat_id}")
            try:
                await bot.send_message(
                    chat_id=int(chat_id),
                    text=message,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                print(f"Сообщение успешно отправлено в чат {chat_id}")
                
            except Exception as e:
                print(f"Ошибка при отправке в чат {chat_id}: {str(e)}")
                continue
                
    except Exception as e:
        error_msg = f"Ошибка при проверке задач: {str(e)}"
        print(error_msg)
        for chat_id in chat_ids:
            try:
                await bot.send_message(
                    chat_id=int(chat_id),
                    text=f"❌ {error_msg}",
                    parse_mode='HTML'
                )
            except Exception as send_error:
                print(f"Не удалось отправить сообщение об ошибке в чат {chat_id}: {str(send_error)}")


async def scheduler(jira):
    while True:
        await check_new_issues(jira)
        await asyncio.sleep(30)  # Проверка каждые 30 секунд


async def main():
    # Инициализация приложения
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("tasks", show_active_tasks))
    application.add_handler(CommandHandler("urgent", show_urgent_tasks))
    application.add_handler(CommandHandler("search", start_search))
    application.add_handler(CommandHandler("status", check_status))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("services", check_services_command))
    
    # Важно: обработчик кнопок должен быть зарегистрирован ПОСЛЕ команд
    # и обрабатывать ВСЕ паттерны callback_data
    application.add_handler(CallbackQueryHandler(handle_button_click, pattern=None))

    # Создаем задачи для асинхронного выполнения
    async def run_polling():
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            await application.stop()

    async def run_jira_checker():
        while True:
            try:
                jira = await authenticate_and_notify()
                await scheduler(jira)
            except Exception as e:
                await send_telegram_message(
                    f"🚨 Критическая ошибка в работе бота: {str(e)}\n"
                    "🔄 Перезапуск через 10 секунд..."
                )
                await asyncio.sleep(10)

    # Запускаем обе задачи параллельно
    try:
        await asyncio.gather(
            run_polling(),
            run_jira_checker()
        )
    except Exception as e:
        print(f"Ошибка в main: {e}")
    finally:
        if application.running:
            await application.stop()


# Добавьте новые функции для обработки команд
async def show_active_tasks(query, context):
    """Показывает активные задачи"""
    try:
        # JQL запрос для активных задач
        jql = 'project = "Поддержка Informatics" AND status not in (Closed, Resolved) ORDER BY created DESC'
        issues = jira.search_issues(jql, maxResults=10)

        if not issues:
            await query.message.edit_text(
                "🔍 Активных задач не найдено",
                reply_markup=create_main_menu_keyboard()
            )
            return

        # Формируем сообщение
        message = "📋 *Активные задачи:*\n\n"
        
        for idx, issue in enumerate(issues, 1):
            priority = getattr(issue.fields, 'priority', None)
            priority_text = priority.name if priority else "Не указан"
            
            # Эмодзи для приоритета
            priority_emoji = {
                "Бомбит": "💣",
                "Срочный": "🔴",
                "Высокий": "🟠",
                "Нормальный": "🟡",
                "Низкий": "⚪"
            }.get(priority_text, "⚪")

            # Формируем строку для задачи
            message += (
                f"{idx}. {priority_emoji} [{issue.key}]({JIRA_SERVER}/browse/{issue.key})\n"
                f"   *{issue.fields.summary[:100]}*\n"
                f"   Статус: {issue.fields.status.name}\n\n"
            )

        # Добавляем подвал сообщения
        message += "\n_Показаны последние 10 задач_"

        await query.message.edit_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=create_main_menu_keyboard()
        )

    except Exception as e:
        print(f"Ошибка при получении задач: {e}")
        await query.message.edit_text(
            "❌ Ошибка при получении задач",
            reply_markup=create_main_menu_keyboard()
        )

async def show_urgent_tasks(query, context):
    """Показывает срочные задачи"""
    try:
        # JQL запрос для срочных задач
        jql = '''project = "Поддержка Informatics" AND 
                (priority in (Highest, High) OR 
                 duedate < now()) AND 
                status not in (Closed, Resolved)
                ORDER BY priority DESC, created DESC'''
        issues = jira.search_issues(jql, maxResults=10)

        if not issues:
            await query.message.edit_text(
                "🔍 Срочных задач не найдено",
                reply_markup=create_main_menu_keyboard()
            )
            return

        # Формируем сообщение
        message = "🚨 *Срочные задачи:*\n\n"
        
        for idx, issue in enumerate(issues, 1):
            priority = getattr(issue.fields, 'priority', None)
            priority_text = priority.name if priority else "Не указан"
            
            priority_emoji = {
                "Бомбит": "💣",
                "Срочный": "🔴",
                "Высокий": "🟠",
                "Нормальный": "🟡",
                "Низкий": "⚪"
            }.get(priority_text, "⚪")

            message += (
                f"{idx}. {priority_emoji} [{issue.key}]({JIRA_SERVER}/browse/{issue.key})\n"
                f"   *{issue.fields.summary[:100]}*\n"
                f"   Статус: {issue.fields.status.name}\n\n"
            )

        message += "\n_Показаны последние 10 срочных задач_"

        await query.message.edit_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=create_main_menu_keyboard()
        )
    except Exception as e:
        print(f"Ошибка при получении задач: {e}")
        await query.message.edit_text(
            "❌ Ошибка при получении задач",
            reply_markup=create_main_menu_keyboard()
        )

async def start_search(update, context):
    """Поиск задач"""
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Для поиска задач используйте команду так:\n"
            "/search <текст для поиска>"
        )
        return

    search_text = ' '.join(context.args)
    try:
        jql = f'project = "Поддержка Informatics" AND (summary ~ "{search_text}" OR description ~ "{search_text}")'
        issues = jira.search_issues(jql, maxResults=10)

        if not issues:
            await update.message.reply_text(
                f"🔍 Задач по запросу '{search_text}' не найдено",
                reply_markup=create_main_menu_keyboard()
            )
            return

        # Формируем сообщение
        message = f"🔍 *Результаты поиска по запросу:* _{search_text}_\n\n"
        
        for idx, issue in enumerate(issues, 1):
            priority = getattr(issue.fields, 'priority', None)
            priority_text = priority.name if priority else "Не указан"
            
            # Эмодзи для приоритета
            priority_emoji = {
                "Бомбит": "💣",
                "Срочный": "🔴",
                "Высокий": "🟠",
                "Нормальный": "🟡",
                "Низкий": "⚪"
            }.get(priority_text, "⚪")

            # Формируем строку для задачи
            message += (
                f"{idx}. {priority_emoji} [{issue.key}]({JIRA_SERVER}/browse/{issue.key})\n"
                f"   *{issue.fields.summary[:100]}*\n"
                f"   Статус: {issue.fields.status.name}\n\n"
            )

        # Добавляем подвал сообщения
        message += "\n_Показаны первые 10 результатов_"

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=create_main_menu_keyboard()
        )

    except Exception as e:
        print(f"Ошибка при поиске задач: {e}")
        await update.message.reply_text(
            "❌ Ошибка при поиске задач",
            reply_markup=create_main_menu_keyboard()
        )

async def check_status(update, context):
    """Проверяет статус системы"""
    try:
        # Проверяем подключение к Jira
        server_info = jira.server_info()

        status_message = f"""
🟢 *Статус системы*

*JIRA:*
✅ Сервер: {server_info['serverTitle']}
✅ Версия: {server_info['version']}
✅ Время ответа: OK

*Telegram Bot:*
✅ Активен и отвечает
"""
        await update.message.reply_text(status_message, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при проверке статуса: {str(e)}")

async def show_help(update, context):
    """Показывает справку по командам"""
    help_text = """
🤖 *Справочная информация*

*Основные команды:*
/start - перезапуск бота и вывод меню
/tasks - активные задачи в работе
/urgent - срочные и просроченные задачи
/search <текст> - поиск по задачам
/status - проверка работы систем
/services - проверка доступности сервисов
/help - эта справка

*Работа с задачами:*
• "📋 Взять в работу" - начать работу над задачей
• "💬 Комментировать (в разработке)" - добавить комментарий
• "👤 Назначить" - назначить на сотрудника
• "📄 Подробности" - детали задачи

*Дежурства:*
• График 5/2 (Пн-Пт): Карпухин П.
• График 2/2: Юдин К., Обордоев В.

*Мониторинг сервисов:*
• informatics.ru - прод
• teacher.edu-app.ru - тичер
• jira.informatics.ru - жира
• my.mshp.ru - платформа 2035

*Поддержка:*
При проблемах с ботом обращайтесь к @yudin
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

def create_navigation_keyboard(current_page, total_pages, command):
    """Создает клавиатуру для навигации по страницам"""
    keyboard = []
    buttons = []

    if current_page > 1:
        buttons.append(
            InlineKeyboardButton("◀️ Назад", callback_data=f"nav:{command}:{current_page - 1}")
        )

    buttons.append(
        InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="noop")
    )

    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton("Вперед ▶️", callback_data=f"nav:{command}:{current_page + 1}")
        )

    keyboard.append(buttons)
    return InlineKeyboardMarkup(keyboard)

def create_stats_keyboard():
    """Создает клавиатуру для статистики"""
    keyboard = [
        [
            InlineKeyboardButton("📊 За неделю", callback_data="stats:week"),
            InlineKeyboardButton("📈 За месяц", callback_data="stats:month")
        ],
        [
            InlineKeyboardButton("👥 По сотрудникам", callback_data="stats:users"),
            InlineKeyboardButton("🎯 По приоритетам", callback_data="stats:priorities")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Добавляем обработку новых callback-кнопок
async def handle_button_click(update, context):
    query = update.callback_query
    try:
        bot_stats.add_user(update.effective_user.id)  # Добавляем пользователя в статистику
        data = query.data.split(':')
        action = data[0]

        if action == 'menu':
            menu_action = data[1]
            if menu_action == 'tasks':
                await show_active_tasks(query, context)
            elif menu_action == 'urgent':
                await show_urgent_tasks(query, context)
            elif menu_action == 'search':
                await query.message.edit_text(
                    "🔍 Для поиска используйте команду:\n/search <текст для поиска>",
                    reply_markup=create_main_menu_keyboard()
                )
            elif menu_action == 'status':
                await show_status_from_callback(query)
            elif menu_action == 'help':
                await show_help_from_callback(query)
            elif menu_action == 'services':
                message = await check_edu_services()
                keyboard = [
                    [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="menu:back")]
                ]
                await query.message.edit_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif menu_action == 'back':
                await query.message.edit_text(
                    "Выберите действие:",
                    reply_markup=create_main_menu_keyboard()
                )
            await query.answer()

        elif action == 'take':
            # Существующий код обработки кнопки "Взять в работу"
            ...

        elif action == 'analyze':
            # Существующий код обработки кнопки "Анализ обращения"
            ...

        elif action == 'back':
            # Существующий код обработки кнопки "Назад"
            ...

    except Exception as e:
        bot_stats.add_error(e)  # Записываем ошибку
        print(f"Ошибка при обработке нажатия кнопки: {e}")
        await query.answer(f"Произошла ошибка: {str(e)}")

# Функции для отображения разных типов статистики
async def show_week_stats(query):
    # Получаем статистику за неделю
    week_ago = (datetime.now(pytz.UTC) - timedelta(days=7)).strftime('%Y-%m-%d')
    stats = await get_period_stats(week_ago)

    message = f"""
📊 *Статистика за неделю*

📥 Новых задач: {stats['new']}
✅ Решено задач: {stats['resolved']}
⚡ В работе: {stats['in_progress']}
⏳ Ожидают: {stats['waiting']}
"""
    await query.message.edit_text(message, parse_mode='Markdown', reply_markup=create_stats_keyboard())
    await query.answer()

async def show_month_stats(query):
    # Аналогично show_week_stats, но за месяц
    pass

async def show_users_stats(query):
    # Статистика по сотрудникам
    pass

async def show_priorities_stats(query):
    # Статистика по приоритетам
    pass

# Вспомогательная функция для получения статистики
async def get_period_stats(start_date):
    try:
        new_tasks_jql = f'project = "Поддержка Informatics" AND created >= "{start_date}"'
        resolved_tasks_jql = f'project = "Поддержка Informatics" AND resolved >= "{start_date}"'
        in_progress_jql = 'project = "Поддержка Informatics" AND status = "In Progress"'
        waiting_jql = 'project = "Поддержка Informatics" AND status = Waiting'

        return {
            'new': len(jira.search_issues(new_tasks_jql, maxResults=0)),
            'resolved': len(jira.search_issues(resolved_tasks_jql, maxResults=0)),
            'in_progress': len(jira.search_issues(in_progress_jql, maxResults=0)),
            'waiting': len(jira.search_issues(waiting_jql, maxResults=0))
        }
    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
        return {'new': 0, 'resolved': 0, 'in_progress': 0, 'waiting': 0}

def create_main_menu_keyboard():
    """Создает основную клавиатуру меню"""
    keyboard = [
        [
            InlineKeyboardButton("📋 Активные задачи", callback_data="menu:tasks"),
            InlineKeyboardButton("🚨 Срочные задачи", callback_data="menu:urgent")
        ],
        [
            InlineKeyboardButton("📥 Последние задачи", callback_data="menu:recent"),
            InlineKeyboardButton("👥 График дежурств", callback_data="menu:duty")
        ],
        [
            InlineKeyboardButton("🏥 Статус сервисов", callback_data="menu:services"),
            InlineKeyboardButton("📊 Статус системы", callback_data="menu:status")
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="menu:help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update, context):
    """Обработчик команды /start"""
    global PINNED_MESSAGE_ID
    
    # Если есть старое закрепленное сообщение, удаляем его
    if PINNED_MESSAGE_ID:
        try:
            await bot.unpin_chat_message(chat_id=update.effective_chat.id, message_id=PINNED_MESSAGE_ID)
            await bot.delete_message(chat_id=update.effective_chat.id, message_id=PINNED_MESSAGE_ID)
        except Exception as e:
            print(f"Ошибка при удалении старого закрепленного сообщения: {e}")

    welcome_message = """
📌 *Инструкция по использованию бота*

Используйте кнопки меню ниже для:
• 📋 Активные задачи - просмотр текущих задач
• 🚨 Срочные задачи - задачи с высоким приоритетом
• 👥 График дежурств - кто сегодня на смене
• ℹ️ Статус системы - проверка работы сервисов
• 🏥 Статус сервисов - доступность платформ
• ❓ Помощь - подробная инструкция

*Быстрые команды:*
/tasks - активные задачи
/urgent - срочные задачи
/search - поиск по задачам
/status - проверка статуса
/help - справка

Выберите нужное действие из меню ниже:
"""
    # Отправляем и закрепляем новое сообщение
    try:
        message = await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=create_main_menu_keyboard()
        )
        await message.pin(disable_notification=True)
        PINNED_MESSAGE_ID = message.message_id
        
        # Удаляем дополнительное сообщение о закреплении
        try:
            await bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=message.message_id + 1
            )
        except Exception as e:
            print(f"Ошибка при удалении сообщения о закреплении: {e}")
            
    except Exception as e:
        print(f"Ошибка при создании закрепленного сообщения: {e}")
        bot_stats.add_error(e)

# Добавляем новые функции для обработки callback-кнопок
async def show_status_from_callback(query):
    """Показывает статус системы через callback"""
    try:
        # Проверяем JIRA
        try:
            server_info = jira.server_info()
            jira_status = (
                f"✅ Сервер: {server_info.get('serverTitle', 'Jira')}\n"
                f"✅ Версия: {server_info.get('version', 'N/A')}\n"
                f"✅ Время ответа: OK"
            )
        except Exception as e:
            print(f"Ошибка при проверке Jira: {e}")
            jira_status = "❌ Сервер недоступен"

        # Получаем статистику бота
        uptime = bot_stats.get_uptime()
        tasks = bot_stats.processed_tasks
        errors = bot_stats.errors_count
        users = len(bot_stats.active_users)
        last_error = bot_stats.last_error

        # Формируем сообщение о статусе
        status_message = f"""
🟢 *Статус системы*

*JIRA:*
{jira_status}

*Telegram Bot:*
⏱️ Время работы: {uptime}
📊 Обработано задач: {tasks}
👥 Активных пользователей: 3
❌ Ошибок: {errors}

*Последняя ошибка:*
{last_error['message'] + ' (' + last_error['time'].strftime('%H:%M:%S') + ')' if last_error else 'Нет ошибок'}
"""
        # Отправляем сообщение
        await query.message.edit_text(
            status_message,
            parse_mode='Markdown',
            reply_markup=create_main_menu_keyboard()
        )

    except Exception as e:
        print(f"Ошибка при проверке статуса: {e}")
        bot_stats.add_error(e)
        await query.message.edit_text(
            "❌ Ошибка при проверке статуса\nБот работает",
            reply_markup=create_main_menu_keyboard()
        )

async def show_help_from_callback(query):
    """Показывает справку через callback"""
    help_text = """
🤖 *Справочная информация*

*Основные команды:*
/start - перезапуск бота и вывод меню
/tasks - активные задачи в работе
/urgent - срочные и просроченные задачи
/search <текст> - поиск по задачам
/status - проверка работы систем
/services - проверка доступности сервисов
/help - эта справка

*Работа с задачами:*
• "📋 Взять в работу" - начать работу над задачей
• "💬 Комментировать" - добавить комментарий
• "👤 Назначить" - назначить на сотрудника
• "📄 Подробности" - детали задачи

*Дежурства:*
• График 5/2 (Пн-Пт): Карпухин П.
• График 2/2: Юдин К., Обордоев В.

*Мониторинг сервисов:*
• informatics.ru - прод
• teacher.edu-app.ru - тичер
• jira.informatics.ru - жира
• my.mshp.ru - платформа 2035

*Поддержка:*
При проблемах с ботом обращайтесь к @filinsi
"""
    await query.message.edit_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=create_main_menu_keyboard()
    )

def get_uptime():
    """Возвращает время работы бота"""
    try:
        uptime = datetime.now() - BOT_START_TIME
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        parts.append(f"{seconds}с")
        
        return " ".join(parts)
    except:
        return "недоступно"

async def show_statistics(update, context):
    """Shows statistics for Jira tasks"""
    try:
        # Create stats keyboard
        await update.message.reply_text(
            "📊 *Выберите тип статистики:*",
            parse_mode='Markdown',
            reply_markup=create_stats_keyboard()
        )
    except Exception as e:
        print(f"Ошибка при показе статистики: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении статистики",
            reply_markup=create_main_menu_keyboard()
        )

async def check_edu_services():
    """Проверяет доступность образовательных сервисов"""
    SERVICES = {
        'Прод': 'https://informatics.ru',
        'Тичер прода': 'https://teacher.edu-app.ru',
        'Jira': 'https://jira.informatics.ru',
        '2035': 'https://my.mshp.ru'
    }

    results = {}
    message = "🏥 Статус образовательных сервисов:\n\n"

    for name, url in SERVICES.items():
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5, verify=False)
            response_time = round((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                status = "✅"
                speed = "🚀" if response_time < 500 else "⚡" if response_time < 1000 else "🐢"
            else:
                status = "⚠️"
                speed = "❌"
            
            results[name] = {
                'status': response.status_code,
                'response_time': response_time,
                'emoji_status': status,
                'emoji_speed': speed
            }
            
        except requests.exceptions.ConnectionError:
            results[name] = {
                'status': 'Недоступен',
                'emoji_status': "❌",
                'emoji_speed': "❌"
            }
        except requests.exceptions.Timeout:
            results[name] = {
                'status': 'Таймаут',
                'emoji_status': "⚠️",
                'emoji_speed': "❌"
            }
        except Exception as e:
            results[name] = {
                'status': f'Ошибка: {str(e)}',
                'emoji_status': "❌",
                'emoji_speed': "❌"
            }

    # Формируем сообщение
    for name, info in results.items():
        message += f"{info['emoji_status']} {name}: "
        
        if isinstance(info['status'], int):
            message += f"HTTP {info['status']}"
            message += f" {info['emoji_speed']} ({info['response_time']}ms)\n"
        else:
            message += f"{info['status']}\n"

    return message

# Добавляем команду в список обработчиков
async def check_services_command(update, context):
    """Обработчик команды /services"""
    message = await check_edu_services()
    await update.message.reply_text(message)

class BotStats:
    def __init__(self):
        self.start_time = datetime.now()
        self.processed_tasks = 0
        self.commands_used = 0
        self.errors_count = 0
        self.last_error = None
        self.active_users = set()

    def get_uptime(self):
        """Возвращает время работы бота в читаемом формате"""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        parts.append(f"{seconds}с")
        
        return " ".join(parts)

    def increment_tasks(self):
        self.processed_tasks += 1

    def add_error(self, error):
        self.errors_count += 1
        self.last_error = {
            "message": str(error),
            "time": datetime.now()
        }

    def add_user(self, user_id):
        self.active_users.add(user_id)

bot_stats = BotStats()

async def show_duty_schedule(query, schedule=None):
    """Показывает график дежурств"""
    if schedule is None:
        schedule = await duty_system.get_week_schedule()
    
    message = "👥 *График дежурств*\n\n"
    
    # Добавляем текущих дежурных
    current_duties = await duty_system.get_duty_for_date(datetime.now().date())
    if current_duties:
        message += "*Сейчас дежурят:*\n"
        for duty_id in current_duties:
            duty_info = duty_system.duty_users[duty_id]
            message += f"🎯 {duty_info['name']} ({duty_info['schedule_type']})\n"
        message += "\n"
    
    # Добавляем график на неделю
    message += "*График на неделю:*\n"
    weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    today = datetime.now().date()
    
    for day in schedule:
        date_str = day['date'].strftime('%d.%m')
        weekday = weekdays[day['date'].weekday()]
        
        if day['date'] == today:
            day_marker = "👉 "
        elif day['date'].weekday() < 5:
            day_marker = "📅 "
        else:
            day_marker = "🌅 "
        
        message += f"{day_marker}*{weekday}* ({date_str})\n"
        message += f"    {day['duty']}\n"
    
    # Добавляем легенду
    message += "\n*Графики работы:*\n"
    message += "📆 5/2 (Пн-Пт) - Карпухин П.\n"
    message += "🔄 2/2 - Юдин К., Обордоев В.\n"
    
    keyboard = [
        [
            InlineKeyboardButton("◀️ Пред. неделя", callback_data="duty:prev_week"),
            InlineKeyboardButton("След. неделя ▶️", callback_data="duty:next_week")
        ],
        [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="menu:back")]
    ]
    
    await query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# Обновляем обработчик кнопок меню
async def handle_button_click(update, context):
    query = update.callback_query
    try:
        print(f"Получен callback query: {query.data}")
        data = query.data.split(':')
        action = data[0]
        
        # Обработка кнопок меню
        if action == 'menu':
            menu_action = data[1]
            print(f"Обработка действия меню: {menu_action}")
            
            if menu_action == 'tasks':
                await show_active_tasks(query, context)
            elif menu_action == 'urgent':
                await show_urgent_tasks(query, context)
            elif menu_action == 'duty':
                await show_duty_schedule(query)
            elif menu_action == 'status':
                await show_status_from_callback(query)
            elif menu_action == 'services':
                message = await check_edu_services()
                keyboard = [
                    [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="menu:back")]
                ]
                await query.message.edit_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif menu_action == 'help':
                await show_help_from_callback(query)
            elif menu_action == 'back':
                await query.message.edit_text(
                    "Выберите действие:",
                    reply_markup=create_main_menu_keyboard()
                )
            await query.answer()
            return

        # Если это не меню, значит это действия с задачами
        issue_key = data[1] if len(data) > 1 else None
        print(f"Разбор callback data: action={action}, issue_key={issue_key}")

        # Добавляем обработку analyze
        if action == 'analyze':
            print(f"Обработка перевода в анализ задачи {issue_key}")
            try:
                issue = jira.issue(issue_key)
                transitions = jira.transitions(issue)
                
                # Получаем текущий статус
                current_status = issue.fields.status.name
                print(f"Текущий статус задачи {issue_key}: {current_status}")
                
                if current_status == "ТИКЕТ СОЗДАН":
                    # Сначала переводим в "Новое обращение"
                    print("Статус 'ТИКЕТ СОЗДАН': выполняем двухшаговый переход")
                    
                    # Шаг 1: Переход в "Новое обращение"
                    transition_id = "271"  # ID перехода в "Новое обращение"
                    print(f"Шаг 1: Переход в 'Новое обращение' (ID: {transition_id})")
                    jira.transition_issue(issue, transition_id)
                    
                    # Получаем обновленные переходы после первого шага
                    transitions = jira.transitions(issue)
                    
                    # Шаг 2: Переход в "Анализ обращения"
                    transition_id = "81"  # ID перехода в "Анализ обращения"
                    print(f"Шаг 2: Переход в 'Анализ обращения' (ID: {transition_id})")
                    jira.transition_issue(issue, transition_id)
                    
                else:
                    # Прямой переход в "Анализ обращения"
                    print(f"Статус '{current_status}': выполняем прямой переход в 'Анализ обращения'")
                    transition_id = "81"
                    jira.transition_issue(issue, transition_id)
                
                # Обновляем UI после всех переходов
                new_keyboard = create_task_keyboard(issue_key, True)
                await query.message.edit_reply_markup(reply_markup=new_keyboard)
                await query.answer("Статус задачи изменен на 'Анализ обращения'")
                print(f"Задача {issue_key} успешно переведена в статус 'Анализ обращения'")
                
            except Exception as e:
                print(f"Ошибка при изменении статуса: {e}")
                await query.answer(f"Ошибка при изменении статуса: {str(e)}")

        # Остальные обработчики (assign, details, take, at, comment, back)
        elif action == 'assign':
            print("Создаем клавиатуру для выбора сотрудника")
            try:
                keyboard = create_staff_keyboard(issue_key)
                await query.message.edit_reply_markup(reply_markup=keyboard)
                await query.answer("Выберите сотрудника")
                print("Клавиатура для выбора сотрудника создана успешно")
            except Exception as e:
                print(f"Ошибка при создании клавиатуры назначения: {e}")
                await query.answer(f"Ошибка: {str(e)}")

        # Добавляем обработку details
        elif action == 'details':
            print(f"Получение деталей для задачи {issue_key}")
            try:
                issue = jira.issue(issue_key)
                details = f"""
<b>Подробности задачи {issue_key}</b>

Статус: {issue.fields.status.name}
Приоритет: {issue.fields.priority.name}
Создана: {issue.fields.created[:10]}
Автор: {issue.fields.reporter.displayName}
"""
                await query.message.reply_text(
                    text=details,
                    parse_mode='HTML'
                )
                await query.answer()
                print(f"Детали задачи {issue_key} отправлены успешно")
            except Exception as e:
                print(f"Ошибка при получении деталей задачи: {e}")
                await query.answer(f"Ошибка: {str(e)}")

        # Добавляем обработку take
        elif action == 'take':
            print(f"Обработка взятия в работу задачи {issue_key}")
            try:
                current_status = task_status.get(issue_key, False)
                task_status[issue_key] = not current_status

                if not current_status:
                    keyboard = create_take_action_keyboard(issue_key)
                    await query.message.edit_reply_markup(reply_markup=keyboard)
                    await query.answer("Задача взята в работу")
                    print(f"Задача {issue_key} взята в работу")
                else:
                    keyboard = create_task_keyboard(issue_key, False)
                    await query.message.edit_reply_markup(reply_markup=keyboard)
                    await query.answer("Задача снята с работы")
                    print(f"Задача {issue_key} снята с работы")
            except Exception as e:
                print(f"Ошибка при обработке взятия задачи: {e}")
                await query.answer(f"Ошибка: {str(e)}")

        # Добавляем обработку at (назначение исполнителя)
        elif action == 'at':
            try:
                issue_key = data[1]
                staff_idx = int(data[2])
                
                if 0 <= staff_idx < len(SUPPORT_STAFF):
                    staff = SUPPORT_STAFF[staff_idx]
                    user_login = staff['jira_login']

                    if not user_login:
                        await query.answer("У сотрудника не указан логин в Jira")
                        return

                    issue = jira.issue(issue_key)
                    jira.assign_issue(issue, user_login)

                    # Возвращаемся к основному меню задачи
                    keyboard = create_task_keyboard(issue_key, task_status.get(issue_key, False))
                    await query.message.edit_reply_markup(reply_markup=keyboard)
                    await query.answer(f"Задача назначена на {staff['name']}")
                    print(f"Задача {issue_key} успешно назначена на {staff['name']}")
                else:
                    await query.answer("Сотрудник не найден")
            except Exception as e:
                print(f"Ошибка при назначении задачи: {e}")
                await query.answer(f"Ошибка при назначении задачи: {str(e)}")

        # Добавляем обработку comment
        elif action == 'comment':
            print("Попытка комментирования")
            await query.answer("Функция комментирования в разработке")

        # Добавляем обработку back
        elif action == 'back':
            print(f"Возврат к основному меню для задачи {issue_key}")
            try:
                keyboard = create_task_keyboard(issue_key, task_status.get(issue_key, False))
                await query.message.edit_reply_markup(reply_markup=keyboard)
                await query.answer("Вернулись к основному меню")
            except Exception as e:
                print(f"Ошибка при возврате к меню: {e}")
                await query.answer(f"Ошибка: {str(e)}")

        else:
            print(f"Неизвестное действие: {action}")
            await query.answer("Неизвестное действие")

    except Exception as e:
        print(f"Критическая ошибка в обработчике кнопок: {e}")
        await query.answer(f"Произошла ошибка: {str(e)}")

async def show_recent_tasks(query, context):
    """Показывает последние 10 задач"""
    try:
        # JQL запрос для последних задач
        jql = 'project = "Поддержка Informatics" ORDER BY created DESC'
        issues = jira.search_issues(jql, maxResults=10)

        if not issues:
            await query.message.edit_text(
                "🔍 Задач не найдено",
                reply_markup=create_main_menu_keyboard()
            )
            return

        # Формируем сообщение
        message = "📥 *Последние задачи:*\n\n"
        
        for idx, issue in enumerate(issues, 1):
            priority = getattr(issue.fields, 'priority', None)
            priority_text = priority.name if priority else "Не указан"
            
            # Эмодзи для приоритета
            priority_emoji = {
                "Бомбит": "💣",
                "Срочный": "🔴",
                "Высокий": "🟠",
                "Нормальный": "🟡",
                "Низкий": "⚪"
            }.get(priority_text, "⚪")

            # Получаем статус
            status = issue.fields.status.name

            # Формируем строку для задачи
            message += (
                f"{idx}. {priority_emoji} [{issue.key}]({JIRA_SERVER}/browse/{issue.key})\n"
                f"   *{issue.fields.summary[:100]}*\n"
                f"   Статус: {status}\n"
                f"   Создана: {issue.fields.created[:10]}\n\n"
            )

        # Добавляем подвал сообщения
        message += "\n_Показаны последние 10 задач_"

        # Добавляем кнопку возврата в меню
        keyboard = [
            [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="menu:back")]
        ]

        await query.message.edit_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print(f"Ошибка при получении последних задач: {e}")
        await query.message.edit_text(
            "❌ Ошибка при получении задач",
            reply_markup=create_main_menu_keyboard()
        )

if __name__ == "__main__":
    # Запуск основного цикла
    asyncio.run(main())
    