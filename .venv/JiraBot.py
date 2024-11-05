import os
import requests
from jira import JIRA
from telegram import Bot
from telegram.error import TelegramError  # Изменено имя импорта для исключения
import asyncio

# Ввод параметров пользователем
JIRA_SERVER = input('Введите URL вашего сервера Jira: ')
JIRA_USER = input('Введите ваш логин или email для входа в Jira: ')
JIRA_PASSWORD = input('Введите ваш пароль для входа в Jira: ')
TELEGRAM_TOKEN = input('Введите токен вашего Telegram бота: ')
TELEGRAM_CHAT_ID = input('Введите ID чата или пользователя в Telegram: ')
jql_query = input('Введите ваш JQL запрос: ')

# Инициализация Jira клиента
jira_options = {'server': JIRA_SERVER}
jira = JIRA(options=jira_options, basic_auth=(JIRA_USER, JIRA_PASSWORD))

# Инициализация Telegram бота
bot = Bot(token=TELEGRAM_TOKEN)

async def send_telegram_message(message):
    print(f"Отправка сообщения: {message}")  # Отладочное сообщение
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("Сообщение отправлено успешно")  # Отладочное сообщение
    except TelegramError as e:
        print(f"Ошибка при отправке сообщения: {e}")  # Отладочное сообщение

async def authenticate_and_notify():
    while True:
        try:
            jira_options = {'server': JIRA_SERVER}
            jira = JIRA(options=jira_options, basic_auth=(JIRA_USER, JIRA_PASSWORD))
            # Проверка подключения к серверу
            server_info = jira.server_info()
            await send_telegram_message("Бот успешно аутентифицирован и готов работать. Анализирую очередь на наличие новых задач.")
            return jira
        except JIRAError as e:
            if "500" in str(e):
                print("Ошибка 500. Внутренняя ошибка сервера. Повторная попытка через 5 минут.")
                await send_telegram_message("Ошибка 500. Внутренняя ошибка сервера. Повторная попытка через 5 минут.")
            else:
                print(f"Ошибка аутентификации или подключения к серверу Jira: {e}")
                await send_telegram_message(f"Ошибка аутентификации или подключения к серверу Jira: {e}")
            await asyncio.sleep(300)  # Ждать 5 минут (300 секунд) перед повторной попыткой
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            await send_telegram_message(f"Неизвестная ошибка: {e}")
            await asyncio.sleep(300)  # Ждать 5 минут (300 секунд) перед повторной попыткой

# Хранение ID последних задач, чтобы избегать повторных уведомлений
last_seen_issue_id = None

async def check_new_issues(jira):
    global last_seen_issue_id
    print("Проверка новых задач...")  # Отладочное сообщение
    try:
        issues = jira.search_issues(jql_query, maxResults=1)
        print(f"Найдено задач: {len(issues)}")  # Отладочное сообщение
        if issues:
            latest_issue = issues[0]
            print(f"ID последней задачи: {latest_issue.id}")  # Отладочное сообщение
            if last_seen_issue_id is None:
                last_seen_issue_id = latest_issue.id
                print(f"Установлен initial last_seen_issue_id: {last_seen_issue_id}")  # Отладочное сообщение
                await send_telegram_message(f"Initial issue in Jira:\n\nSummary: {latest_issue.fields.summary}\nDescription: {latest_issue.fields.description}\nURL: {JIRA_SERVER}/browse/{latest_issue.key}")
            elif latest_issue.id != last_seen_issue_id:
                print(f"Найдена новая задача: {latest_issue.id}")  # Отладочное сообщение
                last_seen_issue_id = latest_issue.id
                await send_telegram_message(f"New issue in Jira:\n\nSummary: {latest_issue.fields.summary}\nDescription: {latest_issue.fields.description}\nURL: {JIRA_SERVER}/browse/{latest_issue.key}")
            else:
                print("Нет новых задач для уведомления.")  # Отладочное сообщение
        else:
            print("Задачи не найдены.")  # Отладочное сообщение
    except JIRAError as e:
        print(f"Ошибка при запросе задач из Jira: {e}")
        await send_telegram_message(f"Ошибка при запросе задач из Jira: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при проверке задач: {e}")
        await send_telegram_message(f"Неизвестная ошибка при проверке задач: {e}")

async def scheduler(jira):
    while True:
        try:
            await check_new_issues(jira)
        except Exception as e:
            print(f"Ошибка при проверке задач: {e}")
            await send_telegram_message(f"Ошибка при проверке задач: {e}")
        await asyncio.sleep(50)

async def main():
    while True:
        try:
            jira = await authenticate_and_notify()
            await scheduler(jira)
        except Exception as e:
            print(f"Произошла ошибка: {e}. Перезапуск через 10 секунд...")
            await send_telegram_message(f"Произошла ошибка: {e}. Перезапуск через 10 секунд...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())

#made by FILINSI