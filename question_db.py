import json
import os
import uuid
import time
import threading

DB_FILE = "data/user_progress.json"

class QuestionDB:
    def __init__(self):
        self.db_file = DB_FILE
        # Ensure data dir exists
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        if not os.path.exists(self.db_file):
            # 新数据结构：支持多个错题本
            # mistake_books: {"默认错题本": [], "知识库A": [], ...}
            self._save_db({
                "history": [], 
                "wrong_questions": [],  # 保留旧字段兼容性
                "mistake_books": {"默认错题本": []}
            })
        else:
            # 迁移旧数据到新结构
            self._migrate_old_data()
    
    def _load_db(self):
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "history": [], 
                "wrong_questions": [],
                "mistake_books": {"默认错题本": []}
            }
    
    def _save_db(self, data):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _migrate_old_data(self):
        """迁移旧版本的错题数据到新的多错题本结构"""
        db = self._load_db()
        
        # 如果没有 mistake_books 字段，说明是旧版本数据
        if "mistake_books" not in db:
            db["mistake_books"] = {"默认错题本": []}
            
            # 将旧的 wrong_questions 迁移到默认错题本
            if "wrong_questions" in db and db["wrong_questions"]:
                db["mistake_books"]["默认错题本"] = db["wrong_questions"]
            
            self._save_db(db)
            print("已迁移旧版本错题数据到多错题本结构")

    def list_mistake_books(self, include_archived=True):
        """获取错题本列表
        
        Args:
            include_archived: 是否包含已归档的错题本，默认True返回所有
        
        Returns:
            list of (book_name, is_archived) tuples if include_archived is True,
            else list of book_name strings (only unarchived)
        """
        db = self._load_db()
        books = db.get("mistake_books", {"默认错题本": []})
        archived_books = set(db.get("archived_books", []))
        
        if include_archived:
            return [(name, name in archived_books) for name in books.keys()]
        else:
            return [name for name in books.keys() if name not in archived_books]
            
    def toggle_book_archive(self, book_name):
        """归档或取消归档错题本"""
        db = self._load_db()
        if "archived_books" not in db:
            db["archived_books"] = []
            
        if book_name in db["archived_books"]:
            db["archived_books"].remove(book_name)
        else:
            db["archived_books"].append(book_name)
            
        self._save_db(db)
    
    def create_mistake_book(self, book_name):
        """创建新的错题本"""
        db = self._load_db()
        if "mistake_books" not in db:
            db["mistake_books"] = {}
        
        if book_name not in db["mistake_books"]:
            db["mistake_books"][book_name] = []
            self._save_db(db)
            return True
        return False
    
    def delete_mistake_book(self, book_name):
        """删除错题本"""
        db = self._load_db()
        books = db.get("mistake_books", {})
        
        if book_name in books:
            del books[book_name]
            # 如果全部删完了，创建一个新的默认错题本
            if not books:
                books["默认错题本"] = []
            self._save_db(db)
            return True
        return False

    def rename_mistake_book(self, old_name, new_name):
        """重命名错题本"""
        if old_name == new_name or not new_name:
            return False
        
        db = self._load_db()
        books = db.get("mistake_books", {})
        
        if old_name in books and new_name not in books:
            # 转移数据
            books[new_name] = books.pop(old_name)
            # 更新题目中的 kb_name 字段（如果需要，虽然通常不需要，因为是动态获取的）
            for q in books[new_name]:
                q["kb_name"] = new_name # 关联到新名称
            
            self._save_db(db)
            return True
        return False

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
        db = self._load_db()
        
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "kb_name": kb_name,
            "question": question_data,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "summary": summary,  # Store LLM summary
            "status": status,  # 处理状态
            "familiarity_score": 2,  # 新增：陌生分数，默认为 2
            "archived": False,  # 新增：归档状态
            "last_reviewed": None,  # 新增：最后复习时间
            "review_count": 0  # 新增：复习次数
        }
        
        db["history"].append(record)
        
        if not is_correct:
            # 保留旧字段兼容性
            db["wrong_questions"].append(record)
            
            # 添加到指定的错题本
            if mistake_book is None:
                # 如果来自练习模式，使用知识库名称作为错题本
                # 如果是手动添加，则使用默认错题本
                if kb_name and kb_name != "Manual_Upload":
                    mistake_book = kb_name
                else:
                    mistake_book = "默认错题本"
            
            # 确保错题本存在
            if "mistake_books" not in db:
                db["mistake_books"] = {}
            if mistake_book not in db["mistake_books"]:
                db["mistake_books"][mistake_book] = []
            
            db["mistake_books"][mistake_book].append(record)
        
        self._save_db(db)
        return record["id"]  # 返回记录 ID，用于后续更新
    
    def update_question_status(self, record_id, question_data=None, summary=None, status="completed", mistake_book=None):
        """更新错题的处理状态和内容
        
        Args:
            record_id: 记录 ID
            question_data: 更新后的题目数据（可选）
            summary: 更新后的摘要（可选）
            status: 处理状态
            mistake_book: 错题本名称（可选，如果不指定则搜索所有错题本）
        """
        db = self._load_db()
        
        # 更新旧字段（兼容性）
        for q in db.get("wrong_questions", []):
            if q["id"] == record_id:
                if question_data:
                    q["question"] = question_data
                if summary is not None:
                    q["summary"] = summary
                q["status"] = status
                break
        
        # 更新错题本中的记录
        if mistake_book:
            for q in db.get("mistake_books", {}).get(mistake_book, []):
                if q["id"] == record_id:
                    if question_data:
                        q["question"] = question_data
                    if summary is not None:
                        q["summary"] = summary
                    q["status"] = status
                    break
        else:
            # 如果没有指定错题本，搜索所有错题本
            for book_name, questions in db.get("mistake_books", {}).items():
                for q in questions:
                    if q["id"] == record_id:
                        if question_data:
                            q["question"] = question_data
                        if summary is not None:
                            q["summary"] = summary
                        q["status"] = status
                        break
        
        self._save_db(db)

    def update_correct_answer(self, record_id, new_correct_answer, mistake_book=None):
        """Update the correct answer for a specific wrong question record."""
        db = self._load_db()
        
        # 更新旧字段（兼容性）
        for q in db.get("wrong_questions", []):
            if q["id"] == record_id:
                if "question" in q:
                    q["question"]["correct_answer"] = new_correct_answer
                break
        
        # 更新错题本中的记录
        if mistake_book:
            for q in db.get("mistake_books", {}).get(mistake_book, []):
                if q["id"] == record_id:
                    if "question" in q:
                        q["question"]["correct_answer"] = new_correct_answer
                    break
        else:
            # 如果没有指定错题本，搜索所有错题本
            for book_name, questions in db.get("mistake_books", {}).items():
                for q in questions:
                    if q["id"] == record_id:
                        if "question" in q:
                            q["question"]["correct_answer"] = new_correct_answer
                        break
        
        self._save_db(db)

    def save_outline(self, kb_name, outline_content, status="completed"):
        """Save generated outline for a specific knowledge base."""
        db = self._load_db()
        if "outlines" not in db:
            db["outlines"] = {}
        
        db["outlines"][kb_name] = {
            "content": outline_content,
            "status": status,
            "timestamp": time.time()
        }
        self._save_db(db)

    def get_outline(self, kb_name):
        """Retrieve stored outline for a specific knowledge base."""
        db = self._load_db()
        return db.get("outlines", {}).get(kb_name)

    def get_wrong_questions(self, kb_name=None, mistake_book=None):
        """获取错题
        
        Args:
            kb_name: 知识库名称（已废弃，保留兼容性）
            mistake_book: 错题本名称，如果不指定则返回默认错题本
        """
        db = self._load_db()
        
        if mistake_book:
            return db.get("mistake_books", {}).get(mistake_book, [])
        else:
            # 默认返回默认错题本
            return db.get("mistake_books", {}).get("默认错题本", [])

    def get_all_wrong_questions(self):
        """获取所有错题本的所有错题"""
        db = self._load_db()
        all_questions = []
        for book_name, questions in db.get("mistake_books", {}).items():
            all_questions.extend(questions)
        return all_questions

    def remove_wrong_question(self, record_id, mistake_book=None):
        """从错题本中删除题目"""
        db = self._load_db()
        
        # 从旧字段删除（兼容性）
        db["wrong_questions"] = [q for q in db.get("wrong_questions", []) if q["id"] != record_id]
        
        # 从错题本删除
        if mistake_book:
            if mistake_book in db.get("mistake_books", {}):
                db["mistake_books"][mistake_book] = [
                    q for q in db["mistake_books"][mistake_book] if q["id"] != record_id
                ]
        else:
            # 如果没有指定错题本，从所有错题本中删除
            for book_name in db.get("mistake_books", {}):
                db["mistake_books"][book_name] = [
                    q for q in db["mistake_books"][book_name] if q["id"] != record_id
                ]
        
        self._save_db(db)
    
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
        db = self._load_db()
        
        def update_score(question):
            """更新单个题目的分数"""
            # 确保有陌生分数字段（兼容旧数据）
            if "familiarity_score" not in question:
                question["familiarity_score"] = 2
            if "archived" not in question:
                question["archived"] = False
            if "review_count" not in question:
                question["review_count"] = 0
            
            current_score = question["familiarity_score"]
            
            if is_correct:
                # 做对了
                if current_score >= 8:
                    question["familiarity_score"] = current_score // 2
                else:
                    question["familiarity_score"] = max(0, current_score - 1)
            else:
                # 做错了
                question["familiarity_score"] = current_score + 1
            
            # 更新复习信息
            question["last_reviewed"] = time.time()
            question["review_count"] = question.get("review_count", 0) + 1
            
            # 自动归档（陌生分数为 0）
            if question["familiarity_score"] == 0:
                question["archived"] = True
            
            return question["familiarity_score"], question["archived"]
        
        # 更新旧字段（兼容性）
        for q in db.get("wrong_questions", []):
            if q["id"] == record_id:
                update_score(q)
                break
        
        # 更新错题本中的记录
        if mistake_book:
            for q in db.get("mistake_books", {}).get(mistake_book, []):
                if q["id"] == record_id:
                    new_score, archived = update_score(q)
                    self._save_db(db)
                    return new_score, archived
        else:
            # 如果没有指定错题本，搜索所有错题本
            for book_name, questions in db.get("mistake_books", {}).items():
                for q in questions:
                    if q["id"] == record_id:
                        new_score, archived = update_score(q)
                        self._save_db(db)
                        return new_score, archived
        
        self._save_db(db)
        return None, None
    
    def toggle_archive(self, record_id, mistake_book=None):
        """手动归档/取消归档错题
        
        Args:
            record_id: 记录 ID
            mistake_book: 错题本名称
        """
        db = self._load_db()
        
        # 更新旧字段（兼容性）
        for q in db.get("wrong_questions", []):
            if q["id"] == record_id:
                if "archived" not in q:
                    q["archived"] = False
                q["archived"] = not q["archived"]
                # 如果取消归档，重置陌生分数为 2
                if not q["archived"]:
                    q["familiarity_score"] = 2
                break
        
        # 更新错题本中的记录
        if mistake_book:
            for q in db.get("mistake_books", {}).get(mistake_book, []):
                if q["id"] == record_id:
                    if "archived" not in q:
                        q["archived"] = False
                    q["archived"] = not q["archived"]
                    # 如果取消归档，重置陌生分数为 2
                    if not q["archived"]:
                        q["familiarity_score"] = 2
                    break
        else:
            # 如果没有指定错题本，搜索所有错题本
            for book_name, questions in db.get("mistake_books", {}).items():
                for q in questions:
                    if q["id"] == record_id:
                        if "archived" not in q:
                            q["archived"] = False
                        q["archived"] = not q["archived"]
                        # 如果取消归档，重置陌生分数为 2
                        if not q["archived"]:
                            q["familiarity_score"] = 2
                        break
        
        self._save_db(db)
    
    def get_archived_questions(self, mistake_book=None):
        """获取归档的错题
        
        Args:
            mistake_book: 错题本名称，如果不指定则返回默认错题本的归档题目
        """
        db = self._load_db()
        
        if mistake_book:
            questions = db.get("mistake_books", {}).get(mistake_book, [])
        else:
            questions = db.get("mistake_books", {}).get("默认错题本", [])
        
        # 筛选归档的题目
        archived = [q for q in questions if q.get("archived", False)]
        return archived

