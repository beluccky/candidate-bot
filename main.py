import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from google_sheets import GoogleSheetsAPI
from telegram_bot import TelegramBot
from database import Database
from config import CHECK_INTERVAL_HOURS
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CandidateBot:
    def __init__(self):
        self.db = Database()
        self.sheets_api = GoogleSheetsAPI()
        self.telegram_bot = TelegramBot()
        self.scheduler = BackgroundScheduler()
    
    async def check_candidates(self):
        """Проверить новых кандидатов и отправить напоминания"""
        logger.info("🔍 Проверка кандидатов в Google Sheets...")
        
        try:
            candidates = self.sheets_api.get_candidates()
            logger.info(f"Найдено {len(candidates)} кандидатов в таблице")
            
            # Добавить новых кандидатов
            for candidate in candidates:
                if not self.db.candidate_exists(candidate['id']):
                    self.db.add_candidate(
                        candidate_id=candidate['id'],
                        name=candidate['name'],
                        obj=candidate['object'],
                        start_date=candidate['start_date'],
                        recruiter_id=candidate.get('recruiter_id')
                    )
                    logger.info(f"✅ Добавлен новый кандидат: {candidate['name']}")
            
            # Проверить напоминания
            await self.check_reminders()
        
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке кандидатов: {e}")
    
    async def check_reminders(self):
        """Проверить, кому нужно отправить напоминание"""
        try:
            candidates = self.db.get_candidates_for_reminder()
            logger.info(f"Проверка напоминаний для {len(candidates)} кандидатов")
            
            for candidate_id, name, obj, start_date, recruiter_id in candidates:
                if self._should_send_reminder(start_date):
                    # Отправить напоминание
                    chat_id = recruiter_id if recruiter_id else None
                    success = await self.telegram_bot.send_reminder(name, obj, chat_id)
                    
                    if success:
                        self.db.mark_reminder_sent(candidate_id)
                        logger.info(f"📱 Напоминание отправлено для {name}")
                    else:
                        logger.error(f"❌ Не удалось отправить напоминание для {name}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке напоминаний: {e}")
    
    def _should_send_reminder(self, start_date_str):
        """Проверить, нужно ли отправить напоминание (за день до выхода)"""
        try:
            # Поддерживаемые форматы дат
            formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']
            start_date = None
            
            for fmt in formats:
                try:
                    start_date = datetime.strptime(start_date_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not start_date:
                logger.warning(f"⚠️ Невозможно распарсить дату: {start_date_str}")
                return False
            
            # Проверить, завтра ли выход
            tomorrow = (datetime.now() + timedelta(days=1)).date()
            return start_date == tomorrow
        
        except Exception as e:
            logger.error(f"Ошибка при обработке даты {start_date_str}: {e}")
            return False
    
    def _run_async_job(self):
        """Обёртка для запуска async функции из scheduler"""
        asyncio.run(self.check_candidates())
    
    def start(self):
        """Запустить бота"""
        logger.info("🚀 Запуск Candidate Bot...")
        
        # Проверить подключение
        asyncio.run(self.telegram_bot.test_connection())
        
        # Добавить задачу в scheduler
        self.scheduler.add_job(
            self._run_async_job,
            'interval',
            hours=CHECK_INTERVAL_HOURS,
            id='check_candidates',
            name='Проверка кандидатов'
        )
        
        # Запустить scheduler
        self.scheduler.start()
        logger.info(f"⏰ Бот запущен. Проверка каждые {CHECK_INTERVAL_HOURS} часа(ов)")
        
        try:
            # Первая проверка сразу
            asyncio.run(self.check_candidates())
            
            # Бот работает в фоне
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️  Бот остановлен")
            self.scheduler.shutdown()

if __name__ == '__main__':
    bot = CandidateBot()
    bot.start()
