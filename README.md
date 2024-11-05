# Jira Notice Bot for Telegram

This repository contains a Python script that monitors Jira issues and sends notifications to a Telegram chat. The script is designed to periodically check for new issues in Jira and send a message using a Telegram bot when a new issue is detected.

## Features

- **Jira Authentication**: Authenticate with Jira using credentials provided by the user.
- **Telegram Notifications**: Send notifications about new Jira issues to a specified Telegram chat.
- **User Input**: Easily configurable by prompting the user for Jira and Telegram credentials at runtime.
- **Periodic Checks**: Continuously checks for new issues and notifies via Telegram if any changes are detected.

## Requirements

To run the script, you need the following Python libraries:

- `requests`
- `jira`
- `python-telegram-bot`

You can install these dependencies using pip:

```sh
pip install requests jira python-telegram-bot
```
or
```sh
pip install -r requirements.txt
```

## Usage

> **Note**: To keep the script running continuously in the background, you may consider using a terminal multiplexer like [GNU Screen](https://wiki.archlinux.org/title/GNU_Screen). This will allow the script to run even if you disconnect from your terminal session.

1. Clone the repository.
2. Install the required libraries as mentioned above.
3. Run the script:

```sh
python JiraBot.py
```

4. You will be prompted to enter the following information:
   - Jira server URL
   - Jira username or email
   - Jira password
   - Telegram bot token
   - Telegram chat ID
   - JQL query for filtering Jira issues

The script will authenticate with Jira and start monitoring for new issues. When a new issue is detected, it will send a notification to the specified Telegram chat.

## Notes

- Ensure that your Jira credentials have the necessary permissions to access the desired Jira projects and issues.
- Make sure your Telegram bot has been created and the bot token is correctly configured.
- The script uses asynchronous operations to handle both Jira authentication and Telegram messaging, making it efficient for continuous use.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

# Jira Notice Bot для Telegram

Этот репозиторий содержит скрипт на Python, который мониторит задачи в Jira и отправляет уведомления в чат Telegram. Скрипт предназначен для периодической проверки наличия новых задач в Jira и отправки сообщения с использованием Telegram-бота, когда обнаружена новая задача.

## Основные возможности

- **Аутентификация в Jira**: Аутентификация в Jira с использованием учетных данных, введенных пользователем.
- **Уведомления в Telegram**: Отправка уведомлений о новых задачах в Jira в указанный чат Telegram.
- **Ввод данных пользователем**: Простая настройка путем ввода учетных данных для Jira и Telegram во время выполнения.
- **Периодические проверки**: Постоянная проверка на наличие новых задач и отправка уведомлений через Telegram при обнаружении изменений.

## Требования

Для запуска скрипта вам потребуются следующие библиотеки Python:

- `requests`
- `jira`
- `python-telegram-bot`

Вы можете установить эти зависимости с помощью pip:

```sh
pip install requests jira python-telegram-bot
```
или
```sh
pip install -r requirements.txt
```

## Использование

> **Примечание**: Чтобы скрипт работал непрерывно в фоне, можно использовать мультиплексор терминала, такой как [GNU Screen](https://wiki.archlinux.org/title/GNU_Screen). Это позволит вам держать скрипт запущенным, даже если вы отключитесь от сессии терминала.

1. Клонируйте репозиторий.
2. Установите необходимые библиотеки, как указано выше.
3. Запустите скрипт:

```sh
python JiraBot.py
```

4. Вам будет предложено ввести следующую информацию:
   - URL сервера Jira
   - Имя пользователя или email для Jira
   - Пароль для Jira
   - Токен вашего Telegram-бота
   - ID чата или пользователя в Telegram
   - JQL-запрос для фильтрации задач Jira

Скрипт выполнит аутентификацию в Jira и начнет мониторинг новых задач. Когда будет обнаружена новая задача, будет отправлено уведомление в указанный чат Telegram.

## Примечания

- Убедитесь, что ваши учетные данные Jira имеют необходимые разрешения для доступа к нужным проектам и задачам Jira.
- Убедитесь, что ваш Telegram-бот создан и токен настроен корректно.
- Скрипт использует асинхронные операции для обработки аутентификации в Jira и отправки сообщений в Telegram, что делает его эффективным для непрерывного использования.

## Лицензия

Этот проект лицензирован на условиях лицензии MIT. См. файл LICENSE для деталей.



