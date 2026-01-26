import streamlit as st
import time
import json
import threading
import base64
from question_db import QuestionDB
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_API_BASE, VL_MODEL_NAME, MODEL_NAME

st.set_page_config(page_title="错题整理", page_icon="logo.webp", layout="wide")

# Page Context Management: Reset dialogs when entering from another page
if st.session_state.get("last_page") != "mistakes":
    st.session_state.active_dialog_id = None
    st.session_state.active_dialog_type = None
    st.session_state.last_page = "mistakes"

# 自定义 CSS 样式
st.markdown("""
<style>
    .block-container { padding-top: 4rem; }
    /* 全局按钮样式优化 */
    .stButton button {
        border-radius: 8px !important;
        border: 1px solid #e8e8e8;
        transition: all 0.3s ease;
        padding-top: 0.2rem !important;
        padding-bottom: 0.2rem !important;
        height: auto !important;
        min-height: 0px !important;
    }
    
    .stButton button:hover {
        border-color: #FF4B4B !important;
        background-color: #FFF5F5 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(255,75,75,0.1);
    }
    
    /* 调整查看详情按钮的高度 */
    .view-det-btn button {
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
    }

    /* 保证垂直居中 */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }

    /* 紧凑化带边框的容器 */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.05rem 0.5rem !important; /* Extremely minimal vertical padding */
        gap: 0px !important;
    }
    
    /* 强制水平块 (columns row) 垂直居中及高度控制 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        min-height: 24px !important; /* Reduced min-height */
        height: auto !important;
    }
    
    /* 强制每个列垂直居中其内容 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 24px !important; /* Match horizontal block */
    }
    
    /* 强制列内所有子元素也居中 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"] > div {
        display: flex !important;
        align-items: center !important;
        width: 100%;
        min-height: 24px !important;
    }

    /* Checkbox 样式重置 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stCheckbox"] {
        min-height: unset !important;
        height: 24px !important;
        margin: 0px !important;
        padding: 0px !important;
        justify-content: center !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stCheckbox"] label {
        min-height: unset !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    
    /* Markdown 容器垂直居中 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        align-items: center !important;
        min-height: 24px !important;
    }
    
    /* Markdown 文本样式 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] p {
        margin: 0px !important;
        padding: 0px !important;
        line-height: 1.2 !important; /* Tighter line height */
        font-size: 15px !important;
    }
    
    /* 按钮容器样式 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] {
        margin: 0px !important;
        padding: 0px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 24px !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button {
        margin: 0px !important;
        padding: 0.1rem 0.5rem !important; /* Smaller button padding */
        min-height: 24px !important;
        height: 24px !important;
        line-height: 1 !important;
    }
    
    
    
    /* Primary按钮样式统一 */
    .stButton button[kind="primary"] {
        background-color: #FF4B4B;
        color: white;
        border: 2px solid #FF4B4B;
    }
    
    .stButton button[kind="primary"]:hover {
        background-color: #FF3333 !important;
        border-color: #FF3333 !important;
        color: white !important;
    }
    
    /* 菜单按钮样式 */
    button[kind="secondary"] {
        background: transparent;
        border: 1px solid #e0e0e0;
    }
    button[kind="secondary"]:hover {
        background: #f5f5f5;
        border-color: #FF4B4B !important;
    }
</style>
""", unsafe_allow_html=True)

question_db = QuestionDB()

# Session State 初始化
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "list"  # list: 错题本列表, detail: 错题详情

if "selected_mistake_book" not in st.session_state:
    st.session_state.selected_mistake_book = "默认错题本"

if "mistake_index" not in st.session_state:
    st.session_state.mistake_index = 0

if "mistake_mode" not in st.session_state:
    st.session_state.mistake_mode = "list"  # list, quiz

if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = set()

# --- Global Helper Functions & Dialogs ---

