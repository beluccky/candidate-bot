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
        self.telegram_bot = TelegramBot(database=self.db)
        self.scheduler = BackgroundScheduler()
    
    async def check_candidates(self):
        """Проверить новых кандидатов и отправить напоминания"""
        logger.info("🔍 Проверка кандидатов в Google Sheets...")
        
        try:
            candidates = self.sheets_api.get_candidates()
            logger.info(f"Найдено {len(candidates)} кандидатов в таблице")
            
            # Собираем все уникальные имена рекрутеров для кэша
            recruiter_names = list(set([c['recruiter_id'] for c in candidates if c['recruiter_id']]))
            recruiter_names.sort()
            self.db.set_unique_recruiter_names(recruiter_names)
            logger.info(f"Уникальных рекрутеров в таблице: {', '.join(recruiter_names) if recruiter_names else 'нет'}")
            
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
                    logger.info(f"✅ Добавлен новый кандидат: {candidate['name']} (рекрутер: {candidate.get('recruiter_id', 'не указан')})")
            
            # Проверить напоминания
            await self.check_reminders()
        
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке кандидатов: {e}")
    
    async def check_reminders(self):
        """?????????, ???? ????? ????????? ???????????"""
        try:
            candidates = self.db.get_candidates_for_reminder()
            logger.info(f"???????? ??????????? ??? {len(candidates)} ??????????")

            for candidate_id, name, obj, start_date, recruiter_id in candidates:
                logger.info(f"?? ????????: {name}, ????: {start_date}, ????????: {recruiter_id}")

                if self._should_send_reminder(start_date):
                    logger.info(f"? ???? ????????? ???: {name}")
                    # ???????? chat_id ????????? ?? ?? ?? ??? ?????
                    chat_id = None
                    if recruiter_id:
                        chat_id = self.db.get_chat_id_by_recruiter_name(recruiter_id)
                        logger.info(f"?? Chat ID ??? {recruiter_id}: {chat_id}")

                    if chat_id:
                        logger.info(f"?? ????????? ??????????? {name} ? chat {chat_id}")
                        # ????????? ??????????? ??????????????????? ?????????
                        success = await self.telegram_bot.send_reminder(name, obj, chat_id)

                        if success:
                            self.db.mark_reminder_sent(candidate_id)
                            logger.info(f"? ??????????? ??????????: {name}")
                        else:
                            logger.error(f"? ?????? ????????: {name}")
                    else:
                        logger.warning(f"?? Chat ID ?? ?????? ??? ????????? {recruiter_id}")
                else:
                    logger.info(f"?? ???? ?? ????????? ??? ?????? ???: {name}")

        except Exception as e:
            logger.error(f"? ?????? ? check_reminders: {e}")

    def _should_send_reminder(self, start_date_str):



        """Проверить, нужно ли отправить напоминание (за день до выхода)"""
        if not start_date_str or not str(start_date_str).strip():
            return False
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
