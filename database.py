import sqlite3
from datetime import datetime
import os
from config import DATABASE_PATH

class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT UNIQUE,
                    name TEXT NOT NULL,
                    object TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    recruiter_id TEXT,
                    reminder_sent INTEGER DEFAULT 0,
                    reminder_sent_date TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.commit()
    
    def candidate_exists(self, candidate_id):
        """Проверить, существует ли кандидат"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM candidates WHERE candidate_id = ?', (candidate_id,))
            return cursor.fetchone() is not None
    
    def add_candidate(self, candidate_id, name, obj, start_date, recruiter_id=None):
        """Добавить нового кандидата"""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO candidates 
                    (candidate_id, name, object, start_date, recruiter_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (candidate_id, name, obj, start_date, recruiter_id, now, now))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def get_candidates_for_reminder(self):
        """Получить кандидатов, которым нужно отправить напоминание"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, candidate_id, name, object, start_date, recruiter_id
                FROM candidates
                WHERE reminder_sent = 0
                ORDER BY start_date ASC
            ''')
            return cursor.fetchall()
    
    def mark_reminder_sent(self, candidate_id):
        """Отметить, что напоминание отправлено"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE candidates
                SET reminder_sent = 1, reminder_sent_date = ?
                WHERE candidate_id = ?
            ''', (now, candidate_id))
            conn.commit()
    
    def get_all_candidates(self):
        """Получить всех кандидатов"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT candidate_id, name, object, start_date, recruiter_id
                FROM candidates
            ''')
            return cursor.fetchall()