def process_question_async(rid, book_name, q_c, q_o, q_correct, q_e, ocr_b64, attachment_b64, f_type):
    try:
        from openai import OpenAI
        import json
        import os  # Fix NameError
        
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )
        model_name = os.getenv("VL_MODEL_NAME", "gpt-4o")

        # --- Stage 1: OCR & Classification ---
        # Objective: Get raw text and determine type quickly.
        source_text = q_c if q_c else ""
        detected_type = f_type if f_type else "fill_in_blank" # Default fallback
        
        if ocr_b64 and not source_text:
            # Call AI for OCR + Classification
            sys_prompt_1 = """
你是一个题目识别助手。请完成两个任务：
1. **OCR识别**：将图片中的题目文字完整提取出来。
   - 保持原有换行和列表格式。
   - 公式必须使用 $ 或 $$ 包裹。严禁使用 \[ \] 或 \( \)。
2. **题型分类**：根据题目结构判断题型。
   - "multiple_choice" (单选): 有选项列表(A/B/C/D 或 1/2/3/4)且单选。
   - "multi_select" (多选): 题干含"多选/Select all"或答案看似多个。
   - "boolean" (判断): 判断对错。
   - "fill_in_blank" (填空): 文本中有横线/括号需要填写，或上下文填空。
   - "short_answer" (解答): 计算题、简答题，有确切结果但非选项选择。
   - "proof" (证明): 证明题、推导题，无单一确切结果，需长篇论述。

输出 JSON: {"question_text": "...", "question_type": "..."}
"""
            msgs_1 = [
                {"role": "system", "content": sys_prompt_1},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "请处理这张图片。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ocr_b64}"}}
                    ]
                }
            ]
            try:
                resp_1 = client.chat.completions.create(
                    model=model_name,
                    messages=msgs_1, # type: ignore
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                res_1 = json.loads(resp_1.choices[0].message.content)
                source_text = res_1.get("question_text", "（识别失败）")
                detected_type = res_1.get("question_type", "fill_in_blank")
            except Exception as e:
                print(f"Stage 1 Error: {e}")
                # Update DB directly to inform user
                failed_data = {
                    "question": "❌ 识别失败，请删除该题后重试",
                    "explanation": f"错误详情: {str(e)}",
                    "status": "failed"
                }
                qk = QuestionDB()
                qk.update_result(rid, book_name, failed_data)
                return # Stop processing


        # --- Stage 2: Extraction & Generation ---
        # Objective: Standardize options, format answers, generate explanation.
        # Uses source_text (from Stage 1 or User) + User Answer
        
        sys_prompt_2 = """
你是一个智能助教。根据题目文本、类型和用户答案，完善题目信息。
请输出 JSON:
{
    "question": "题目主干...",    // 修正后的题目（去除选项）
    "options": ["A. xxx", "B. xxx"], // 仅针对选择类，需标准化为A. B. ...
    "correct_answer": "...",        // 标准化答案
    "answers": ["..."],             // 填空题/解答题答案数组（支持多空/多问）
    "explanation": "...",           // 详细解析
    "summary": "..."                // 题目梗概
}

**规则**：
1. **question**: 提取题目主干。**注意**：对于选择题，请在 question 字段中**去除**选项部分，只保留题干文本。
2. 如果已确定是选择题 (multiple_choice/multi_select)，请从题目文本中提取选项，转为 A. B. C. D. 格式。
3. 如果是 **short_answer** (解答题/计算题) 或 **fill_in_blank** (填空题)，请将确切结果提取到 `answers` 数组中。
4. 如果是 **proof** (证明题)，请仅生成 `explanation` (解析)，无需 `answers`。
5. 生成详细解析。
6. 所有数学公式请强制使用 $ 或 $$ 包裹，绝对不要使用 \[ \] 或 \( \) 格式，以兼容 Markdown 渲染。
"""
        user_content = f"【题目文本】:\n{source_text}\n\n【题型】: {detected_type}\n"
        if q_correct:
            user_content += f"【用户提供的答案】: {q_correct}\n"
        
        msgs_2 = [{"role": "system", "content": sys_prompt_2}]
        payload_2 = [{"type": "text", "text": user_content}]
        if attachment_b64: # Context image
            payload_2.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{attachment_b64}"}})
        
        msgs_2.append({"role": "user", "content": payload_2}) # type: ignore

        try:
            resp_2 = client.chat.completions.create(
                model=model_name,
                messages=msgs_2, # type: ignore
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            res_2 = json.loads(resp_2.choices[0].message.content)
        except Exception as e:
            print(f"Stage 2 Error: {e}")
            res_2 = {}

        # --- Post-Processing ---
        final_question = q_c if q_c else res_2.get("question", source_text)
        final_explanation = q_e if q_e else res_2.get("explanation", "")
        
        ai_options = res_2.get("options", [])
        
        # Options Logic
        if q_o:
            final_options = q_o
        else:
            if detected_type in ["multiple_choice", "multi_select", "boolean"] and ai_options:
                final_options = "\n".join(ai_options)
            elif detected_type == "fill_in_blank" and ai_options: 
                 final_options = "\n".join(ai_options)
                 detected_type = "multiple_choice"
            elif detected_type == "boolean":
                 # Ensure standard True/False options if missing
                 final_options = "True\nFalse"
            else:
                final_options = ""

        # Helper for mapping various formats to Uppercase Letters
        def _map_to_letter(s):
            s = s.strip()
            mapping = {
                '1': 'A', '１': 'A', 'I': 'A', '甲': 'A', '对': 'T', 'T': 'T', 'True': 'T', 'TRUE': 'T', '√': 'T',
                '2': 'B', '２': 'B', 'II': 'B', '乙': 'B', '错': 'F', 'F': 'F', 'False': 'F', 'FALSE': 'F', '×': 'F',
                '3': 'C', '３': 'C', 'III': 'C', '丙': 'C',
                '4': 'D', '４': 'D', 'IV': 'D', '丁': 'D',
                '5': 'E', '５': 'E', 'V': 'E', '戊': 'E'
            }
            # Special Boolean handling if detected type is boolean
            if detected_type == "boolean":
                if s in ['A', 'T', 't', '1', '对', '√', 'True', 'TRUE']: return "True"
                if s in ['B', 'F', 'f', '0', '错', '×', 'False', 'FALSE']: return "False"
            
            return mapping.get(s, s.upper())

        # Answer Logic
        if q_correct:
            final_correct = q_correct
            # Normalize User MC Answer if single letter or digit
            if detected_type in ["multiple_choice", "boolean"]:
                  # Use standard mapper
                  final_correct = _map_to_letter(final_correct)
        else:
            final_correct = res_2.get("correct_answer", "")
            if detected_type == "fill_in_blank":
                ans_list = res_2.get("answers", [])
                if ans_list:
                    final_options = "FILL_IN_BLANK:" + json.dumps(ans_list, ensure_ascii=False)
                    final_correct = "FILL_IN_BLANK"
                else:
                    final_options = "FILL_IN_BLANK:" + json.dumps([final_correct], ensure_ascii=False)
                    final_correct = "FILL_IN_BLANK"
        
        # Multi-select normalization fallback
        if detected_type == "multi_select" and q_correct:
             cleaned = final_correct.replace('，', ',').replace('|', ',').replace(' ', ',')
             # Check if it looks like "13" (digits string) or just comma separated
             if ',' not in cleaned and len(cleaned) > 1:
                # Treat "13" as "1", "3"
                final_parts = [_map_to_letter(c) for c in cleaned]
             else:
                parts = [p.strip() for p in cleaned.split(',') if p.strip()]
                final_parts = [_map_to_letter(p) for p in parts]
             
             final_correct = ", ".join(sorted(list(set(final_parts)))) # Sort and Dedup

        # Save
        q_data = {
            "question_type": detected_type,
            "question": final_question,
            "options": final_options.split('\n') if final_options and "FILL_IN_BLANK" not in final_options else [],
            "answers": json.loads(final_options[14:]) if final_options and "FILL_IN_BLANK" in final_options else None,
            "correct_answer": final_correct if "FILL_IN_BLANK" not in final_correct else None,
            "explanation": final_explanation
        }
        if attachment_b64: q_data["image"] = attachment_b64
        
        final_summary = res_2.get("summary", final_question[:20])
        question_db.update_question_status(record_id=rid, question_data=q_data, summary=final_summary, status="completed", mistake_book=book_name)
        
    except Exception as e:
        print(f"Process Error: {e}")
        error_msg = str(e)
        if "os" in error_msg: error_msg = "System Error (Import)"
        question_db.update_question_status(record_id=rid, status="failed", mistake_book=book_name)

@st.dialog("重命名错题本", width="small")
def rename_book_dialog(old_name):
    st.markdown(f"✍️ 正在重命名: **{old_name}**")
    new_name = st.text_input("新名称", value=old_name, placeholder="输入新名称...", key=f"rename_val_{old_name}")
    if st.button("💾 保存修改", type="primary", use_container_width=True, key=f"rename_confirm_{old_name}"):
        if new_name and new_name != old_name:
            if question_db.rename_mistake_book(old_name, new_name):
                st.toast(f"✅ 已重命名为 {new_name}")
                time.sleep(0.5)
                st.rerun()
            else: st.error("❌ 重命名失败 (可能名称已存在)")
        else: st.warning("⚠️ 名称未变更")

@st.dialog("�️ 确认删除", width="small")
def delete_book_dialog(book_name):
    st.warning(f"⚠️ 确定要彻底删除错题本 **{book_name}** 吗？\n\n此操作将删除该本中的**所有题目**，且**不可恢复**！")
    col_del_1, col_del_2 = st.columns(2)
    with col_del_1:
         if st.button("🔥 确认删除", type="primary", use_container_width=True, key=f"dialog_confirm_del_{book_name}"):
            if question_db.delete_mistake_book(book_name):
                st.toast("✅ 已删除")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 删除失败")
    with col_del_2:
        if st.button("取消", use_container_width=True, key=f"dialog_cancel_del_{book_name}"):
            st.rerun()

@st.dialog("➕ 新建错题本", width="small")
def create_book_dialog():
    new_book_name = st.text_input("错题本名称", placeholder="例如：数学错题本")
    if st.button("立即创建", type="primary", use_container_width=True, key="dialog_create_book_btn"):
        if new_book_name:
            if question_db.create_mistake_book(new_book_name):
                st.toast(f"✅ 创建成功")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 错题本已存在")
        else:
            st.warning("请输入错题本名称")

@st.dialog("�📓 错题详情与编辑", width="large")
def mistake_detail_dialog(item, book_name, is_archived):
    # 使用 session_state 控制内部模式，避免嵌套 Dialog
    mode_key = f"dialog_mode_{item['id']}"
    # Only initialize if not already set (allows external setting from quiz page)
    current_mode = st.session_state.get(mode_key, "view")
    
    if current_mode == "view":
        # --- VIEW MODE ---
        # Move Buttons to Top
        c_edit, c_arch, c_del = st.columns([1, 1, 1])
        with c_edit:
            def _enter_edit(): st.session_state[mode_key] = "edit"
            st.button("✏️ 编辑", use_container_width=True, key=f"btn_go_edit_{item['id']}", on_click=_enter_edit)
        with c_arch:
            btn_arch_label = "📤 取消归档" if is_archived else "📥 归档"
            if st.button(btn_arch_label, use_container_width=True, key=f"btn_dia_arch_{item['id']}"):
                question_db.toggle_archive(item['id'], mistake_book=book_name)
                # Auto deselect
                if item['id'] in st.session_state.get('selected_questions', set()):
                    st.session_state.selected_questions.discard(item['id'])
                st.toast("操作成功")
                time.sleep(0.5)
                st.rerun()
        with c_del:
            if st.button("🗑️ 删除", use_container_width=True, type="primary", key=f"btn_dia_del_{item['id']}"):
                question_db.remove_wrong_question(item['id'], mistake_book=book_name)
                st.toast("已删除")
                time.sleep(0.5)
                st.rerun()
        
        st.divider()

        q = item["question"]
        st.markdown(f"### 题目")
        if q.get("image"):
            try:
                # Decide if base64 or url (assuming base64 for now as per adder)
                img_data = q.get("image")
                if img_data.startswith("http"):
                    st.image(img_data)
                else:
                    st.image(base64.b64decode(img_data))
            except:
                st.warning("图片加载失败")
                
        display_q = q.get('question', '')
        if not display_q and q.get('image'):
            display_q = "_（此题为纯图片模式，无文字描述）_"
        st.markdown(display_q)
        
        q_type = q.get("question_type", "")
        options = q.get("options", [])
        
        if q_type in ["multiple_choice", "multi_select", "boolean"] or options:
            st.markdown("**选项：**")
            for opt in options:
                st.markdown(f"- {opt}")
            st.success(f"**正确答案：** {q.get('correct_answer')}")
        else:
            st.markdown("**正确答案：**")
            answers = q.get("answers") or []
            if answers:
                for ans in answers:
                    st.markdown(f"- {ans}")
            else:
                st.caption("（无标准答案记录）")
                
        st.markdown(f"### 💡 解析\n\n{q.get('explanation', '暂无解析')}", unsafe_allow_html=True)
        st.divider()
        
        st.divider()
                
    else:
        # --- EDIT MODE ---
        q = item["question"]
        current_type = q.get("question_type", "multiple_choice")
        # Type Selector (Only in Edit Mode)
        st.markdown("#### 修改题型")
        type_opts = {
            "单选题": "multiple_choice",
            "多选题": "multi_select",
            "判断题": "boolean",
            "填空题": "fill_in_blank",
            "解答题": "short_answer",
            "证明题": "proof"
        }
        curr_type_idx = list(type_opts.values()).index(current_type) if current_type in type_opts.values() else 0
        new_type_display = st.radio("题目类型", list(type_opts.keys()), index=curr_type_idx, horizontal=True, label_visibility="collapsed")
        new_type = type_opts[new_type_display]

        new_q = st.text_area("题目内容", value=q.get("question", ""), height=150, key=f"edit_q_{item['id']}")
        
        # Image Edit
        curr_img = q.get("image")
        if curr_img:
            st.markdown("current image:")
            try: st.image(base64.b64decode(curr_img), width=200)
            except: st.text("Image Error")
            if st.button("🗑️ 删除图片", key=f"del_img_{item['id']}"):
                q["image"] = None
                st.rerun()
        
        new_img_file = st.file_uploader("更换/上传图片", type=["png", "jpg", "jpeg"], key=f"up_img_edit_{item['id']}")
        new_img_b64 = curr_img
        if new_img_file:
             new_img_b64 = base64.b64encode(new_img_file.getvalue()).decode('utf-8')
        
        if new_type in ["multiple_choice", "multi_select", "boolean"]:
            # If switching, handle missing options
            options_val = q.get("options", [])
            options_str = "\n".join(options_val) if isinstance(options_val, list) else ""
            
            new_o = st.text_area("选项 (每行一个)", value=options_str, height=120, key=f"edit_o_{item['id']}")
            new_a = st.text_input("正确答案", value=q.get("correct_answer", ""), key=f"edit_a_{item['id']}", help="多选题答案可用逗号或空格分隔")
            new_data = {
                "question_type": new_type,
                "question": new_q,
                "options": [o.strip() for o in new_o.split("\n") if o.strip()],
                "correct_answer": new_a.strip(),
                "explanation": st.text_area("解析", value=q.get("explanation", ""), height=150, key=f"edit_e_{item['id']}")
            }
        elif new_type in ["fill_in_blank", "short_answer"]:
            answers_val = q.get("answers") or []
            if not answers_val and q.get("correct_answer"): answers_val = [q.get("correct_answer")]
            answers_str = "\n".join(answers_val) if isinstance(answers_val, list) else ""
            
            new_ans = st.text_area("正确答案 (每行一个，同一空多个可能答案用 | 分隔)", value=answers_str, height=120, key=f"edit_ans_{item['id']}")
            new_data = {
                "question_type": new_type,
                "question": new_q,
                "answers": [a.strip() for a in new_ans.split("\n") if a.strip()],
                "explanation": st.text_area("解析", value=q.get("explanation", ""), height=150, key=f"edit_e_blank_{item['id']}")
            }
        else: # Proof
            new_data = {
                "question_type": "proof",
                "question": new_q,
                "explanation": st.text_area("解析与证明过程", value=q.get("explanation", ""), height=200, key=f"edit_proof_e_{item['id']}")
            }
        
        if new_img_b64:
            new_data["image"] = new_img_b64
        
        # Familiarity Score Editing
        st.divider()
        current_score = item.get("familiarity_score", 2)
        new_score = st.slider("📊 陌生度", min_value=0, max_value=5, value=current_score, key=f"edit_score_{item['id']}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 保存修改", type="primary", use_container_width=True, key=f"btn_save_edit_{item['id']}"):
                question_db.update_question_status(record_id=item["id"], question_data=new_data, summary=new_q[:20], status="completed", mistake_book=book_name)
                # Update familiarity score if changed
                if new_score != current_score:
                    question_db.set_familiarity_score(item['id'], new_score, book_name)
                
                st.toast("✅ 修改已保存")
                
                # Check for Return to Quiz
                if st.session_state.get("return_to_quiz"):
                     st.session_state.mistake_mode = "quiz"
                     st.session_state.active_dialog_id = None
                     st.session_state.active_dialog_type = None
                     del st.session_state["return_to_quiz"]
                     time.sleep(0.5); st.rerun()
                else:
                    st.session_state[mode_key] = "view"
                    time.sleep(0.5); st.rerun()
                    
        with c2:
            if st.button("❌ 取消", use_container_width=True, key=f"btn_cancel_edit_{item['id']}"):
                if st.session_state.get("return_to_quiz"):
                     st.session_state.mistake_mode = "quiz"
                     st.session_state.active_dialog_id = None
                     del st.session_state["return_to_quiz"]
                     st.rerun()
                else:
                     st.session_state[mode_key] = "view"
                     st.rerun()
                
    st.divider()
    if st.button("❌ 关闭", use_container_width=True, key=f"btn_close_dlg_{item['id']}"):
        st.session_state.active_dialog_id = None
        st.rerun()

@st.dialog("📚 批量已选详情", width="large")
def batch_view_dialog(items):
    st.markdown(f"### 已选择 {len(items)} 道题目")
    st.divider()
    
    for i, item in enumerate(items):
        q = item["question"]
        st.markdown(f"#### 题目 {i+1}")
        
        # Batch View Image Support
        if q.get("image"):
             try:
                b_img = q.get("image")
                if b_img.startswith("http"): st.image(b_img, width=300)
                else: st.image(base64.b64decode(b_img), width=300)
             except: st.error("图片加载错")

        st.info(q.get("question", "（无内容）"))
        
        options = q.get("options", [])
        if func_q_type := q.get("question_type", "") == "multiple_choice" or options:
            st.markdown("**选项：**")
            for opt in options:
                st.markdown(f"- {opt}")

        with st.expander("查看答案与解析", expanded=True):
            q_type = q.get("question_type", "")
            if q_type == "multiple_choice":
                st.markdown(f"**正确选项：** {q.get('correct_answer')}")
            else:
                st.markdown("**正确答案：**")
                answers = q.get("answers") or []
                for ans in answers: st.markdown(f"- {ans}", unsafe_allow_html=True)
            st.markdown(f"**解析：**\n\n{q.get('explanation', '暂无解析')}", unsafe_allow_html=True)
        st.divider()
        
    if st.button("❌ 关闭所有", use_container_width=True, key="btn_close_batch_view"):
        st.session_state.active_dialog_id = None
        st.session_state.active_dialog_type = None
        st.rerun()

@st.dialog("➕ 添加错题", width="large")
def add_mistake_dialog(selected_book):
    # Custom CSS to center file uploaders and adjust layout
    st.markdown("""
    <style>
    /* File Uploader 200px Height & Centering */
    div[data-testid="stFileUploader"] label { width: 100%; text-align: center; }
    div[data-testid="stFileUploader"] button { margin: 0 auto; display: block; }
    section[data-testid="stFileUploaderDropzone"] { 
        min-height: 171.5px !important; 
        height: 171.5px !important;
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
    }
    /* Checkbox optical adjustment */
    div[data-testid="stCheckbox"] { transform: translateY(-2px); }
    </style>
    """, unsafe_allow_html=True)

    st.info("💡 上传图片或输入文本，系统将自动填充空白部分（答案、解析等）。")
    # Only show unarchived books for adding new mistakes
    books = question_db.list_mistake_books(include_archived=False)
    target = st.selectbox("📚 目标错题本", books, index=books.index(selected_book) if selected_book in books else 0)
    
    # Row 1: Images, Question, Options
    c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
    with c1:
        u_ocr = st.file_uploader("📸 识别源", type=["jpg", "png", "jpeg"], key="u_ocr_new")
    with c2:
        u_fig = st.file_uploader("🖼️ 配图", type=["jpg", "png", "jpeg"], key="u_fig_new")
    with c3:
        q_c = st.text_area("题目内容", placeholder="输入题目...", height=200)
    with c4:
        q_o = st.text_area("选项 (可选)", placeholder="A. B. C. D.", height=200)
    
    # Row 2: Answer, Explanation
    c5, c6 = st.columns([1, 5])
    with c5:
        q_a = st.text_area("正确答案", placeholder="例如：A\n填空用逗号分隔", height=200)
    with c6:
        q_e = st.text_area("解析 (可选)", placeholder="由 AI 自动生成...", height=200)
    
    if st.button("智能识别并添加", type="primary", use_container_width=True):
        if u_ocr or u_fig or q_c:
            i_q = q_c if q_c else "（正在识别中...）"
            
            # Normalize answer separators: Support both half-width and full-width
            normalized_answer = q_a.replace('｜', '|').replace('，', ',') if q_a else ""
            
            i_d = {"question": i_q, "explanation": q_e if q_e else "（处理中...）"}
            
            ocr_b64 = base64.b64encode(u_ocr.getvalue()).decode('utf-8') if u_ocr else None
            fig_b64 = base64.b64encode(u_fig.getvalue()).decode('utf-8') if u_fig else None
            
            # Request 1: Only use figure if explicitly provided (No fallback to OCR)
            final_attachment = fig_b64 
            
            # Initial placeholder
            rid = question_db.add_result(
                kb_name=st.session_state.get("selected_kb", "default"), # Placeholder
                question_data=i_d,
                user_answer="（手动添加）",
                is_correct=False,
                summary=i_q[:20],
                mistake_book=target
            )
            
            # Auto detection mode (None)
            f_type = None 
            
            # Pass normalized answer to backend
            threading.Thread(target=process_question_async, args=(rid, target, q_c, q_o, normalized_answer, q_e, ocr_b64, final_attachment, f_type), daemon=True).start()
            st.session_state.active_dialog_type = None  # Clear dialog state
            st.success("✅ 已添加，正在处理..."); time.sleep(1.0); st.rerun()
        else: st.error("请提供内容或图片")

# ========== 错题本列表页面 ==========
if st.session_state.view_mode == "list":
    st.title("📓 错题本管理")
    st.markdown("### 选择一个错题本开始管理错题")
    
    # 获取所有错题本 (with archive status)
    all_books = question_db.list_mistake_books(include_archived=True)
    
    # 新建错题本按钮 + 显示已归档切换
    col_manage1, col_manage2, col_manage3 = st.columns([1, 1, 3])
    with col_manage1:
        # Use button + dialog for consistency with other actions
        if st.button("➕ 新建错题本", use_container_width=True):
            create_book_dialog()
    
    with col_manage2:
        # Use a button to toggle archive view instead of st.toggle
        if "show_archived_books" not in st.session_state:
            st.session_state.show_archived_books = False
            
        btn_label = "� 查看未归档" if st.session_state.show_archived_books else "📦 查看已归档"
        # Use secondary type for toggle
        if st.button(btn_label, use_container_width=True):
            st.session_state.show_archived_books = not st.session_state.show_archived_books
            st.rerun()
            
    show_archived = st.session_state.show_archived_books
    
    st.markdown("---")
    
    # 根据切换过滤错题本
    if show_archived:
        # Show only archived books
        display_books = [(name, True) for name, is_archived in all_books if is_archived]
        if not display_books:
            st.info("📦 没有已归档的错题本")
    else:
        # Show only unarchived books
        display_books = [(name, False) for name, is_archived in all_books if not is_archived]
    
    # 显示错题本卡片
    if not display_books:
        if not show_archived:
            st.info("还没有错题本，点击上方按钮创建一个吧！")
    else:
        # Grid Layout: 3 cards per row
        for i in range(0, len(display_books), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(display_books):
                    book_name, is_archived = display_books[i + j]
                    with cols[j]:
                        # 卡片容器
                        with st.container(border=True):
                            # Row 1: Title with archive indicator
                            icon = "📦" if is_archived else "📓"
                            st.markdown(f"<div style='text-align: center; font-size: 1.25rem; margin-bottom: 5px;'><b>{icon} {book_name}</b></div>", unsafe_allow_html=True)
        
                            # Row 2: Statistics
                            questions = question_db.get_wrong_questions(mistake_book=book_name)
                            active_count = len([q for q in questions if not q.get("archived", False)])
                            archived_count = len([q for q in questions if q.get("archived", False)])
                            st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.85rem; margin-bottom: 12px;'>📝 未归档: <b>{active_count}</b> &nbsp;|&nbsp; 📦 已归档: <b>{archived_count}</b></div>", unsafe_allow_html=True)
                            
                            st.divider()
                            
                            if not is_archived:
                                # --- UNARCHIVED BOOK BUTTONS ---
                                # Row 3: Enter, Practice
                                c_enter, c_quiz = st.columns(2)
                                with c_enter:
                                    if st.button("进入错题本", key=f"enter_{book_name}", use_container_width=True):
                                        st.session_state.selected_mistake_book = book_name
                                        st.session_state.view_mode = "detail"
                                        st.session_state.mistake_mode = "list"
                                        st.session_state.active_dialog_id = None # Reset dialog
                                        st.session_state.active_dialog_type = None
                                        st.rerun()
                                with c_quiz:
                                    if st.button("错题练习", key=f"review_{book_name}", use_container_width=True):
                                        st.session_state.selected_mistake_book = book_name
                                        st.session_state.view_mode = "detail"
                                        st.session_state.mistake_mode = "quiz"
                                        st.session_state.mistake_index = 0
                                        _all = question_db.get_wrong_questions(mistake_book=book_name)
                                        _active = [q for q in _all if not q.get("archived", False)]
                                        _active = _active[::-1] 
                                        st.session_state.quiz_ids = [q['id'] for q in _active]
                                        for k in list(st.session_state.keys()):
                                            if k.startswith(("mistake_answered_", "mistake_blanks_", "mq_radio_", "score_res_")):
                                                del st.session_state[k]
                                        st.rerun()
            
                                # Row 4: Rename, Archive
                                c_ren, c_arch = st.columns(2)
                                with c_ren:
                                    if st.button("📝 重命名", key=f"pre_ren_{book_name}", use_container_width=True):
                                        rename_book_dialog(book_name)
                                with c_arch:
                                    if st.button("📥 归档", key=f"arch_{book_name}", use_container_width=True):
                                        question_db.toggle_book_archive(book_name)
                                        st.toast(f"已归档: {book_name}")
                                        time.sleep(0.5)
                                        st.rerun()
                            else:
                                # --- ARCHIVED BOOK BUTTONS ---
                                # Row 3: Enter, Delete
                                c_enter, c_del = st.columns(2)
                                with c_enter:
                                    if st.button("进入错题本", key=f"enter_{book_name}", use_container_width=True):
                                        st.session_state.selected_mistake_book = book_name
                                        st.session_state.view_mode = "detail"
                                        st.session_state.mistake_mode = "list"
                                        st.session_state.active_dialog_id = None # Reset
                                        st.session_state.active_dialog_type = None
                                        st.rerun()
                                with c_del:
                                    if st.button("🗑️ 删除", key=f"pre_del_{book_name}", use_container_width=True):
                                        delete_book_dialog(book_name)
            
                                # Row 4: Rename, Unarchive
                                c_ren, c_unarch = st.columns(2)
                                with c_ren:
                                    if st.button("📝 重命名", key=f"pre_ren_{book_name}", use_container_width=True):
                                        rename_book_dialog(book_name)
                                with c_unarch:
                                    if st.button("📤 移出归档", key=f"unarch_{book_name}", use_container_width=True):
                                        question_db.toggle_book_archive(book_name)
                                        st.toast(f"已取消归档: {book_name}")
                                        time.sleep(0.5)
                                        st.rerun()

# ========== 错题详情页面 ==========
elif st.session_state.view_mode == "detail":
    # 非复习模式下显示 Header
    if st.session_state.mistake_mode != "quiz":
        # Row 1: Back Button
        if st.button("⬅️ 返回", type="secondary"):
            st.session_state.view_mode = "list"
            st.rerun()
        
        # Row 2: Title and Stats
        selected_book = st.session_state.selected_mistake_book
        # 获取错题数据用于统计
        wrong_questions = question_db.get_wrong_questions(mistake_book=selected_book)
        st.markdown(f"#### 📚 当前错题本：{selected_book} | 共 {len(wrong_questions)} 道错题")
    else:
        selected_book = st.session_state.selected_mistake_book
        wrong_questions = question_db.get_wrong_questions(mistake_book=selected_book)
    
    # 检查是否有处理中的题目
    has_processing = False
    if wrong_questions:
        has_processing = any(item.get("status", "completed") == "processing" for item in wrong_questions)

    if wrong_questions:
        has_processing = any(item.get("status", "completed") == "processing" for item in wrong_questions)

# Callbacks for Batch Actions (Defined here to access closure variables effectively if needed, 
# or use st.session_state)
def cb_ba_select_all():
    # Need access to 'cur_list' - we can store IDs in session state or just grab all from DB?
    # Better: The button will execute this. We can pull from session state if we stored the view list?
    # Actually, simplistic approach: Do logic here. BUT 'cur_list' is local.
    # Hack: passing args to callback
    pass 

def cb_ba_cancel():
    for qid in st.session_state.get('selected_questions', []):
        if f"it_chk_{qid}" in st.session_state:
             st.session_state[f"it_chk_{qid}"] = False
    st.session_state.selected_questions = set()
    st.session_state.active_dialog_id = None
    st.session_state.active_dialog_type = None

def cb_ba_archive(sel_qs_arg, book_arg):
    for qid in sel_qs_arg: 
        question_db.toggle_archive(qid, mistake_book=book_arg)
    st.session_state.selected_questions = set()
    st.session_state.active_dialog_id = None
    st.session_state.active_dialog_type = None
    # Cannot toast here easily without rerun context? callbacks run before render. Toast works.
    
def cb_ba_expand():
    st.session_state.active_dialog_id = "batch_view"
    st.session_state.active_dialog_type = "batch"

# --- Mode: List View ---
# --- Mode: List View ---
if st.session_state.view_mode == "detail" and st.session_state.mistake_mode == "list":
    # CSS for List Item Checkbox Alignment
    st.markdown("""<style>div[data-testid="stCheckbox"] { transform: translateY(-2px); }</style>""", unsafe_allow_html=True)

    # Check for active dialog triggers
    active_type = st.session_state.get('active_dialog_type')
    active_id = st.session_state.get('active_dialog_id')
    
    # Simple dispatcher based on Type
    if active_type == "add":
        add_mistake_dialog(selected_book)
        
    elif active_type == "batch" and active_id == "batch_view":
        # Batch View Mode
        sel_qs = st.session_state.get('selected_questions', set())
        cur_all_qs = question_db.get_wrong_questions(mistake_book=selected_book)
        _selected_items = [q for q in cur_all_qs if q['id'] in sel_qs]
        if _selected_items:
            batch_view_dialog(_selected_items)
        else:
            st.session_state.active_dialog_id = None
            st.session_state.active_dialog_type = None
            st.rerun()
            
    elif active_id: # Default to single if ID exists and type is None or 'single'
         # Single Detail Mode
        target_item = next((q for q in wrong_questions if q['id'] == active_id), None)
        if target_item:
            v_arch = st.session_state.get("view_archived", False)
            mistake_detail_dialog(target_item, selected_book, v_arch)
        else:
            # Item might have been deleted
            st.session_state.active_dialog_id = None
            st.rerun()
            
    # 如果有处理中的题目，显示提示和刷新按钮
    if has_processing:
        col_info, col_refresh = st.columns([3, 1])
        with col_info:
            st.info("⏳ 检测到有题目正在后台处理中，请稍候...")
        with col_refresh:
            if st.button("🔄 刷新状态", key="refresh_processing_top"):
                st.rerun()
    
    # 获取归档错题数量
    archived_questions = question_db.get_archived_questions(mistake_book=selected_book)
    archived_count = len(archived_questions)
    
    # 如果错题本为空，显示提示信息
    if not wrong_questions:
        st.info(f"🎉 太棒了！错题本「{selected_book}」是空的。可以手动添加错题或去【做题练习】！")
        if archived_count > 0:
            st.info(f"📦 该错题本有 {archived_count} 道已归档的题目")
        if st.button("前往做题练习", type="primary", key="go_quiz_empty_main"):
            st.switch_page("pages/2_📝_做题练习.py")
        st.markdown("---")

    else:
        st.markdown(f"### 共 {len(wrong_questions)} 道错题")
        # Row 3: Control Buttons (Same style/size)
        c_r3_1, c_r3_2, c_r3_3, c_r3_4 = st.columns(4)
        with c_r3_1:
            if st.button("错题练习", use_container_width=True, key="tb_quiz"):
                st.session_state.mistake_mode = "quiz"; st.session_state.mistake_index = 0
                st.session_state.active_dialog_id = None  # Clear dialog state
                
                # Initialize Quiz Queue
                _all = question_db.get_wrong_questions(mistake_book=selected_book)
                _active = [q for q in _all if not q.get("archived", False)]
                
                # Apply current sort order
                s_opt = st.session_state.get("quiz_sort_order", "📅 添加时间(最新)")
                if s_opt == "📅 添加时间(最新)": _active = _active[::-1]
                elif s_opt == "🔥 陌生度(高→低)": _active.sort(key=lambda x: x.get("familiarity_score", 0), reverse=True)
                elif s_opt == "✨ 陌生度(低→高)": _active.sort(key=lambda x: x.get("familiarity_score", 0))
                
                st.session_state.quiz_ids = [q['id'] for q in _active]
                
                # Reset quiz states
                for k in list(st.session_state.keys()):
                    if k.startswith(("mistake_answered_", "mistake_blanks_", "mq_radio_", "score_res_")):
                        del st.session_state[k]
                st.rerun()
        with c_r3_2:
            sort_modes = ["📅 时间(最新)", "📅 时间(最早)", "🔥 陌生(高→低)", "✨ 陌生(低→高)"]
            if "sort_idx" not in st.session_state: st.session_state.sort_idx = 0
            if st.button(f"🔄 顺序: {sort_modes[st.session_state.sort_idx]}", use_container_width=True, key="tb_sort"):
                st.session_state.active_dialog_id = None  # Clear dialog state
                st.session_state.sort_idx = (st.session_state.sort_idx + 1) % len(sort_modes)
                st.session_state.quiz_sort_order = ["📅 添加时间(最新)", "📅 添加时间(最早)", "🔥 陌生度(高→低)", "✨ 陌生度(低→高)"][st.session_state.sort_idx]
                st.rerun()
        with c_r3_3:
            v_arch = st.session_state.get("view_archived", False)
            if st.button("📦 查看归档" if not v_arch else "🔙 查看未归档", use_container_width=True, key="tb_arch"):
                st.session_state.view_archived = not v_arch; st.session_state.selected_questions = set(); 
                st.session_state.active_dialog_id = None # Clear dialog
                st.rerun()
        with c_r3_4:
            if st.session_state.get("view_archived", False):
                # Archive View: Show Delete Selected
                 if st.button("🗑️ 删除选中", use_container_width=True, key="tb_del_multi"):
                    sel = st.session_state.get("selected_questions", set())
                    if not sel:
                        st.toast("⚠️ 请先勾选要删除的题目")
                    else:
                        for qid in list(sel):
                            question_db.remove_wrong_question(qid, mistake_book=selected_book)
                        st.session_state.selected_questions = set()
                        st.success(f"已删除 {len(sel)} 道题目")
                        time.sleep(1.0)
                        st.rerun()
            else:
                # Normal View: Show Add Mistake
                if st.button("➕ 添加错题", use_container_width=True, key="tb_add"): 
                    st.session_state.active_dialog_id = None 
                    st.session_state.active_dialog_type = "add"
                    st.rerun() 


        # Row 4: Batch Actions (Below, same style/size)
        c_r4_1, c_r4_2, c_r4_3, c_r4_4 = st.columns(4)
        if v_arch: cur_list = [q for q in wrong_questions if q.get("archived", False)]
        else: cur_list = [q for q in wrong_questions if not q.get("archived", False)]
        
        sel_qs = st.session_state.get('selected_questions', set())
        sel_cnt = len(sel_qs)
        
        with c_r4_1:
            if st.button("✅ 全选", use_container_width=True, key="ba_all"):
                # Handle Select All directly
                all_ids = {it["id"] for it in cur_list if it.get("status") != "processing"}
                st.session_state.selected_questions = all_ids
                for qid in all_ids:
                    st.session_state[f"it_chk_{qid}"] = True
                st.session_state.active_dialog_id = None
                st.session_state.active_dialog_type = None
                st.rerun()
                
        with c_r4_2:
            if st.button("❌ 取消", use_container_width=True, key="ba_none", on_click=cb_ba_cancel):
                pass
                
        with c_r4_3:
            v_arch = st.session_state.get("view_archived", False)
            btn_l = f"📤 批量恢复 ({sel_cnt})" if v_arch and sel_cnt > 0 else (f"📥 批量归档 ({sel_cnt})" if sel_cnt > 0 else "📥 批量归档")
            
            # Using on_click for archive to prevent reload race
            if st.button(btn_l, use_container_width=True, disabled=(sel_cnt == 0), key="ba_arch"): 
                 cb_ba_archive(sel_qs, selected_book) # Direct call or on_click? 
                 # Direct block execution is safer for 'args'.
                 # Let's keep block but ensure state is cleared.
                 st.rerun()

        with c_r4_4:
            btn_exp_label = f"📖 展开选中 ({sel_cnt})" if sel_cnt > 0 else "📖 展开选中"
            if st.button(btn_exp_label, use_container_width=True, disabled=(sel_cnt == 0), key="ba_exp", on_click=cb_ba_expand):
                pass
        
        st.divider()

        # Final Filtering & Rendering
        if wrong_questions:
            v_arch = st.session_state.get("view_archived", False)
            if v_arch: cur_list = [q for q in wrong_questions if q.get("archived", False)]
            else: cur_list = [q for q in wrong_questions if not q.get("archived", False)]
            s_opt = st.session_state.get("quiz_sort_order", "📅 添加时间(最新)")
            if s_opt == "📅 添加时间(最新)": cur_list = cur_list[::-1]
            elif s_opt == "🔥 陌生度(高→低)": cur_list.sort(key=lambda x: x.get("familiarity_score", 0), reverse=True)
            elif s_opt == "✨ 陌生度(低→高)": cur_list.sort(key=lambda x: x.get("familiarity_score", 0))
            
            if not cur_list:
                st.info("暂无归档题目" if v_arch else "暂无待复习题目")
            else:
                for i, item in enumerate(cur_list):
                    with st.container(border=True):
                        q = item["question"]
                        question_text = q.get('question', "（未知题目）")
                        status = item.get("status", "completed")
                        is_processing = status == "processing"
                        
                        if not question_text and q.get("image"):
                            question_text = "（🖼️ 图片题目）"
                        elif not question_text:
                            question_text = "（📝 无内容）"
                        
                        summary_text = item.get("summary") or (question_text[:25] + "..." if len(question_text) > 25 else question_text)
                        if is_processing: summary_text = f"⏳ 处理中... {summary_text}"
                        
                        # Layout: Checkbox | Question Summary | Score | Details Button
                        c_check, c_summ, c_score, c_btn = st.columns([0.05, 0.78, 0.05, 0.12], vertical_alignment="center")
                        
                        selected_ids = st.session_state.get('selected_questions', set())
                        is_checked = item["id"] in selected_ids
                        
                        with c_check:
                            chk_key = f"it_chk_{item['id']}"
                            # Sync session state with external source of truth (selected_questions)
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = is_checked
                            elif st.session_state[chk_key] != is_checked:
                                st.session_state[chk_key] = is_checked
                                
                            def _on_check_change(k=chk_key, iid=item["id"]):
                                if st.session_state[k]:
                                    st.session_state.selected_questions.add(iid)
                                else:
                                    st.session_state.selected_questions.discard(iid)
                                    
                            st.checkbox(
                                f"选择题目 {item['id']}", 
                                key=chk_key, 
                                label_visibility="collapsed", 
                                disabled=is_processing,
                                on_change=_on_check_change
                            )
                        
                        with c_summ:
                            # Use plain Markdown to ensure ** and LaTeX are parsed correctly
                            # Vertical alignment is handled by st.columns(..., vertical_alignment="center")
                            st.markdown(f"**{i+1}.** {summary_text}")
                        
                        with c_score:
                            f_score = item.get("familiarity_score", 2)
                            # 使用 st.markdown 保持一致，CSS会处理对齐
                            st.markdown(f"{f_score}")
                            
                        with c_btn:
                            if st.button("🔍 详情", key=f"view_det_{item['id']}", use_container_width=True):
                                st.session_state.active_dialog_id = item["id"]
                                st.session_state.active_dialog_type = "single"
                                st.rerun()

# --- Mode: Quiz View ---
elif st.session_state.view_mode == "detail" and st.session_state.mistake_mode == "quiz":
    # Ensure queue exists
    if "quiz_ids" not in st.session_state:
        st.session_state.mistake_mode = "list"
        st.rerun()
        
    quiz_ids = st.session_state.quiz_ids
    
    if not quiz_ids:
        st.success("🎉 复习完成！暂无待复习题目。")
        if st.button("⬅️ 返回列表", type="primary"):
            st.session_state.mistake_mode = "list"
            st.rerun()
        st.stop()
        
    # Ensure index is valid
    if st.session_state.mistake_index >= len(quiz_ids):
        st.session_state.mistake_index = 0
        
    idx = st.session_state.mistake_index
    current_qid = quiz_ids[idx]
    
    # Fetch fresh data for this ID
    # Use optimized fetch if possible, here filtering list
    all_qs = question_db.get_wrong_questions(mistake_book=st.session_state.selected_mistake_book)
    item = next((q for q in all_qs if q['id'] == current_qid), None)
    
    if not item:
        # Item might be deleted? Skip
        if len(quiz_ids) > 1:
            st.session_state.quiz_ids.pop(idx)
            st.rerun()
        else:
            st.session_state.mistake_mode = "list"
            st.rerun()
        st.stop()

    q = item["question"]
    
    # Back Button
    if st.button("⬅️ 中止练习", type="secondary", key="quiz_back_btn"):
        st.session_state.mistake_mode = "list"
        st.session_state.active_dialog_id = None # Clear any potential dialog ID
        st.rerun()
        
    # Header Area: Progress and Score
    c_p1, c_p2 = st.columns([4, 1])
    # Header Area: Progress and Score
    c_p1, c_p2 = st.columns([4, 1])
    with c_p1:
        st.progress((idx + 1) / len(quiz_ids))
        st.caption(f"当前进度: {idx + 1} / {len(quiz_ids)}")
    with c_p2:
        st.metric("陌生度", item.get("familiarity_score", 2))
    
    st.divider()
    
    # Question Body
    if q.get("image"):
        try:
             quiz_img = q.get("image")
             if quiz_img.startswith("http"): st.image(quiz_img)
             else: st.image(base64.b64decode(quiz_img))
        except: st.warning("图片加载失败")

    q_text = q.get('question', '')
    if not q_text and q.get("image"): q_text = "（请参考图片作答）"
    elif not q_text: q_text = "（题目内容为空）"
    
    st.markdown(f"#### {q_text}")
    
    # State for current question feedback
    answered_key = f"mistake_answered_{item['id']}"
    if answered_key not in st.session_state:
        st.session_state[answered_key] = False
    
    answered = st.session_state[answered_key]
    question_type = q.get("question_type", "multiple_choice")
    
    # Input Area
    if question_type in ["fill_in_blank", "short_answer"]:
        answers = q.get("answers") or []
        num_blanks = len(answers)
        if f"mistake_blanks_{item['id']}" not in st.session_state:
            st.session_state[f"mistake_blanks_{item['id']}"] = [""] * num_blanks
            
        if not answered:
            user_inputs = []
            for i in range(num_blanks):
                val = st.text_input(f"空格 {i+1}", key=f"mq_blank_{item['id']}_{i}")
                user_inputs.append(val)
            
            if st.button("提交答案", type="primary", use_container_width=True):
                st.session_state[f"mistake_blanks_{item['id']}"] = user_inputs
                # Updated logic to support multiple potential answers separated by | or ｜
                correct_count = 0
                for u, a_str in zip(user_inputs, answers):
                    # Normalize full-width pipe to half-width
                    normalized_a = a_str.replace('｜', '|')
                    valid_ans = [cand.strip().lower() for cand in normalized_a.split('|')]
                    if u.strip().lower() in valid_ans:
                        correct_count += 1
                
                is_correct = (correct_count == num_blanks)
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
        else:
            st.markdown("**你的答案：**")
            cols_ans = st.columns(num_blanks)
            for i, val in enumerate(st.session_state[f"mistake_blanks_{item['id']}"]):
                cols_ans[i].info(f"空格 {i+1}: {val}")
    
    elif question_type == "proof":
        if not answered:
            st.info("📝 证明题/简答题请先自行在草稿本完成，完成后点击下方按钮查看标准答案并自评。")
            if st.button("完成练习，查看解析", type="primary", use_container_width=True):
                st.session_state[answered_key] = "eval" # Intermediate state
                st.rerun()
        elif st.session_state[answered_key] == "eval":
            st.warning("🧐 请根据下方解析对自己的作答进行评估：")
            c_yes, c_no = st.columns(2)
            if c_yes.button("✅ 我做对了", use_container_width=True, type="primary"):
                is_correct = True
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
            if c_no.button("❌ 我做错了 / 有误", use_container_width=True):
                is_correct = False
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
    
    elif question_type == "multi_select":
        options = q.get("options", [])
        if not answered:
            st.write("请勾选所有正确选项：")
            # Initialize or retrieve selected options from session state
            if f"mq_multi_selected_{item['id']}" not in st.session_state:
                st.session_state[f"mq_multi_selected_{item['id']}"] = []

            current_selected_opts = []
            for idx, opt in enumerate(options):
                # Use a unique key for each checkbox
                is_checked = opt in st.session_state[f"mq_multi_selected_{item['id']}"]
                if st.checkbox(opt, value=is_checked, key=f"quiz_check_{item['id']}_{idx}"):
                    current_selected_opts.append(opt)
            
            # Update session state with current selections
            st.session_state[f"mq_multi_selected_{item['id']}"] = current_selected_opts
            selected_opts = current_selected_opts # Fix NameError for submit logic

            if st.button("提交答案", type="primary", use_container_width=True):
                # Matching logic for multi-select
                def extract_option_key(s):
                    if not s: return ""
                    s = s.strip()
                    # Check for "A. " pattern
                    if len(s) >= 2 and s[0].isalpha() and s[1] in [".", "、", " "]: return s[0].upper()
                    # Check for "1. " pattern (if mapped options) but options usually A-D normalized
                    return s
                
                # User's selected keys (e.g. ['A', 'C'])
                user_keys = set(extract_option_key(o) for o in selected_opts)
                
                # Correct keys
                # correct_answer is like "A, C" or "A C"
                correct_str = q.get('correct_answer', '').replace(',', ' ').upper()
                correct_keys = set(c.strip() for c in correct_str.split() if c.strip())
                
                is_correct = (user_keys == correct_keys)
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
        else:
            sel_vals = st.session_state.get(f"mq_multi_{item['id']}", [])
            st.info(f"**你的答案：** {', '.join(sel_vals) if sel_vals else '未选择'}")

    else: # multiple_choice or boolean
        options = q.get("options", [])
        if not answered:
            # 强化 Radio 的稳定性：显式指定 key
            selected_opt = st.radio("选择答案：", options, index=None, key=f"mq_radio_real_{item['id']}")
            
            if st.button("提交答案", type="primary", use_container_width=True, key=f"btn_sub_quiz_{item['id']}"):
                # 获取最新的 radio 状态
                actual_sel = st.session_state.get(f"mq_radio_real_{item['id']}")
                if actual_sel:
                    # Extract Key Logic for Comparison
                    def extract_option_key(s):
                        s = str(s).strip()
                        # Standard "A. Content"
                        if len(s) >= 2 and s[0].isalpha() and s[1] in [".", "、", " "]: return s[0].upper()
                        return s.strip()
                    
                    user_key = extract_option_key(actual_sel)
                    correct_key = str(q.get('correct_answer')).strip()
                    
                    is_correct = (user_key.upper() == correct_key.upper()) or (actual_sel.strip() == correct_key)
                    
                    old_score = item.get("familiarity_score", 2)
                    new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                    st.session_state[answered_key] = True
                    st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                    st.rerun()
                else:
                    st.warning("请在提交前先选择一个选项")
        else:
            sel_val = st.session_state.get(f"mq_radio_real_{item['id']}", '未选择')
            st.info(f"**你的答案：** {sel_val}")

    # Result and Navigation Area (After Answered)
    if answered:
        res = st.session_state.get(f"score_res_{item['id']}")
        if res:
            is_correct, old_score, new_score, archived = res
            arrow = "↘️" if new_score < old_score else ("↗️" if new_score > old_score else "➡️")
            score_txt = f" (陌生度: {old_score} {arrow} {new_score}{', 已自动归档' if archived else ''})"
            
            if is_correct: st.success(f"✅ 回答正确！{score_txt}")
            else: st.error(f"❌ 回答错误！{score_txt}")
        
        st.divider()
        
        # Actions Row
        st.divider()
        
        # Actions Row
        c_nav, c_arch = st.columns(2)
        is_last = (idx + 1) >= len(quiz_ids)
        btn_next_label = "✅ 完成复习" if is_last else "➡️ 下一题"
        
        with c_nav:
            if st.button(btn_next_label, type="primary", use_container_width=True):
                if is_last:
                    st.session_state.mistake_mode = "list"
                    st.session_state.active_dialog_id = None # Clear dialog
                else:
                    st.session_state.mistake_index += 1
                st.rerun()
        
        with c_arch:
            new_is_archived = item.get("archived", False)
            arc_label = "📤 取消归档" if new_is_archived else "📥 归档此题"
            
            if st.button(arc_label, use_container_width=True, key=f"btn_quiz_arc_{item['id']}"):
                question_db.toggle_archive(item['id'], mistake_book=st.session_state.selected_mistake_book)
                st.rerun()
                
        # Report/Edit Feature in Post-Quiz
        def _go_to_edit_from_quiz():
            st.session_state.active_dialog_id = item["id"]
            st.session_state.active_dialog_type = "single"
            st.session_state[f"dialog_mode_{item['id']}"] = "edit"
            st.session_state.mistake_mode = "list" # Switch to list mode to show dialog
            st.session_state.return_to_quiz = True # Set flag to return
            
        st.button("🛠️ 题目/答案有误？点击修改", use_container_width=True, key=f"btn_quiz_err_{item['id']}", on_click=_go_to_edit_from_quiz)
        
        # Explanation Area
        with st.container(border=True):
            st.markdown("### 📝 详解")
            if question_type in ["multiple_choice", "multi_select", "boolean"]:
                st.markdown(f"**正确选项：** {q.get('correct_answer')}")
            else:
                st.markdown("**正确答案：**")
                ans_list = q.get("answers") or []
                if ans_list:
                    for ans in ans_list: st.markdown(f"- {ans}")
                else:
                    st.markdown(f"- {q.get('correct_answer', '（空）')}")
            st.info(q.get("explanation", "暂无解析"))

