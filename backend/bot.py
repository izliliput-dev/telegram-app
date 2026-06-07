"""
Telegram Bot для SDA Web App
"""
import asyncio
import json
import logging
import os
from telegram import Update, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    FileHandler,
    MessageHandler
)
from telegram.constants import ParseMode

from config import settings

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для диалога добавления аккаунта
(
    ADD_STEP_WAITING_FILE,
    ADD_STEP_WAITING_LOGIN,
    ADD_STEP_WAITING_PASSWORD,
    ADD_STEP_CONFIRM
) = range(4)

# Хранилище данных для временного хранения состояния
temp_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    webapp_url = settings.WEB_APP_URL
    
    await update.message.reply_text(
        "🔐 **SDA Telegram App**\n"
        "Управляйте своими аккаунтами Steam прямо в Telegram!\n\n"
        "**Возможности:**\n"
        "• Генерация 2FA кодов Steam Guard\n"
        "• Подтверждение трейдов и обменов\n"
        "• Управление несколькими аккаунтами\n"
        "• Авто-принятие подарочных трейдов\n\n"
        "**Команды:**\n"
        "/start - Открыть приложение\n"
        "/add - Добавить новый аккаунт\n"
        "/log pass - Восстановить сохраненные логины/пароли\n"
        "/help - Справка\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup={
            "inline_keyboard": [[
                {
                    "text": "🚀 Открыть SDA",
                    "web_app": {"url": webapp_url}
                }
            ]]
        }
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    help_text = """
🛡️ **SDA Telegram App - Справка**

**Команды:**
/start - Открыть приложение
/add - Добавить новый аккаунт Steam
/log pass - Восстановить сохраненные логины и пароли
/help - Эта справка

**Возможности:**
🔑 **2FA коды** - Генерация кодов Steam Guard каждые 30 секунд
📦 **Трейды** - Просмотр и управление торговыми предложениями
✅ **Подтверждения** - Принятие/отклонение подтверждений Steam
🎁 **Авто-принятие** - Автоматическое принятие подарочных трейдов

**Безопасность:**
• Все данные шифруются (AES-256)
• Пароли хранятся в зашифрованном виде
• Используется безопасное соединение

**Как добавить аккаунт:**
1. Отправьте /add
2. Отправьте файл .maFile как документ
3. Введите логин Steam
4. Введите пароль Steam
5. Подтвердите добавление
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления аккаунта."""
    telegram_id = str(update.effective_user.id)
    
    await update.message.reply_text(
        "📁 **Добавление аккаунта Steam**\n\n"
        "Отправьте файл `.maFile` из Steam Desktop Authenticator.\n\n"
        "⚠️ **Важно:** Файл нужно отправлять как **Document** (документ), а не как фото!\n\n"
        "Чтобы отправить как документ:\n"
        "1. Нажмите на скрепку (📎)\n"
        "2. Выберите файл\n"
        "3. Отправьте не как фото, а как файл",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADD_STEP_WAITING_FILE


async def handle_mafile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик maFile файла."""
    telegram_id = str(update.effective_user.id)
    
    if not update.message.document:
        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте файл как документ, а не как фото!"
        )
        return ADD_STEP_WAITING_FILE
    
    doc = update.message.document
    
    # Если файл уже был обработан
    if telegram_id in temp_data and temp_data[telegram_id].get('mafile_data'):
        await update.message.reply_text(
            "⚠️ Вы уже загрузили файл. Подождите завершения текущего процесса или отправьте /cancel"
        )
        return ADD_STEP_WAITING_FILE
    
    try:
        # Скачиваем файл
        file = await doc.get_file()
        downloaded = await file.download_to_drive()
        
        # Читаем JSON
        with open(downloaded, 'r', encoding='utf-8') as f:
            mafile_data = json.load(f)
        
        # Проверяем что это правильный формат
        if 'shared_secret' not in mafile_data:
            raise ValueError("Это не файл .maFile Steam")
        
        # Сохраняем данные
        temp_data[telegram_id] = {'mafile_data': mafile_data}
        
        await update.message.reply_text(
            "✅ Файл принят!\n\n"
            "Теперь отправьте ** логин Steam** (текстом):",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ADD_STEP_WAITING_LOGIN
        
    except Exception as e:
        logger.error(f"Ошибка обработки maFile: {e}")
        await update.message.reply_text(
            f"⚠️ Ошибка обработки файла: {str(e)}\n\n"
            "Попробуйте отправить файл снова или используйте /cancel"
        )
        return ADD_STEP_WAITING_FILE


async def handle_steam_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик логина Steam."""
    telegram_id = str(update.effective_user.id)
    
    if telegram_id not in temp_data:
        await update.message.reply_text(
            "⚠️ Сначала загрузите файл .maFile. Отправьте /add"
        )
        return ConversationHandler.END
    
    steam_login = update.message.text.strip()
    
    if not steam_login:
        await update.message.reply_text(
            "⚠️ Логин не может быть пустым. Отправьте логин Steam:"
        )
        return ADD_STEP_WAITING_LOGIN
    
    temp_data[telegram_id]['steam_login'] = steam_login
    
    await update.message.reply_text(
        "✅ Логин принят!\n\n"
        "Теперь отправьте **пароль Steam** (текстом):",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADD_STEP_WAITING_PASSWORD


async def handle_steam_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пароля Steam."""
    telegram_id = str(update.effective_user.id)
    
    if telegram_id not in temp_data:
        await update.message.reply_text(
            "⚠️ Нет сохраненных данных. Отправьте /add чтобы начать"
        )
        return ConversationHandler.END
    
    steam_password = update.message.text.strip()
    
    if not steam_password:
        await update.message.reply_text(
            "⚠️ Пароль не может быть пустым. Отправьте пароль Steam:"
        )
        return ADD_STEP_WAITING_PASSWORD
    
    temp_data[telegram_id]['steam_password'] = steam_password
    
    # Формируем подтверждение
    mafile_data = temp_data[telegram_id]['mafile_data']
    name = mafile_data.get('account_name', 'Без названия')
    steam_name = temp_data[telegram_id]['steam_login']
    
    message = (
        f"📋 **Подтверждение добавления аккаунта**\n\n"
        f"🏷️ Имя в приложении: <b>{name}</b>\n"
        f"👤 Логин Steam: <code>{steam_name}</code>\n"
        f"🔐 Пароль: <code>{steam_password[:4]}****</code>\n\n"
        "<i>Все данные будут зашифрованы!</i>\n\n"
        "<b>Отправить аккаунт в приложение?</b>\n\n"
        "<code>/add confirm</code> - да\n"
        "<code>/cancel</code> - отмена"
    )
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML
    )
    
    return ADD_STEP_CONFIRM


async def add_account_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение добавления аккаунта."""
    telegram_id = str(update.effective_user.id)
    
    if telegram_id not in temp_data:
        await update.message.reply_text("⚠️ Нет сохраненных данных.")
        return ConversationHandler.END
    
    # Отправляем подтверждение
    await update.message.reply_text(
        "⏳ Добавление аккаунта...\n\n"
        "Пожалуйста, подождите."
    )
    
    try:
        import httpx
        mafile_data = temp_data[telegram_id]['mafile_data']
        steam_login = temp_data[telegram_id]['steam_login']
        steam_password = temp_data[telegram_id]['steam_password']
        name = mafile_data.get('account_name', 'Без названия')
        
        # Отправляем запрос на API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.WEB_APP_URL.replace(':3000', ':8000')}/api/accounts/log",
                json={
                    "name": name,
                    "steam_login": steam_login,
                    "steam_password": steam_password
                },
                headers={
                    "X-Telegram-Init-Data": str(telegram_id),
                    "Content-Type": "application/json"
                }
            )
        
        if response.status_code == 200:
            result = response.json()
            await update.message.reply_text(
                f"✅ Аккаунт успешно добавлен!\n\n"
                f"Имя: <b>{name}</b>\n"
                f"ID аккаунта: <code>{result['account_id']}</code>\n\n"
                "<i>Данные зашифрованы и сохранены.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            await update.message.reply_text(
                f"⚠️ Ошибка добавления аккаунта: {response.status_code}\n\n"
                "Попробуйте отправить /add снова или используйте Web App"
            )
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении аккаунта: {e}")
        await update.message.reply_text(
            f"⚠️ Произошла ошибка: {str(e)}\n\n"
            "Попробуйте отправить /add снова или используйте Web App"
        )
    
    # Очищаем временные данные
    if telegram_id in temp_data:
        del temp_data[telegram_id]
    
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего процесса."""
    telegram_id = str(update.effective_user.id)
    
    if telegram_id in temp_data:
        del temp_data[telegram_id]
    
    await update.message.reply_text(
        "⚠️ Процесс отменён. Отправьте /add для начала заново."
    )
    
    return ConversationHandler.END


async def log_pass_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /log pass."""
    telegram_id = str(update.effective_user.id)
    
    try:
        import httpx
        
        # Получаем сохраненные логины/пароли
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEB_APP_URL.replace(':3000', ':8000')}/api/accounts/me/creds",
                headers={
                    "X-Telegram-Init-Data": str(telegram_id)
                }
            )
        
        if response.status_code == 200:
            accounts = response.json()
            
            if not accounts:
                await update.message.reply_text(
                    "📋 У вас нет сохраненных аккаунтов.\n\n"
                    "Добавьте аккаунт через Web App или командой /add",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            message = "📋 **Ваши сохраненные аккаунты:**\n\n"
            
            for acc in accounts:
                message += f"• **{acc['name']}**\n"
                if acc['steam_login']:
                    message += f"  👤 Логин: <code>{acc['steam_login']}</code>\n"
                if acc['steam_password']:
                    message += f"  🔐 Пароль: <code>{acc['steam_password']}</code>\n"
                message += "\n"
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.HTML
            )
        
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            await update.message.reply_text(
                "⚠️ Ошибка получения данных. Проверьте настройки приложения."
            )
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        await update.message.reply_text(
            f"⚠️ Произошла ошибка: {str(e)}"
        )


