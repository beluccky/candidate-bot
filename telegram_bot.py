import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_RECRUITER_CHAT_ID
import logging

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, database=None):
        self.bot = Bot(token=token)
        self.default_chat_id = TELEGRAM_RECRUITER_CHAT_ID
        self.database = database
        self.app = None
    
    async def setup_handlers(self, app):
        """Настроить обработчики команд"""
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CallbackQueryHandler(self.recruiter_selection_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start - выбор рекрутера"""
        if not self.database:
            await update.message.reply_text("❌ База данных недоступна")
            return
        
        chat_id = str(update.effective_chat.id)
        
        # Проверяем, уже ли зарегистрирован рекрутер
        existing_recruiter = self.database.get_recruiter_by_chat_id(chat_id)
        if existing_recruiter:
            await update.message.reply_text(
                f"✅ Вы уже зарегистрированы как: <b>{existing_recruiter}</b>\n\n"
                f"Будете получать напоминания о кандидатах, назначенных вам.",
                parse_mode='HTML'
            )
            return
        
        # Получаем всех рекрутеров из таблицы (все уникальные имена)
        recruiters = self.database.get_unique_recruiter_names()
        
        if not recruiters:
            await update.message.reply_text("❌ Нет рекрутеров в таблице")
            return
        
        # Создаем кнопки для выбора
        keyboard = []
        for recruiter_name in recruiters:
            keyboard.append([
                InlineKeyboardButton(recruiter_name, callback_data=f"recruiter_{recruiter_name}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Выберите вашу фамилию и имя из списка:",
            reply_markup=reply_markup
        )
    
    async def recruiter_selection_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатия кнопки с выбором рекрутера"""
        query = update.callback_query
        await query.answer()
        
        if not self.database:
            await query.edit_message_text("❌ База данных недоступна")
            return
        
        # Извлекаем имя рекрутера из callback_data
        if not query.data.startswith("recruiter_"):
            return
        
        recruiter_name = query.data.replace("recruiter_", "")
        chat_id = str(query.effective_chat.id)
        
        # Сохраняем рекрутера в БД
        success = self.database.add_recruiter(chat_id, recruiter_name)
        
        if success:
            await query.edit_message_text(
                f"✅ <b>Вы зарегистрированы!</b>\n\n"
                f"Имя: <b>{recruiter_name}</b>\n\n"
                f"Вы будете получать напоминания о кандидатах, назначенных вам.",
                parse_mode='HTML'
            )
            logger.info(f"✅ Рекрутер {recruiter_name} зарегистрирован с chat_id {chat_id}")
        else:
            await query.edit_message_text("❌ Ошибка при регистрации. Попробуйте позже.")
    
    async def send_reminder(self, candidate_name, object_name, chat_id=None):
        """Отправить напоминание рекрутеру"""
        if not chat_id:
            chat_id = self.default_chat_id
        
        message = (
            f"⚠️ <b>Напоминание о выходе кандидата</b>\n\n"
            f"<b>Кандидат:</b> {candidate_name}\n"
            f"<b>Объект:</b> {object_name}\n\n"
            f"🔔 Кандидат выходит на работу <b>ЗАВТРА</b>!\n"
            f"Пожалуйста, позвоните и уточните факт выхода."
        )
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке сообщения: {e}")
            return False
    
    async def send_message(self, chat_id, text):
        """Отправить произвольное сообщение"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке сообщения: {e}")
            return False
    
    async def test_connection(self):
        """Проверить подключение к боту"""
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Бот подключён: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            return False
    
    async def start(self, database):
        """Запустить Application бота с обработчиками"""
        self.database = database
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        await self.setup_handlers(self.app)
        
        # Запускаем polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        return self.app
    
    async def stop(self):
        """Остановить бота"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
