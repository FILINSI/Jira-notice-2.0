## 📝 Description
A feature-rich Telegram bot for JIRA ticket management and helpdesk coordination. The bot provides instant notifications of new tickets, interactive task management and duty schedule tracking.

## 🚀 Main features
- Instant notifications of new JIRA tickets
- Interactive task management (take/assign/comment)
- Duty schedule management (2/2 and 5/2 shifts)
- Service status monitoring
- Statistics and reporting on tasks
- Support for multiple users with different roles
- Customizable notification parameters

## 🛠️ Technical Stack
- Python 3.8+
- python-telegram-bot
- JIRA API
- asyncio for asynchronous operations
- requests for service monitoring

## 🔧 Customization
Required environment variables:
- `JIRA_SERVER`: JIRA server URL
- `JIRA_USER`: JIRA user name
- `JIRA_PASSWORD`: JIRA password
- `TELEGRAM_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Comma separated list of chat IDs

## 📋 Commands
- `/start` - Start the bot and display the menu
- `/tasks` - Show active tasks
- `/urgent` - Show urgent and overdue tasks
- `/search <text>` - Search by tasks
- `/status` - Check system status
- `/services` - Check availability of services
- `/help` - Show Help

## 🔄 Workflow
1. the bot monitors new tickets in JIRA
2. sends notifications to the specified Telegram chats
3. Support team manages tickets via interactive buttons
4. keeps track of the duty schedule and assigns responsible persons
5. Monitors service status and sends alerts

## 👥 Functions for the support team
- Taking tasks to work
- Assigning tasks to employees
- Adding comments
- View task details
- Check duty schedule
- Monitoring the status of services

## 🏗️ Project Structure
- Basic bot logic
- Integration with JIRA
- Duty schedule management
- Service monitoring
- Statistics collection
- Interactive menu system

## 📊 Monitoring
- Checking service availability
- Tracking bot uptime
- Tracking and reporting errors
- Usage statistics

## 🔐 Security
- Secure authentication in JIRA
- Secure configuration
- Session encryption will be added later

## 💡 Requirements
- Python 3.8 or higher
- Access to JIRA API
- Telegram Bot API token
- Access to monitored services

## ⚙️ Install and run
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`.
3. set environment variables
4. Run the bot: `python JiraBot.py`.

## 📌 Note
The bot is designed to optimize helpdesk performance and improve communication between employees. If you have any problems or suggestions for improvement, create an issue in the repository.

The script will authenticate to Jira and start monitoring new tasks. When a new task is detected, a notification will be sent to the specified Telegram chat.

## Notes

- Make sure your Jira credentials have the necessary permissions to access the right Jira projects and tasks.
- Make sure your Telegram bot is created and the token is configured correctly.
- The script uses asynchronous operations to handle authentication in Jira and sending messages to Telegram, making it efficient for continuous use.

Made by FILINSI

_____________________________________________________

## Использование

> **Примечание**: Чтобы скрипт работал непрерывно в фоне, можно использовать мультиплексор терминала, такой как [GNU Screen](https://wiki.archlinux.org/title/GNU_Screen). Это позволит вам держать скрипт запущенным, даже если вы отключитесь от сессии терминала.

# Telegram Бот для JIRA Support

## 📝 Описание
Многофункциональный Telegram бот для управления тикетами JIRA и координации работы службы поддержки. Бот обеспечивает мгновенные уведомления о новых тикетах, интерактивное управление задачами и отслеживание графика дежурств.

## 🚀 Основные возможности
- Мгновенные уведомления о новых тикетах JIRA
- Интерактивное управление задачами (взять/назначить/комментировать)
- Управление графиком дежурств (смены 2/2 и 5/2)
- Мониторинг состояния сервисов
- Статистика и отчетность по задачам
- Поддержка нескольких пользователей с разными ролями
- Настраиваемые параметры уведомлений

## 🛠️ Технический стек
- Python 3.8+
- python-telegram-bot
- JIRA API
- asyncio для асинхронных операций
- requests для мониторинга сервисов

## 🔧 Настройка
Необходимые переменные окружения:
- `JIRA_SERVER`: URL сервера JIRA
- `JIRA_USER`: Имя пользователя JIRA
- `JIRA_PASSWORD`: Пароль JIRA
- `TELEGRAM_TOKEN`: Токен Telegram бота
- `TELEGRAM_CHAT_ID`: Список ID чатов через запятую

## 📋 Команды
- `/start` - Запуск бота и вывод меню
- `/tasks` - Показать активные задачи
- `/urgent` - Показать срочные и просроченные задачи
- `/search <текст>` - Поиск по задачам
- `/status` - Проверка статуса системы
- `/services` - Проверка доступности сервисов
- `/help` - Показать справку

## 🔄 Рабочий процесс
1. Бот отслеживает новые тикеты в JIRA
2. Отправляет уведомления в указанные Telegram чаты
3. Команда поддержки управляет тикетами через интерактивные кнопки
4. Отслеживает график дежурств и назначает ответственных
5. Контролирует статус сервисов и отправляет оповещения

## 👥 Функции для команды поддержки
- Взятие задач в работу
- Назначение задач на сотрудников
- Добавление комментариев
- Просмотр деталей задачи
- Проверка графика дежурств
- Мониторинг состояния сервисов

## 🏗️ Структура проекта
- Основная логика бота
- Интеграция с JIRA
- Управление графиком дежурств
- Мониторинг сервисов
- Сбор статистики
- Система интерактивного меню

## 📊 Мониторинг
- Проверка доступности сервисов
- Отслеживание времени работы бота
- Отслеживание и отчетность по ошибкам
- Статистика использования

## 🔐 Безопасность
- Безопасная аутентификация в JIRA
- Защищенная конфигурация
- Позже бужет добавлено шифрование сессии

## 💡 Требования
- Python 3.8 или выше
- Доступ к JIRA API
- Telegram Bot API токен
- Доступ к мониторируемым сервисам

## ⚙️ Установка и запуск
1. Клонировать репозиторий
2. Установить зависимости: `pip install -r requirements.txt`
3. Настроить переменные окружения
4. Запустить бота: `python JiraBot.py`

## 📌 Примечание
Бот разработан для оптимизации работы службы технической поддержки и улучшения коммуникации между сотрудниками. При возникновении проблем или предложений по улучшению, создавайте issue в репозитории.

Скрипт выполнит аутентификацию в Jira и начнет мониторинг новых задач. Когда будет обнаружена новая задача, будет отправлено уведомление в указанный чат Telegram.

## Примечания

- Убедитесь, что ваши учетные данные Jira имеют необходимые разрешения для доступа к нужным проектам и задачам Jira.
- Убедитесь, что ваш Telegram-бот создан и токен настроен корректно.
- Скрипт использует асинхронные операции для обработки аутентификации в Jira и отправки сообщений в Telegram, что делает его эффективным для непрерывного использования.

Made by FILINSI