def create_bot():
    """Создаёт и настраивает бота."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не настроен!")
        return None
    
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_account_start))
    application.add_handler(CommandHandler("cancel", cancel_conversation))
    application.add_handler(CommandHandler("log", log_pass_handler, patterns=['pass']))
    
    # Обработчик файла maFile
    application.add_handler(
        FileHandler(
            filters.Document.ANY & filters.Document.Filename(r'.*\.maFile$', mode="ignore"),
            handle_mafile
        )
    )
    
    # Обработчики для диалога добавления аккаунта
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_account_start)],
        states={
            ADD_STEP_WAITING_FILE: [
                FileHandler(
                    filters.DOCUMENT & filters.Document.Filename(r'.*\.maFile$', mode="ignore"),
                    handle_mafile
                )
            ],
            ADD_STEP_WAITING_LOGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_steam_login)
            ],
            ADD_STEP_WAITING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_steam_password)
            ],
            ADD_STEP_CONFIRM: [
                MessageHandler(filters.TEXT & filters.Regex(r'/add confirm$'), add_account_confirm),
                CommandHandler("cancel", cancel_conversation)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    return application


async def main():
    """Запускает бота."""
    bot = create_bot()
    
    if bot:
        logger.info("Бот запущен...")
        await bot.initialize()
        await bot.start()
        await bot.updater.start_polling()
        
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
