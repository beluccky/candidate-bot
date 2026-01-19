import os
from dotenv import load_dotenv

load_dotenv()

# Google Sheets
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID', '1jXV_w8PZ3cBAvJHYF5YgIph__O_5qXAxZW_rYOwvvvc')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_RECRUITER_CHAT_ID = os.getenv('TELEGRAM_RECRUITER_CHAT_ID')

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'candidates.db')

# Schedule
CHECK_INTERVAL_HOURS = int(os.getenv('CHECK_INTERVAL_HOURS', 1))

# Google Sheets columns (0-indexed)
COLUMNS = {
    'name': 0,           # Колонка A - ФИО кандидата
    'object': 11,        # Колонка L - Объект/название должности
    'recruiter': 12,     # Колонка M - Рекрутер
    'start_date': 16     # Колонка Q - Дата выхода на работу (дд.мм.гггг, дд.гг)
}
