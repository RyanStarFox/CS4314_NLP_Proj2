"""
SQLite Database Layer for User Progress Storage.

This module replaces the JSON-based storage with SQLite for better
reliability and query performance.
"""
import sqlite3
import os
import json
import sys
import threading
from contextlib import contextmanager
from settings_utils import get_user_data_dir

DB_FILE = "user_progress.db"

# Thread-local storage for connections (one connection per thread)
_thread_local = threading.local()


def get_db_path():
    """Get the absolute path to the database file."""
    data_dir = get_user_data_dir()
    return os.path.join(data_dir, DB_FILE)


def _get_thread_connection():
    """Get or create a connection for the current thread."""
    if not hasattr(_thread_local, 'conn') or _thread_local.conn is None:
        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _thread_local.conn = conn
    return _thread_local.conn


@contextmanager
def get_connection():
    """Context manager for database connections using thread-local singleton."""
    conn = _get_thread_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise



_db_initialized = False

def init_db():
    """Initialize the database with required tables."""
    global _db_initialized
    if _db_initialized:
        return
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 错题本表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistake_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_archived INTEGER DEFAULT 0,
                created_at REAL
            )
        ''')
        
        # 答题记录/错题表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                book_id INTEGER,
                timestamp REAL,
                kb_name TEXT,
                question_type TEXT,
                question_text TEXT,
                options TEXT,
                answers TEXT,
                correct_answer TEXT,
                explanation TEXT,
                user_answer TEXT,
                is_correct INTEGER,
                summary TEXT,
                status TEXT DEFAULT 'completed',
                familiarity_score INTEGER DEFAULT 2,
                is_archived INTEGER DEFAULT 0,
                last_reviewed REAL,
                review_count INTEGER DEFAULT 0,
                FOREIGN KEY (book_id) REFERENCES mistake_books(id)
            )
        ''')
        
        # Migration: Add answers column if missing (for existing databases)
        try:
            cursor.execute('ALTER TABLE questions ADD COLUMN answers TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # 历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                kb_name TEXT,
                question_data TEXT,
                user_answer TEXT,
                is_correct INTEGER,
                summary TEXT,
                status TEXT
            )
        ''')
        
        # 大纲表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outlines (
                kb_name TEXT PRIMARY KEY,
                content TEXT,
                status TEXT DEFAULT 'completed',
                timestamp REAL
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_book_id ON questions(book_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_kb_name ON questions(kb_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)')
        
        # 确保默认错题本存在
        cursor.execute('''
            INSERT OR IGNORE INTO mistake_books (name, created_at) 
            VALUES (?, ?)
        ''', ("默认错题本", None))
    
    _db_initialized = True



# Helper functions for JSON serialization
def serialize_options(options):
    """Serialize options list to JSON string."""
    if options is None:
        return None
    return json.dumps(options, ensure_ascii=False)


def deserialize_options(options_str):
    """Deserialize JSON string to options list."""
    if options_str is None:
        return None
    return json.loads(options_str)


def serialize_question_data(question_data):
    """Serialize question data dict to JSON string."""
    if question_data is None:
        return None
    return json.dumps(question_data, ensure_ascii=False)


def deserialize_question_data(question_data_str):
    """Deserialize JSON string to question data dict."""
    if question_data_str is None:
        return None
    return json.loads(question_data_str)

