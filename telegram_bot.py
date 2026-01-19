import asyncio
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_RECRUITER_CHAT_ID

class TelegramBot:
    def __init__(self, token=TELEGRAM_BOT_TOKEN):
        self.bot = Bot(token=token)
        self.default_chat_id = TELEGRAM_RECRUITER_CHAT_ID
    
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
            print(f"Ошибка при отправке сообщения: {e}")
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
            print(f"Ошибка при отправке сообщения: {e}")
            return False
    
    async def test_connection(self):
        """Проверить подключение к боту"""
        try:
            bot_info = await self.bot.get_me()
            print(f"✅ Бот подключён: @{bot_info.username}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
