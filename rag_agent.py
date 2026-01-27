from typing import List, Dict, Optional, Tuple, Any
import json
from openai import OpenAI
from config import (
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    MODEL_NAME,
    VL_MODEL_NAME,
    TOP_K,
    EXERCISE_TOP_K,
    MEMORY_WINDOW_SIZE,
    COLLECTION_NAME,
    MAX_TOKENS,
    get_openai_client,
)
from vector_store import VectorStore
import re
import random
import concurrent.futures

class RAGAgent:
    def __init__(
        self,
        model: str = MODEL_NAME,
        kb_name: str = COLLECTION_NAME
    ):
        self.model = model
        self.vl_model = VL_MODEL_NAME 
        self.kb_name = kb_name

        self.client = get_openai_client(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
        # 初始化 VectorStore 时指定 collection_name
        self.vector_store = VectorStore(collection_name=kb_name)

        self.system_prompt = """你是一位专业、亲切的计算机课程助教。
任务：结合【课程资料】与【对话历史】回答学生问题。

基本准则：
1. **直接回答**：除非用户明确要求"出题"或"测验"，否则**绝对不要**生成题目。直接回答用户的问题即可。
2. **拒绝废话**：不要每次都重复"根据资料..."，直接说结论。
3. **准确引用**：引用知识点时，请在句末标注 (出处: 文件名 第X页)。
4. **格式规范**：Markdown格式。数学公式必须用LaTeX并用美元符号包裹才能正确渲染：
   - 行内公式用单美元符号，如 $E=mc^2$
   - 块级公式用双美元符号，如 $$\\sum_{i=1}^{n} x_i$$
   - 选择题格式：必须包含题干和A/B/C/D四个选项
   - 选项中的公式部分用美元符号包裹，文本部分正常书写，例如：A. 错误排列的数量为 $D(n) = n! \\sum_{k=0}^{n} \\frac{(-1)^k}{k!}$

特殊模式：
- **作业批改**：当用户输入 A/B/C/D 时，检查历史记录中的题目，判断对错并解析。
- **自动出题**：仅当用户要求"出题"时，设计单选题，必须包含题干和A/B/C/D四个选项，不给答案，等待作答。
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

    def fix_latex_format(self, text: str) -> str:
        """修复LaTeX格式：将代码块中的LaTeX转换为美元符号格式"""
        # 1. 匹配 ```...``` 代码块中的LaTeX公式
        def replace_code_block(match):
            code_content = match.group(1)
            # 检查是否是LaTeX公式（包含常见的LaTeX命令）
            if any(cmd in code_content for cmd in ['\\sum', '\\frac', '\\int', '\\sqrt', '\\left', '\\right', '=', '^', '_']):
                cleaned = code_content.strip()
                # 单行用单美元符号，多行用双美元符号
                if '\n' in cleaned:
                    return f"$${cleaned}$$"
                else:
                    return f"${cleaned}$"
            return match.group(0)
        
        # 匹配 ```latex、```math 或普通 ``` 代码块
        text = re.sub(r'```(?:latex|math)?\n?(.*?)```', replace_code_block, text, flags=re.DOTALL)
        
        # 2. 匹配行内代码 `...` 中的LaTeX
        def replace_inline_code(match):
            code_content = match.group(1)
            if any(cmd in code_content for cmd in ['\\sum', '\\frac', '\\int', '\\sqrt', '\\left', '\\right', '=', '^', '_']):
                return f"${code_content}$"
            return match.group(0)
        
        text = re.sub(r'`([^`]+)`', replace_inline_code, text)
        
        # 3. 修复选择题选项中的LaTeX（A. D(n) = n! \sum... 格式）
        # 匹配选项行，查找未用美元符号包裹的LaTeX公式
        lines = text.split('\n')
        fixed_lines = []
        for line in lines:
            # 匹配选项格式：A. 或 B. 等开头
            if re.match(r'^[A-D][\.\)]\s*', line):
                # 查找选项字母后的内容
                option_match = re.match(r'^([A-D][\.\)])\s*(.+)', line)
                if option_match:
                    prefix = option_match.group(1)
                    content = option_match.group(2)
                    
                    # 如果内容中包含LaTeX命令但不在美元符号中，需要包裹
                    # 查找包含反斜杠但不在$...$中的部分
                    if '\\' in content and '$' not in content:
                        # 整个内容作为公式包裹
                        line = f"{prefix} ${content}$"
                    elif '\\' in content:
                        # 已经有部分美元符号，需要更精细处理
                        # 查找未包裹的LaTeX片段
                        parts = re.split(r'(\$[^$]+\$)', content)
                        fixed_parts = []
                        for part in parts:
                            if part.startswith('$') and part.endswith('$'):
                                fixed_parts.append(part)  # 已经是包裹的
                            elif '\\' in part:
                                fixed_parts.append(f"${part}$")  # 需要包裹
                            else:
                                fixed_parts.append(part)  # 普通文本
                        line = f"{prefix} {''.join(fixed_parts)}"
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

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
            for msg in chat_history[-MEMORY_WINDOW_SIZE:]: # 只取最近 N 条
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
要求：出一道完整的单选题，必须包含：
1. **题干**：清晰的问题描述
2. **四个选项**：A、B、C、D四个选项
3. **不给答案**：等待学生作答

重要格式要求：
- 必须包含题干，不能只有选项
- 选项可以包含文本和公式的混合，例如：A. 错误排列的数量为 $D(n) = n! \\sum_{{k=0}}^{{n}} \\frac{{(-1)^k}}{{k!}}$
- 选项中的数学公式部分必须用单美元符号 $...$ 包裹
- 绝对不要使用代码块（```）包裹LaTeX公式
- 示例格式：
  题目：什么是错位排列的数量？
  A. 错误排列的数量为 $D(n) = n! \\sum_{{k=0}}^{{n}} \\frac{{(-1)^k}}{{k!}}$
  B. $D(n) = n! \\sum_{{k=0}}^{{n}} \\frac{{(-1)^k}}{{k}}$
  C. $D(n) = \\sum_{{k=0}}^{{n}} \\frac{{(-1)^k}}{{k!}}$
  D. 其他答案
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

        # IMPORTANT: For models that don't support multi-modal input in the 'content' field as a list when using tools or system prompts in specific ways,
        # we need to ensure the format is correct.
        # OpenAI API format for vision: content is a list of dicts.
        
        # If it's the first user message, append it. 
        # If we have history, we need to be careful. The history logic above adds dicts to `messages`.
        # Here we construct the new user message.
        
        new_user_msg = {"role": "user", "content": content_payload}
        messages.append(new_user_msg)

        # Determine temperature
        # Quiz generation uses a dedicated function, so this generate_response is mostly for chat.
        # However, if is_quiz flag is true (legacy path or specific instruction), we set it.
        # Standard chat should be lower for accuracy, creative tasks higher.
        temp_value = 0.7 if is_quiz else 0.3

        try:
            response = self.client.chat.completions.create(
                model=current_model, 
                messages=messages, 
                temperature=temp_value, 
                max_tokens=1500
            )
            response_text = response.choices[0].message.content
            # 修复LaTeX格式：将代码块中的LaTeX转换为美元符号格式
            # 不仅是 is_quiz 模式，智能助教的回答也需要修复 LaTeX 格式
            response_text = self.fix_latex_format(response_text)
            return response_text
        except Exception as e:
            return f"生成回答时出错: {str(e)}"

    def answer_question(self, query: str, chat_history: Optional[List[Dict]] = None, top_k: int = TOP_K, image_data: Optional[str] = None) -> str:
        """命令行入口"""
        if len(query) < 10 and re.match(r'^(我?选|答案是)?[a-dA-D\s]+$', query.strip()):
            return self.generate_response(query, "", chat_history, skip_retrieval=True, image_data=image_data)
        
        context, _ = self.retrieve_context(query, top_k=top_k)
        
        # If no context is found, but we have an image, we should still proceed.
        # Only return "No relevant data" if neither context nor image exists.
        if not context and not image_data: 
            return "无相关资料。"
            
        return self.generate_response(query, context, chat_history, image_data=image_data)

    def generate_quiz(self, topic: str, q_type: str, question_format: str = "multiple_choice", num_options: int = 4, num_blanks: int = 3, randomize_context: bool = False) -> Dict[str, Any]:
        """生成一道题，返回 JSON 格式
        
        Args:
            topic: 题目主题
            q_type: 题目类型（偏概念/偏应用）
            question_format: 题目格式，"multiple_choice" 或 "fill_in_blank"
            num_options: 选择题选项数量
            num_blanks: 填空题空格数量
            randomize_context: 是否使用随机上下文策略 (Top K*5 中随机选 Top K)
        """
        
        # 检索上下文
        if randomize_context:
            # 扩大召回范围，从中随机采样，以增加题目多样性
            pool_size = EXERCISE_TOP_K 
            context_str, docs = self.retrieve_context(topic, top_k=pool_size)
            
            if docs:
                # 随机采样 TOP_K 个文档，或者如果文档不够，就全部使用
                sample_size = min(TOP_K, len(docs))
                sampled_docs = random.sample(docs, sample_size)
                
                # 重新构建 context 字符串
                formatted_context = ""
                for i, doc_info in enumerate(sampled_docs):
                    formatted_context += f"【资料 {i+1}】({doc_info['source_label']}):\n{doc_info['content']}\n\n"
                context = formatted_context
        else:
            context, _ = self.retrieve_context(topic)
        
        # 根据题目格式生成不同的提示词
        if question_format == "fill_in_blank":
            prompt = f"""
你是一个专业的出题老师。请根据以下资料出一道【{q_type}】类型的填空题。
资料：
{context[:2000]}

要求：
1. 题目类型：{q_type} (偏概念/偏应用)
2. 空格数量：{num_blanks}个
3. 在题目中使用 _____ 表示需要填空的位置
4. 输出格式：必须是严格的JSON格式，不要包含Markdown代码块标记。

JSON格式模板：
{{
    "question_type": "fill_in_blank",
    "question": "题目内容，使用 _____ 表示空格",
    "answers": ["第一个空的答案", "第二个空的答案", ...],
    "explanation": "解析"
}}

示例：
{{
    "question_type": "fill_in_blank",
    "question": "在Python中，_____ 是一种可变的数据类型，而 _____ 是不可变的。",
    "answers": ["列表(list)", "元组(tuple)"],
    "explanation": "列表是可变的，可以修改元素；元组是不可变的，一旦创建就不能修改。"
}}
"""
        else:  # multiple_choice
            prompt = f"""
你是一个专业的出题老师。请根据以下资料出一道【{q_type}】类型的单选题。
资料：
{context[:2000]}

要求：
1. 题目类型：{q_type} (偏概念/偏应用)
2. 选项数量：{num_options}个
3. 输出格式：必须是严格的JSON格式，不要包含Markdown代码块标记。

JSON格式模板：
{{
    "question_type": "multiple_choice",
    "question": "题目内容",
    "options": ["选项1", "选项2", ...],
    "correct_answer": "正确选项的内容（必须与options中的某一项完全一致）",
    "explanation": "解析"
}}
"""
        
        messages = [
            {"role": "system", "content": "你是一个严谨的出题系统，只输出JSON。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9, # High temperature for variety
                response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content
            quiz_data = json.loads(content)
            
            # 确保包含 question_type 字段
            if "question_type" not in quiz_data:
                quiz_data["question_type"] = question_format
            
            # 修复 JSON 中所有文本字段的 LaTeX 格式
            if "question" in quiz_data:
                quiz_data["question"] = self.fix_latex_format(quiz_data["question"])
            
            if question_format == "fill_in_blank":
                if "answers" in quiz_data and isinstance(quiz_data["answers"], list):
                    quiz_data["answers"] = [self.fix_latex_format(ans) for ans in quiz_data["answers"]]
            else:  # multiple_choice
                if "options" in quiz_data and isinstance(quiz_data["options"], list):
                    quiz_data["options"] = [self.fix_latex_format(opt) for opt in quiz_data["options"]]
                if "correct_answer" in quiz_data:
                    quiz_data["correct_answer"] = self.fix_latex_format(quiz_data["correct_answer"])
            
            if "explanation" in quiz_data:
                quiz_data["explanation"] = self.fix_latex_format(quiz_data["explanation"])
            
            return quiz_data
        except Exception as e:
            print(f"出题失败: {e}")
            return {}

    def generate_quiz_batch(self, count: int, topic: str, q_type: str, question_format: str = "multiple_choice", num_options: int = 4, num_blanks: int = 3) -> List[Dict[str, Any]]:
        """并行生成多道题目"""
        print(f"开始并行生成 {count} 道题目...")
        questions = []
        
        # 使用 ThreadPoolExecutor 并行调用
        # 注意：OpenAI 客户端是线程安全的
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(count, 5)) as executor:
            # 提交任务
            futures = [
                executor.submit(self.generate_quiz, topic, q_type, question_format, num_options, num_blanks, randomize_context=True) 
                for _ in range(count)
            ]
            
            # 获取结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    q = future.result()
                    if q:
                        questions.append(q)
                except Exception as e:
                    print(f"并行任务出错: {e}")
                    
        return questions

    def generate_outline(self) -> str:
        """根据知识库生成复习大纲"""
        # 导入 KBManager 获取文件大小
        from kb_manager import KBManager
        kb_manager = KBManager()
        
        # 获取知识库文件总大小（字节）
        total_size_bytes = kb_manager.get_kb_total_size(self.kb_name)
        total_size_mb = total_size_bytes / (1024 * 1024)  # 转换为 MB
        
        # 计算知识库文档数量（用于 top_k）
        total_docs = self.vector_store.get_collection_count()
        # 动态调整 top_k，至少20，最多100
        dynamic_top_k = min(max(20, total_docs // 2), 10000)
        
        # 动态调整 max_tokens，与文件总大小成正比
        # 基础值：2000 tokens
        # 每 1 MB 增加 200 tokens
        # 最小 2000，最大 8000
        base_tokens = 2000
        extra_tokens = int(total_size_mb * 200)
        dynamic_max_tokens = min(max(base_tokens, base_tokens + extra_tokens), 8000)
        
        # 检索更多上下文
        context, _ = self.retrieve_context("目录 章节 大纲 核心概念 重点 Summary", top_k=dynamic_top_k)
        
        prompt = f"""
请根据以下检索到的课程资料片段，整理生成一份**非常详细**的复习大纲。
资料片段（共检索到 {dynamic_top_k} 个相关片段）：
{context[:15000]} 

要求：
1. 使用 Markdown 格式。
2. 结构清晰，分章节或知识模块。
3. **内容详实**：包含核心概念、定义、定理和重点公式（如有）。不要只列标题。
4. 篇幅应与资料量相匹配，尽可能覆盖所有重要知识点。
"""
        messages = [
            {"role": "system", "content": "你是一个课程助教，擅长总结大纲。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=dynamic_max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"生成大纲失败: {e}"

    def refine_outline(self, current_outline: str, user_feedback: str) -> str:
        """根据用户反馈修改大纲"""
        prompt = f"""
你是一个专业的课程助教。这是你之前生成的复习大纲：
=== 当前大纲 ===
{current_outline}
=== 结束 ===

用户的修改意见：
{user_feedback}

请根据用户的意见对大纲进行修改和优化。
要求：
1. 保持 Markdown 格式。
2. 针对性地修改，不要随意删除未被提及的正确内容。
3. 输出完整的、修改后的新大纲。
"""
        messages = [
            {"role": "system", "content": "你是一个擅长修改文档的助教。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4000 
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"修改大纲失败: {e}"
