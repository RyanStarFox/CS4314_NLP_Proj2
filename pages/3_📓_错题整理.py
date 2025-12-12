import streamlit as st
import time
import json
import threading
import base64
from question_db import QuestionDB
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_API_BASE, VL_MODEL_NAME, MODEL_NAME

st.set_page_config(page_title="错题整理", page_icon="logo.webp", layout="wide")

st.markdown("""
<style>
    .stButton button {
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📓 错题整理")

question_db = QuestionDB() # 重新添加初始化
st.markdown("### 📚 错题本选择与管理") # 新增：共同标题
col1, col2 = st.columns([3, 1])
with col1:
    # 获取所有错题本
    mistake_books = question_db.list_mistake_books()
    if "selected_mistake_book" not in st.session_state:
        st.session_state.selected_mistake_book = "默认错题本"
    
    selected_book = st.selectbox(
        "📚 选择错题本", 
        mistake_books,
        index=mistake_books.index(st.session_state.selected_mistake_book) if st.session_state.selected_mistake_book in mistake_books else 0,
        key="mistake_book_selector",
        label_visibility="collapsed" # 新增：隐藏标签
    )
    
    # 如果切换了错题本，清空选中状态
    if st.session_state.selected_mistake_book != selected_book:
        st.session_state.selected_questions = set()
    st.session_state.selected_mistake_book = selected_book

with col2:
    with st.popover("⚙️ 管理错题本"):
        st.subheader("创建新错题本")
        new_book_name = st.text_input("错题本名称", key="new_book_input")
        if st.button("➕ 创建", key="create_book_btn"):
            if new_book_name:
                if question_db.create_mistake_book(new_book_name):
                    st.success(f"创建成功：{new_book_name}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("该错题本已存在")
            else:
                st.warning("请输入错题本名称")
        
        st.markdown("---")
        st.subheader("删除错题本")
        if selected_book != "默认错题本":
            if st.button(f"🗑️ 删除 {selected_book}", type="secondary", key="delete_book_btn"):
                if question_db.delete_mistake_book(selected_book):
                    st.session_state.selected_mistake_book = "默认错题本"
                    st.success("删除成功")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.info("默认错题本不能删除")

# 获取当前错题本的错题
wrong_questions = question_db.get_wrong_questions(mistake_book=selected_book)

# 检查是否有处理中的题目
has_processing = False
if wrong_questions:
    has_processing = any(item.get("status", "completed") == "processing" for item in wrong_questions)

# Session State for Re-quiz
if "mistake_index" not in st.session_state:
    st.session_state.mistake_index = 0
if "mistake_mode" not in st.session_state:
    st.session_state.mistake_mode = "list" # list, quiz
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = set()  # 存储选中的错题ID

# --- Mode: List View ---
if st.session_state.mistake_mode == "list":
    # 如果有处理中的题目，显示提示和刷新按钮
    if has_processing:
        col_info, col_refresh = st.columns([3, 1])
        with col_info:
            st.info("⏳ 检测到有题目正在后台处理中，请稍候...")
        with col_refresh:
            if st.button("🔄 刷新状态", key="refresh_processing"):
                st.rerun()
    
    st.markdown(f"### 共 {len(wrong_questions)} 道错题")
    
    # 如果错题本为空，显示提示信息
    if not wrong_questions:
        st.info(f"🎉 太棒了！错题本「{selected_book}」是空的。可以手动添加错题或去【做题练习】！")
        if st.button("前往做题练习", type="primary"):
            st.switch_page("pages/2_📝_做题练习.py")
        st.markdown("---")
        expand_all = False  # 空错题本时不需要展开选项
    else:
        # 有错题时显示复习按钮
        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if st.button("📝 开始复习模式 (逐个重做)", type="primary", use_container_width=True):
                st.session_state.mistake_mode = "quiz"
                st.session_state.mistake_index = 0
                st.rerun()
        with col_act2:
            expand_all = st.checkbox("📖 展开所有题目", value=False)

    # Manual Question Upload - 始终显示，无论错题本是否为空
    with st.expander("➕ 手动添加错题", expanded=False):
        with st.form("manual_add_mistake"):
            st.info("💡 提示：上传题目图片后，系统将尝试自动识别题目内容和选项。")
            
            # 选择添加到哪个错题本
            target_book = st.selectbox(
                "📚 添加到错题本", 
                question_db.list_mistake_books(),
                index=question_db.list_mistake_books().index(selected_book) if selected_book in question_db.list_mistake_books() else 0,
                help="选择将错题添加到哪个错题本"
            )
            
            uploaded_q_image = st.file_uploader("上传题目图片（可选）", type=["jpg", "png", "jpeg"])
            
            # Use columns for text inputs to save space if needed, or just standard
            q_content = st.text_area("题目内容 (留空则尝试从图片自动提取)", placeholder="请输入题目文本...", height=100)
            q_options = st.text_area("选项 (每行一个，留空则尝试自动提取)", placeholder="A. 选项1\nB. 选项2\n...", height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                q_correct = st.text_input("正确答案 (可选)", placeholder="例如：A")
            with col2:
                q_explanation = st.text_area("解析 (留空则由 AI 生成)", placeholder="请输入解析...", height=100)
            
            submitted = st.form_submit_button("智能识别并添加")
            
            if submitted:
                # 至少需要有图片 或者 有题目内容
                # 如果没有图片，必须有题目内容
                # 如果有图片，题目内容可以为空
                
                valid_input = False
                if uploaded_q_image:
                    valid_input = True
                elif q_content:
                    valid_input = True
                    
                if not valid_input:
                    st.error("请至少输入题目文本或上传图片")
                else:
                    # 先保存"处理中"状态的记录
                    initial_question = q_content if q_content else "（正在识别中...）"
                    initial_options = q_options.split('\n') if q_options else ["（正在识别中...）"]
                    
                    initial_question_data = {
                        "question": initial_question,
                        "options": initial_options,
                        "correct_answer": q_correct if q_correct else "（处理中...）",
                        "explanation": q_explanation if q_explanation else "（处理中...）"
                    }
                    
                    # 保存图片数据到 session state（用于后台处理）
                    image_data = None
                    if uploaded_q_image:
                        image_data = base64.b64encode(uploaded_q_image.getvalue()).decode('utf-8')
                    
                    # 添加"处理中"状态的记录
                    record_id = question_db.add_result(
                        kb_name="Manual_Upload", 
                        question_data=initial_question_data,
                        user_answer="（手动添加）",
                        is_correct=False,
                        summary="处理中...",
                        mistake_book=target_book,
                        status="processing"
                    )
                    
                    # 启动后台线程处理 LLM 识别
                    def process_question_async(record_id, target_book, q_content, q_options, q_correct, q_explanation, image_data):
                        """后台异步处理题目识别"""
                        try:
                            client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
                            
                            final_question = q_content
                            final_options = q_options
                            final_correct = q_correct
                            final_explanation = q_explanation
                            
                            # 1. Image Processing (Extraction)
                            if image_data and (not q_content or not q_options):
                                try:
                                    extract_prompt = """请识别这张图片中的题目。
                                    请以严格的 JSON 格式输出，不要包含 Markdown 代码块。
                                    格式如下：
                                    {
                                        "question": "题目文本",
                                        "options": ["选项A内容", "选项B内容", ...],
                                        "correct_answer": "如果有标准答案请填在这里，否则留空",
                                        "explanation": "如果有解析请填在这里，否则留空"
                                    }
                                    """
                                    response = client.chat.completions.create(
                                        model=VL_MODEL_NAME,
                                        messages=[
                                            {
                                                "role": "user", 
                                                "content": [
                                                    {"type": "text", "text": extract_prompt},
                                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                                                ]
                                            }
                                        ],
                                        response_format={"type": "json_object"}
                                    )
                                    extracted = json.loads(response.choices[0].message.content)
                                    
                                    if not final_question: final_question = extracted.get("question", "")
                                    if not final_options: final_options = "\n".join(extracted.get("options", []))
                                    if not final_correct: final_correct = extracted.get("correct_answer", "")
                                    if not final_explanation: final_explanation = extracted.get("explanation", "")
                                    
                                except Exception as e:
                                    print(f"图片识别失败: {e}")
                            
                            # 2. Answer & Explanation Generation (if missing)
                            if not final_correct or not final_explanation:
                                try:
                                    solve_prompt = f"""
                                    题目：{final_question}
                                    选项：{final_options}
                                    
                                    请做这道题。
                                    1. 给出正确选项（例如 "A" 或 "选项内容"）。
                                    2. 给出详细解析。
                                    
                                    请以 JSON 格式输出：
                                    {{
                                        "correct_answer": "...",
                                        "explanation": "..."
                                    }}
                                    """
                                    solve_resp = client.chat.completions.create(
                                        model=MODEL_NAME,
                                        messages=[{"role": "user", "content": solve_prompt}],
                                        response_format={"type": "json_object"}
                                    )
                                    solution = json.loads(solve_resp.choices[0].message.content)
                                    
                                    if not final_correct: final_correct = solution.get("correct_answer", "")
                                    if not final_explanation: final_explanation = solution.get("explanation", "")
                                    
                                except Exception as e:
                                    print(f"解析生成失败: {e}")

                            # Construct Final Data
                            options_list = [opt.strip() for opt in final_options.split('\n') if opt.strip()]
                            if not options_list: options_list = ["(未识别到选项)"]
                            
                            question_data = {
                                "question": final_question if final_question else "（未识别题目）",
                                "options": options_list,
                                "correct_answer": final_correct if final_correct else "（未知）",
                                "explanation": final_explanation if final_explanation else "暂无解析"
                            }
                            
                            # Generate Summary for Manual Question
                            summary = None
                            try:
                                sum_prompt = f"请用不超过20个字总结以下题目的核心考点或问题大意：\n{final_question}"
                                sum_resp = client.chat.completions.create(
                                    model=MODEL_NAME,
                                    messages=[{"role": "user", "content": sum_prompt}],
                                    max_tokens=50,
                                    temperature=0.3
                                )
                                summary = sum_resp.choices[0].message.content.strip()
                            except Exception as e:
                                print(f"Summary generation failed: {e}")
                                summary = final_question[:20] + "..." if final_question else "图片题目"

                            # 更新记录状态
                            question_db.update_question_status(
                                record_id=record_id,
                                question_data=question_data,
                                summary=summary,
                                status="completed",
                                mistake_book=target_book
                            )
                        except Exception as e:
                            print(f"后台处理失败: {e}")
                            # 更新为失败状态
                            question_db.update_question_status(
                                record_id=record_id,
                                status="failed",
                                mistake_book=target_book
                            )
                    
                    # 启动后台线程
                    thread = threading.Thread(
                        target=process_question_async,
                        args=(record_id, target_book, q_content, q_options, q_correct, q_explanation, image_data),
                        daemon=True
                    )
                    thread.start()
                    
                    st.success("✅ 题目已添加，正在后台处理中...")
                    time.sleep(0.5)
                    st.rerun()

    # 错题列表显示 - 只有当有错题时才显示
    if wrong_questions:
        st.markdown("---")
        
        # 批量操作区域
        selected_count = len(st.session_state.selected_questions)
        col_batch1, col_batch2, col_batch3, col_batch4 = st.columns([1, 1, 1, 2])
        with col_batch1:
            if st.button("✅ 全选", key="select_all", use_container_width=True):
                # 更新选中集合
                all_ids = {item["id"] for item in wrong_questions}
                st.session_state.selected_questions = all_ids
                # 同步更新所有checkbox的session_state
                for item in wrong_questions:
                    checkbox_key = f"checkbox_{item['id']}"
                    st.session_state[checkbox_key] = True
                st.rerun()
        with col_batch2:
            if st.button("❌ 取消全选", key="deselect_all", use_container_width=True):
                # 更新选中集合
                st.session_state.selected_questions = set()
                # 同步更新所有checkbox的session_state
                for item in wrong_questions:
                    checkbox_key = f"checkbox_{item['id']}"
                    st.session_state[checkbox_key] = False
                st.rerun()
        with col_batch3:
            if selected_count > 0:
                if st.button(f"🗑️ 批量删除 ({selected_count})", key="batch_delete", type="primary", use_container_width=True):
                    # 批量删除选中的错题
                    for question_id in st.session_state.selected_questions:
                        question_db.remove_wrong_question(question_id, mistake_book=selected_book)
                    st.session_state.selected_questions = set()
                    st.success(f"已删除 {selected_count} 道错题")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.button("🗑️ 批量删除", key="batch_delete_disabled", disabled=True, use_container_width=True)
        with col_batch4:
            if selected_count > 0:
                st.info(f"已选择 {selected_count} 道错题")

        st.markdown("---")

        for i, item in enumerate(wrong_questions):
            q = item["question"]
            question_text = q.get('question')
            
            # 检查处理状态
            status = item.get("status", "completed")  # 默认为已完成（兼容旧数据）
            is_processing = status == "processing"
            is_failed = status == "failed"
            
            # Summary logic: Use LLM summary if available, else truncate
            summary = item.get("summary")
            if not summary:
                summary = question_text[:20] + "..." if len(question_text) > 20 else question_text
            
            # 如果正在处理中，在摘要前添加标识
            if is_processing:
                summary = f"⏳ 处理中... {summary}"
            elif is_failed:
                summary = f"❌ 处理失败 {summary}"
            
            # 多选复选框（处理中的题目不允许选择）
            col_check, col_expander = st.columns([0.05, 0.95])
            with col_check:
                checkbox_key = f"checkbox_{item['id']}"
                # 初始化checkbox状态（如果不存在）
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = item["id"] in st.session_state.selected_questions
                
                is_selected = st.checkbox(
                    "",
                    value=st.session_state[checkbox_key],
                    key=checkbox_key,
                    label_visibility="collapsed",
                    disabled=is_processing  # 处理中的题目不允许选择
                )
                # 根据checkbox状态同步更新选中集合
                # 检查状态是否改变，如果改变则更新并刷新页面
                was_selected = item["id"] in st.session_state.selected_questions
                if is_selected != was_selected and not is_processing:
                    if is_selected:
                        st.session_state.selected_questions.add(item["id"])
                    else:
                        st.session_state.selected_questions.discard(item["id"])
                    st.rerun()
            
            with col_expander:
                expander_title = f"❌ 错题 {i+1}: {summary}"
                if is_processing:
                    expander_title = f"⏳ 错题 {i+1}: {summary}"
                elif is_failed:
                    expander_title = f"❌ 错题 {i+1}: {summary}"
                
                with st.expander(expander_title, expanded=expand_all):
                    if is_processing:
                        st.info("🔄 正在后台处理中，请稍候...")
                        st.markdown(f"**题目：** {question_text}")
                        st.markdown("**选项：**")
                        options = q.get("options", [])
                        for opt in options:
                            st.text(f"- {opt}")
                        st.warning("💡 题目内容正在由 AI 识别和处理中，完成后会自动更新。")
                    elif is_failed:
                        st.error("❌ 处理失败，请重新上传或手动编辑。")
                        st.markdown(f"**题目：** {question_text}")
                        st.markdown("**选项：**")
                        options = q.get("options", [])
                        for opt in options:
                            st.text(f"- {opt}")
                    else:
                        # 正常显示
                        st.markdown(f"**题目：** {question_text}")
                        st.markdown("**选项：**")
                        options = q.get("options", [])
                        for opt in options:
                            st.text(f"- {opt}")
                        
                        st.markdown(f"**你的错误答案：** ❌ {item.get('user_answer')}")
                        
                        # Editable Correct Answer
                        current_correct = q.get('correct_answer')
                        col_ans, col_edit = st.columns([3, 1])
                        with col_ans:
                            st.markdown(f"**正确答案：** ✅ {current_correct}")
                        with col_edit:
                            with st.popover("✏️ 修改答案"):
                                new_correct = st.selectbox("修正正确答案为:", options, index=options.index(current_correct) if current_correct in options else 0, key=f"edit_ans_{item['id']}")
                                if st.button("确认修改", key=f"confirm_edit_{item['id']}"):
                                    question_db.update_correct_answer(item['id'], new_correct, mistake_book=selected_book)
                                    st.rerun()

                        st.info(f"💡 **解析：** {q.get('explanation')}")
                        
                        if st.button("🗑️ 我已掌握，移出错题本", key=f"del_{item['id']}"):
                            question_db.remove_wrong_question(item['id'], mistake_book=selected_book)
                            st.rerun()

# --- Mode: Quiz View ---
elif st.session_state.mistake_mode == "quiz":
    # Reload in case some were deleted
    wrong_questions = question_db.get_wrong_questions(mistake_book=st.session_state.selected_mistake_book)
    # 过滤掉处理中的题目（复习模式不显示处理中的题目）
    wrong_questions = [q for q in wrong_questions if q.get("status", "completed") != "processing"]
    
    if not wrong_questions:
        st.session_state.mistake_mode = "list"
        st.rerun()
        
    idx = st.session_state.mistake_index
    if idx >= len(wrong_questions):
        st.success("🎉 复习完成！")
        if st.button("返回列表"):
            st.session_state.mistake_mode = "list"
            st.rerun()
        st.stop()
        
    item = wrong_questions[idx]
    q = item["question"]
    
    st.progress((idx + 1) / len(wrong_questions))
    st.caption(f"错题复习 {idx + 1} / {len(wrong_questions)}")
    
    st.markdown(f"### {q.get('question')}")
    
    # State for current question feedback
    if f"mistake_answered_{item['id']}" not in st.session_state:
        st.session_state[f"mistake_answered_{item['id']}"] = False
        
    options = q.get("options", [])
    correct_option = q.get("correct_answer")
    
    answered = st.session_state[f"mistake_answered_{item['id']}"]
    
    if not answered:
        for opt in options:
            if st.button(opt, key=f"mq_{item['id']}_{opt}", use_container_width=True):
                if opt == correct_option:
                    st.toast("✅ 回答正确！")
                    st.session_state[f"mistake_answered_{item['id']}"] = True
                    st.rerun()
                else:
                    st.toast("❌ 依然错误，请再想想", icon="❌")
    else:
        st.success(f"✅ 正确答案：{correct_option}")
        st.info(f"💡 解析：{q.get('explanation')}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 标记为已掌握 (移出)", key=f"mq_del_{item['id']}", type="primary"):
                question_db.remove_wrong_question(item['id'], mistake_book=st.session_state.selected_mistake_book)
                # Adjust index if needed? If we delete, the next item slides into this index.
                # So we don't increment index, but we need to reset the state for the new item at this index?
                # Actually, easier to just increment index for flow, or reload.
                # If we delete, len decreases. 
                # Let's just remove and stay at same index (which is now next item).
                # But we need to clear session state for the 'next' item ID if it was recycled?
                # Using ID in key helps.
                st.rerun()
        with col2:
            if st.button("➡️ 下一题", key=f"mq_next_{item['id']}"):
                st.session_state.mistake_index += 1
                st.rerun()

    if st.button("🔙 退出复习", type="secondary"):
        st.session_state.mistake_mode = "list"
        st.rerun()

