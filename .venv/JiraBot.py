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

