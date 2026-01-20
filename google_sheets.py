from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_FILE, COLUMNS
import os
import json
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

class GoogleSheetsAPI:
    def __init__(self, spreadsheet_id=GOOGLE_SHEETS_ID):
        self.spreadsheet_id = spreadsheet_id
        self.service = self._get_service()
    
    def _get_service(self):
        """Получить доступ к Google Sheets API"""
        creds = None
        
        # Вариант 1: Service Account JSON из переменной окружения (для Railway/облако)
        creds_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if creds_json_str:
            try:
                creds_dict = json.loads(creds_json_str)
                creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                logger.info("✅ Использую Google Service Account из переменной окружения")
                return build('sheets', 'v4', credentials=creds)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при парсинге GOOGLE_CREDENTIALS_JSON: {e}")
        
        # Вариант 2: Проверить наличие сохранённых учётных данных OAuth2 (для локального тестирования)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(base_dir, GOOGLE_CREDENTIALS_FILE)
        if not os.path.exists(credentials_file):
            credentials_file = "/etc/secrets/credentials.json"
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(
                f"Файл {credentials_file} не найден. "
                f"Загрузите его из Google Cloud Console"
            )
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        return build('sheets', 'v4', credentials=creds)

        if os.path.exists('token.json'):
            creds = UserCredentials.from_authorized_user_file('token.json', SCOPES)
        
        # Вариант 3: Использовать файл учётных данных
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                credentials_file = os.path.join(base_dir, GOOGLE_CREDENTIALS_FILE)
                if not os.path.exists(credentials_file):
                    credentials_file = "/etc/secrets/credentials.json"
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"Файл {credentials_file} не найден. "
                        f"Загрузите его из Google Cloud Console"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Сохранить учётные данные для последующего использования
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return build('sheets', 'v4', credentials=creds)
    
    def _parse_date(self, date_str):
        """Парсить дату в форматах дд.мм.гггг и дд.гг"""
        if not date_str or not date_str.strip():
            return None
        
        date_str = date_str.strip()
        
        # Формат дд.мм.гггг (полный)
        match = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day)).strftime('%Y-%m-%d')
            except ValueError:
                logger.warning(f"⚠️ Невалидная дата: {date_str}")
                return None
        
        # Формат дд.гг (месяц.год, предполагаем текущий день)
        match = re.match(r'(\d{1,2})\.(\d{2})', date_str)
        if match:
            month, year = match.groups()
            # Предполагаем, что это означает 1-й день месяца в году 20гг или 19гг
            year_full = int(year)
            if year_full < 50:
                year_full += 2000
            else:
                year_full += 1900
            
            try:
                return datetime(year_full, int(month), 1).strftime('%Y-%m-%d')
            except ValueError:
                logger.warning(f"⚠️ Невалидная дата: {date_str}")
                return None
        
        # Стандартные форматы
        formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y']
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        logger.warning(f"⚠️ Невозможно распарсить дату: {date_str}")
        return None
    
    def get_all_sheets(self):
        """Получить список всех листов в таблице"""
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            sheets = sheet_metadata.get('sheets', [])
            return [sheet['properties']['title'] for sheet in sheets]
        except Exception as e:
            logger.error(f"Ошибка при получении списка листов: {e}")
            return []
    
    def get_candidates(self, sheet_names=None):
        """Получить список кандидатов из всех листов или из указанных"""
        candidates = []
        
        # Получить все листы, если не указаны конкретные
        if not sheet_names:
            sheet_names = self.get_all_sheets()
        
        if not sheet_names:
            logger.error("Листы не найдены в таблице")
            return []
        
        for sheet_name in sheet_names:
            logger.info(f"Чтение кандидатов с листа: {sheet_name}")
            candidates.extend(self._get_candidates_from_sheet(sheet_name))
        
        return candidates
    
    def _get_candidates_from_sheet(self, sheet_name):
        """Получить кандидатов с одного листа"""
        try:
            sheet = self.service.spreadsheets()
            # Получить максимальный диапазон для этого листа
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet_name}'!A2:Q"  # От A до Q (колонка Q = индекс 16)
            ).execute()
            
            values = result.get('values', [])
            candidates = []
            
            for idx, row in enumerate(values):
                # Проверить минимальные колонки (до Q = индекс 16)
                if len(row) < 17:
                    # Дополнить пустыми значениями до нужного размера
                    row = row + [''] * (17 - len(row))
                
                try:
                    name = row[COLUMNS['name']].strip() if len(row) > COLUMNS['name'] else ''
                    obj = row[COLUMNS['object']].strip() if len(row) > COLUMNS['object'] else ''
                    recruiter = row[COLUMNS['recruiter']].strip() if len(row) > COLUMNS['recruiter'] else None
                    date_str = row[COLUMNS['start_date']].strip() if len(row) > COLUMNS['start_date'] else ''
                    
                    # Пропустить пустые строки
                    if not name or not obj or not date_str:
                        continue
                    
                    # Парсить дату
                    parsed_date = self._parse_date(date_str)
                    if not parsed_date:
                        continue
                    
                    # Создать уникальный ID кандидата
                    candidate_id = f"{sheet_name}_{idx+2}"
                    
                    candidate = {
                        'id': candidate_id,
                        'name': name,
                        'object': obj,
                        'start_date': parsed_date,
                        'recruiter_id': recruiter if recruiter else None,
                        'sheet': sheet_name
                    }
                    candidates.append(candidate)
                    logger.info(f"  ✓ {name} | {obj} | {parsed_date}")
                
                except (IndexError, AttributeError, ValueError) as e:
                    logger.debug(f"Ошибка при обработке строки {idx+2}: {e}")
                    continue
            
            logger.info(f"Лист '{sheet_name}': загружено {len(candidates)} кандидатов")
            return candidates
        
        except Exception as e:
            logger.error(f"Ошибка при получении данных с листа '{sheet_name}': {e}")
            return []
