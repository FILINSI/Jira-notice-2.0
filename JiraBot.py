from JiraBot.config.settings import TELEGRAM_TOKEN
from JiraBot.handlers.callback_handlers import show_status_from_callback, show_help_from_callback
from JiraBot.handlers.command_handlers import show_active_tasks, show_urgent_tasks, check_status, \
    handle_button_click
from JiraBot.main import main
from JiraBot.models.bot_stats import bot_stats
from JiraBot.services.monitoring import check_edu_services, check_services_command
from JiraBot.utils.keyboards import create_main_menu_keyboard
from JiraBot.utils.scheduler import scheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import asyncio


# Добавьте новые функции для обработки команд

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


if __name__ == "__main__":
    # Запуск основного цикла
    asyncio.run(main())