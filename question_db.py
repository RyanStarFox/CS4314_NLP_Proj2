"""
Question Database with SQLite Backend.

This module provides the QuestionDB class for managing user progress data.
All public methods maintain the same signatures as the original JSON-based
implementation for backward compatibility.
"""
import json
import os
import uuid
import time
import sqlite3
from database import get_connection, init_db, serialize_options, deserialize_options, serialize_question_data, deserialize_question_data

DB_FILE = "data/user_progress.db"


class QuestionDB:
    def __init__(self):
        # Ensure database is initialized
        init_db()
    
    def _get_book_id(self, book_name, cursor):
        """Get book ID by name, create if not exists."""
        cursor.execute('SELECT id FROM mistake_books WHERE name = ?', (book_name,))
        row = cursor.fetchone()
        if row:
            return row['id']
        
        # Create the book
        print(f"Auto-creating mistake book: {book_name}")
        # Explicitly set is_archived to 0 to avoid potential schema issues
        cursor.execute(
            'INSERT INTO mistake_books (name, created_at, is_archived) VALUES (?, ?, 0)',
            (book_name, time.time())
        )
        return cursor.lastrowid
    
    def _question_row_to_dict(self, row, book_name=None):
        """Convert a question row to the original dict format."""
        if row is None:
            return None
        
        question_data = {
            'question_type': row['question_type'],
            'question': row['question_text'],
            'options': deserialize_options(row['options']),
            'answers': deserialize_options(row['answers']),
            'correct_answer': row['correct_answer'],
            'explanation': row['explanation']
        }
        # Clean up None values
        question_data = {k: v for k, v in question_data.items() if v is not None}
        
        return {
            'id': row['id'],
            'timestamp': row['timestamp'],
            'kb_name': row['kb_name'] or book_name,
            'question': question_data,
            'user_answer': row['user_answer'],
            'is_correct': bool(row['is_correct']),
            'summary': row['summary'],
            'status': row['status'],
            'familiarity_score': row['familiarity_score'],
            'archived': bool(row['is_archived']),
            'last_reviewed': row['last_reviewed'],
            'review_count': row['review_count']
        }
    
    def _history_row_to_dict(self, row):
        """Convert a history row to the original dict format."""
        if row is None:
            return None
        
        return {
            'id': row['id'],
            'timestamp': row['timestamp'],
            'kb_name': row['kb_name'],
            'question': deserialize_question_data(row['question_data']) or {},
            'user_answer': row['user_answer'],
            'is_correct': bool(row['is_correct']),
            'summary': row['summary'],
            'status': row['status']
        }

    def list_mistake_books(self, include_archived=True):
        """获取错题本列表
        
        Args:
            include_archived: 是否包含已归档的错题本，默认True返回所有
        
        Returns:
            list of (book_name, is_archived) tuples if include_archived is True,
            else list of book_name strings (only unarchived)
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name, is_archived FROM mistake_books')
            rows = cursor.fetchall()
            
            if include_archived:
                return [(row['name'], bool(row['is_archived'])) for row in rows]
            else:
                return [row['name'] for row in rows if not row['is_archived']]
            
    def toggle_book_archive(self, book_name):
        """归档或取消归档错题本"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mistake_books 
                SET is_archived = CASE WHEN is_archived = 0 THEN 1 ELSE 0 END
                WHERE name = ?
            ''', (book_name,))
    
    def create_mistake_book(self, book_name):
        """创建新的错题本"""
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO mistake_books (name, created_at, is_archived) VALUES (?, ?, 0)',
                    (book_name, time.time())
                )
                return True
            except sqlite3.IntegrityError:
                # Book already exists
                return False
    
    def delete_mistake_book(self, book_name):
        """删除错题本"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get book ID
            cursor.execute('SELECT id FROM mistake_books WHERE name = ?', (book_name,))
            row = cursor.fetchone()
            if not row:
                return False
            
            book_id = row['id']
            
            # Delete questions in this book
            cursor.execute('DELETE FROM questions WHERE book_id = ?', (book_id,))
            
            # Delete the book
            cursor.execute('DELETE FROM mistake_books WHERE id = ?', (book_id,))
            
            # Ensure at least one book exists
            cursor.execute('SELECT COUNT(*) as count FROM mistake_books')
            if cursor.fetchone()['count'] == 0:
                cursor.execute(
                    'INSERT INTO mistake_books (name, created_at) VALUES (?, ?)',
                    ("默认错题本", time.time())
                )
            
            return True

    def rename_mistake_book(self, old_name, new_name):
        """重命名错题本"""
        if old_name == new_name or not new_name:
            return False
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if new name already exists
            cursor.execute('SELECT id FROM mistake_books WHERE name = ?', (new_name,))
            if cursor.fetchone():
                return False
            
            # Rename
            cursor.execute(
                'UPDATE mistake_books SET name = ? WHERE name = ?',
                (new_name, old_name)
            )
            
            # Update kb_name in questions
            cursor.execute(
                'UPDATE questions SET kb_name = ? WHERE kb_name = ?',
                (new_name, old_name)
            )
            
            return cursor.rowcount > 0

    def add_result(self, kb_name, question_data, user_answer, is_correct, summary=None, mistake_book=None, status="completed"):
        """添加答题记录
        
        Args:
            kb_name: 知识库名称
            question_data: 题目数据
            user_answer: 用户答案
            is_correct: 是否正确
            summary: 题目摘要
            mistake_book: 错题本名称，如果不指定则使用知识库名称（练习模式）或默认错题本
            status: 处理状态，"processing" 表示处理中，"completed" 表示已完成
        """
        record_id = str(uuid.uuid4())
        timestamp = time.time()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Add to history
            cursor.execute('''
                INSERT INTO history (id, timestamp, kb_name, question_data, user_answer, is_correct, summary, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_id,
                timestamp,
                kb_name,
                serialize_question_data(question_data),
                user_answer,
                1 if is_correct else 0,
                summary,
                status
            ))
            
            # If wrong, add to mistake book
            if not is_correct:
                # Determine which book to use
                if mistake_book is None:
                    if kb_name and kb_name != "Manual_Upload":
                        mistake_book = kb_name
                    else:
                        mistake_book = "默认错题本"
                
                book_id = self._get_book_id(mistake_book, cursor)
                
                # Extract question fields
                q_type = question_data.get('question_type') if question_data else None
                q_text = question_data.get('question') if question_data else None
                q_options = question_data.get('options') if question_data else None
                q_answers = question_data.get('answers') if question_data else None
                q_answer = question_data.get('correct_answer') if question_data else None
                q_explanation = question_data.get('explanation') if question_data else None
                
                cursor.execute('''
                    INSERT INTO questions (
                        id, book_id, timestamp, kb_name, question_type, question_text,
                        options, answers, correct_answer, explanation, user_answer, is_correct,
                        summary, status, familiarity_score, is_archived, last_reviewed, review_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record_id, book_id, timestamp, kb_name, q_type, q_text,
                    serialize_options(q_options), serialize_options(q_answers), q_answer, q_explanation,
                    user_answer, 0, summary, status, 2, 0, None, 0
                ))
        
        return record_id
    
    def update_question_status(self, record_id, question_data=None, summary=None, status="completed", mistake_book=None):
        """更新错题的处理状态和内容
        
        Args:
            record_id: 记录 ID
            question_data: 更新后的题目数据（可选）
            summary: 更新后的摘要（可选）
            status: 处理状态
            mistake_book: 错题本名称（可选，如果不指定则搜索所有错题本）
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query for questions
            updates = ['status = ?']
            params = [status]
            
            if question_data:
                updates.extend([
                    'question_type = ?',
                    'question_text = ?',
                    'options = ?',
                    'answers = ?',
                    'correct_answer = ?',
                    'explanation = ?'
                ])
                params.extend([
                    question_data.get('question_type'),
                    question_data.get('question'),
                    serialize_options(question_data.get('options')),
                    serialize_options(question_data.get('answers')),
                    question_data.get('correct_answer'),
                    question_data.get('explanation')
                ])
            
            if summary is not None:
                updates.append('summary = ?')
                params.append(summary)
            
            params.append(record_id)
            
            cursor.execute(f'''
                UPDATE questions SET {', '.join(updates)} WHERE id = ?
            ''', params)
            
            # Update history too
            history_updates = ['status = ?']
            history_params = [status]
            
            if question_data:
                history_updates.append('question_data = ?')
                history_params.append(serialize_question_data(question_data))
            
            if summary is not None:
                history_updates.append('summary = ?')
                history_params.append(summary)
            
            history_params.append(record_id)
            
            cursor.execute(f'''
                UPDATE history SET {', '.join(history_updates)} WHERE id = ?
            ''', history_params)
        
    # Alias for compatibility
    def update_result(self, record_id, book_name, data):
        """兼容旧的 update_result 调用"""
        if data.get("status") == "failed":
            self.update_question_status(
                record_id, 
                question_data={"question": data.get("question", "")}, 
                summary=data.get("explanation", ""), 
                status="failed",
                mistake_book=book_name
            )
        else:
            self.update_question_status(
                record_id,
                question_data=data.get("question"),
                summary=data.get("summary"),
                status=data.get("status", "completed"),
                mistake_book=book_name
            )

    def update_correct_answer(self, record_id, new_correct_answer, mistake_book=None):
        """Update the correct answer for a specific wrong question record."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE questions SET correct_answer = ? WHERE id = ?
            ''', (new_correct_answer, record_id))

    def save_outline(self, kb_name, outline_content, status="completed"):
        """Save generated outline for a specific knowledge base."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO outlines (kb_name, content, status, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (kb_name, outline_content, status, time.time()))

    def get_outline(self, kb_name):
        """Retrieve stored outline for a specific knowledge base."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT content, status, timestamp FROM outlines WHERE kb_name = ?
            ''', (kb_name,))
            row = cursor.fetchone()
            if row:
                return {
                    'content': row['content'],
                    'status': row['status'],
                    'timestamp': row['timestamp']
                }
            return None

    def get_wrong_questions(self, kb_name=None, mistake_book=None):
        """获取错题
        
        Args:
            kb_name: 知识库名称（已废弃，保留兼容性）
            mistake_book: 错题本名称，如果不指定则返回默认错题本
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if mistake_book is None:
                mistake_book = "默认错题本"
            
            cursor.execute('''
                SELECT q.*, mb.name as book_name
                FROM questions q
                JOIN mistake_books mb ON q.book_id = mb.id
                WHERE mb.name = ?
                ORDER BY q.timestamp DESC
            ''', (mistake_book,))
            
            return [self._question_row_to_dict(row, mistake_book) for row in cursor.fetchall()]

    def get_all_wrong_questions(self):
        """获取所有错题本的所有错题"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT q.*, mb.name as book_name
                FROM questions q
                JOIN mistake_books mb ON q.book_id = mb.id
                ORDER BY q.timestamp DESC
            ''')
            return [self._question_row_to_dict(row) for row in cursor.fetchall()]

    def remove_wrong_question(self, record_id, mistake_book=None):
        """从错题本中删除题目"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM questions WHERE id = ?', (record_id,))
    
    def update_familiarity_score(self, record_id, is_correct, mistake_book=None):
        """更新陌生分数
        
        规则：
        - 做错：+1 分
        - 做对：
          - ≥8 分：÷2 取整
          - <8 分：-1 分
        - 陌生分数 = 0 时自动归档
        
        Args:
            record_id: 记录 ID
            is_correct: 是否答对
            mistake_book: 错题本名称
        
        Returns:
            (new_score, archived): 新分数和归档状态
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current score
            cursor.execute('''
                SELECT familiarity_score, is_archived FROM questions WHERE id = ?
            ''', (record_id,))
            row = cursor.fetchone()
            
            if not row:
                return None, None
            
            current_score = row['familiarity_score'] or 2
            
            # Calculate new score
            if is_correct:
                if current_score >= 8:
                    new_score = current_score // 2
                else:
                    new_score = max(0, current_score - 1)
            else:
                new_score = current_score + 1
            
            # Auto-archive if score is 0
            is_archived = 1 if new_score == 0 else row['is_archived']
            
            # Update
            cursor.execute('''
                UPDATE questions 
                SET familiarity_score = ?, is_archived = ?, last_reviewed = ?, review_count = review_count + 1
                WHERE id = ?
            ''', (new_score, is_archived, time.time(), record_id))
            
            return new_score, bool(is_archived)
    
    def toggle_archive(self, record_id, mistake_book=None):
        """手动归档/取消归档错题
        
        Args:
            record_id: 记录 ID
            mistake_book: 错题本名称
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current state
            cursor.execute('SELECT is_archived FROM questions WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            
            if row:
                new_archived = 0 if row['is_archived'] else 1
                new_score = 2 if new_archived == 0 else None  # Reset score if unarchiving
                
                if new_score is not None:
                    cursor.execute('''
                        UPDATE questions SET is_archived = ?, familiarity_score = ? WHERE id = ?
                    ''', (new_archived, new_score, record_id))
                else:
                    cursor.execute('''
                        UPDATE questions SET is_archived = ? WHERE id = ?
                    ''', (new_archived, record_id))
    
    def get_archived_questions(self, mistake_book=None):
        """获取归档的错题
        
        Args:
            mistake_book: 错题本名称，如果不指定则返回默认错题本的归档题目
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if mistake_book is None:
                mistake_book = "默认错题本"
            
            cursor.execute('''
                SELECT q.*, mb.name as book_name
                FROM questions q
                JOIN mistake_books mb ON q.book_id = mb.id
                WHERE mb.name = ? AND q.is_archived = 1
                ORDER BY q.timestamp DESC
            ''', (mistake_book,))
            
            return [self._question_row_to_dict(row, mistake_book) for row in cursor.fetchall()]
