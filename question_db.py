import json
import os
import uuid
import time

DB_FILE = "data/user_progress.json"

class QuestionDB:
    def __init__(self):
        self.db_file = DB_FILE
        # Ensure data dir exists
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        if not os.path.exists(self.db_file):
            self._save_db({"history": [], "wrong_questions": []})
    
    def _load_db(self):
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"history": [], "wrong_questions": []}
    
    def _save_db(self, data):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_result(self, kb_name, question_data, user_answer, is_correct, summary=None):
        db = self._load_db()
        
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "kb_name": kb_name,
            "question": question_data,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "summary": summary  # Store LLM summary
        }
        
        db["history"].append(record)
        
        if not is_correct:
            db["wrong_questions"].append(record)
        
        self._save_db(db)

    def update_correct_answer(self, record_id, new_correct_answer):
        """Update the correct answer for a specific wrong question record."""
        db = self._load_db()
        for q in db["wrong_questions"]:
            if q["id"] == record_id:
                if "question" in q:
                    q["question"]["correct_answer"] = new_correct_answer
                break
        self._save_db(db)

    def get_wrong_questions(self, kb_name=None):
        db = self._load_db()
        if kb_name:
            return [q for q in db["wrong_questions"] if q["kb_name"] == kb_name]
        return db["wrong_questions"]

    def remove_wrong_question(self, record_id):
        db = self._load_db()
        db["wrong_questions"] = [q for q in db["wrong_questions"] if q["id"] != record_id]
        self._save_db(db)

