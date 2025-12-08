from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from config import (
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    MODEL_NAME,
    VL_MODEL_NAME,
    TOP_K,
)
from vector_store import VectorStore
import re

class RAGAgent:
    def __init__(
        self,
        model: str = MODEL_NAME,
    ):
        self.model = model
        self.vl_model = VL_MODEL_NAME 

        self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
        self.vector_store = VectorStore()

        self.system_prompt = """你是一位专业、亲切的计算机课程助教。
任务：结合【课程资料】与【对话历史】回答学生问题。

基本准则：
1. **直接回答**：除非用户明确要求“出题”或“测验”，否则**绝对不要**生成题目。直接回答用户的问题即可。
2. **拒绝废话**：不要每次都重复“根据资料...”，直接说结论。
3. **准确引用**：引用知识点时，请在句末标注 (出处: 文件名 第X页)。
4. **格式规范**：Markdown格式，数学公式用LaTeX。

特殊模式：
- **作业批改**：当用户输入 A/B/C/D 时，检查历史记录中的题目，判断对错并解析。
- **自动出题**：仅当用户要求“出题”时，设计单选题，不给答案，等待作答。
"""

    def retrieve_context(
        self, query: str, top_k: int = TOP_K
    ) -> Tuple[str, List[Dict]]:
        """检索相关上下文"""
        if not query:
            return "", []

        results = self.vector_store.search(query, top_k=top_k)
        
        formatted_context = ""
        retrieved_docs = []

        if not results['documents'] or not results['documents'][0]:
            return "", []

        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]

        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            filename = meta.get('filename', '未知文件')
            page_num = meta.get('page_number', '?')
            source_label = f"{filename} (第 {page_num} 页)"
            formatted_context += f"【资料 {i+1}】({source_label}):\n{doc}\n\n"
            retrieved_docs.append({
                "content": doc,
                "metadata": meta,
                "score": dist,
                "source_label": source_label
            })

        return formatted_context, retrieved_docs

    def generate_response(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict]] = None,
        image_data: Optional[str] = None,
        is_quiz: bool = False,
        skip_retrieval: bool = False 
    ) -> str:
        """生成回答"""
        
        messages = [{"role": "system", "content": self.system_prompt}]

        # [关键修复] 处理历史记录，防止图片数据污染历史导致报错
        if chat_history:
            clean_history = []
            for msg in chat_history[-4:]: # 只取最近4条
                # 如果历史消息里有 image_base64 字段，我们只取 content 文本
                # 这样可以避免把巨大的 Base64 字符串重复发给 API，节省 Token 并防止报错
                content = msg.get("content", "")
                role = msg.get("role", "user")
                clean_history.append({"role": role, "content": content})
            messages.extend(clean_history)

        # 构建 User Prompt
        if skip_retrieval:
            user_text = f"""(用户正在回答上一轮的选择题)
学生回答：{query}
请执行【作业批改】：判断对错并解析。
"""
        elif is_quiz:
            user_text = f"""执行【自动出题】模式。
=== 课程资料 ===
{context if context else "（未检索到资料，基于通用知识出题）"}
=== 结束 ===
要求：出单选题，含A/B/C/D选项，不给答案。
"""
        else:
            user_text = f"""请阅读资料回答问题。
=== 课程资料 ===
{context if context else "（未检索到资料，尝试基于常识回答）"}
=== 结束 ===
学生问题：{query}
"""

        # 多模态逻辑
        if image_data:
            print(f" [系统] 切换至视觉模型: {self.vl_model}")
            content_payload = [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                }
            ]
            current_model = self.vl_model 
        else:
            content_payload = user_text
            current_model = self.model

        messages.append({"role": "user", "content": content_payload})

        temp_value = 0.7 if is_quiz else 0.3

        try:
            response = self.client.chat.completions.create(
                model=current_model, 
                messages=messages, 
                temperature=temp_value, 
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"生成回答时出错: {str(e)}"

    def answer_question(self, query: str, chat_history: Optional[List[Dict]] = None, top_k: int = TOP_K) -> str:
        """命令行入口"""
        if len(query) < 10 and re.match(r'^(我?选|答案是)?[a-dA-D\s]+$', query.strip()):
            return self.generate_response(query, "", chat_history, skip_retrieval=True)
        context, _ = self.retrieve_context(query, top_k=top_k)
        if not context: return "无相关资料。"
        return self.generate_response(query, context, chat_history)