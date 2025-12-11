import streamlit as st
import time
import json
from question_db import QuestionDB

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

question_db = QuestionDB()
wrong_questions = question_db.get_wrong_questions()

if not wrong_questions:
    st.info("🎉 太棒了！目前错题本是空的。快去【做题练习】吧！")
    if st.button("前往做题练习"):
        st.switch_page("pages/2_📝_做题练习.py")
    st.stop()

# Session State for Re-quiz
if "mistake_index" not in st.session_state:
    st.session_state.mistake_index = 0
if "mistake_mode" not in st.session_state:
    st.session_state.mistake_mode = "list" # list, quiz

# --- Mode: List View ---
if st.session_state.mistake_mode == "list":
    st.markdown(f"### 共 {len(wrong_questions)} 道错题")
    
    col_act1, col_act2 = st.columns([1, 1])
    with col_act1:
        if st.button("📝 开始复习模式 (逐个重做)", type="primary", use_container_width=True):
            st.session_state.mistake_mode = "quiz"
            st.session_state.mistake_index = 0
            st.rerun()
    with col_act2:
        expand_all = st.checkbox("📖 展开所有题目", value=False)

    # Manual Question Upload
    with st.expander("➕ 手动添加错题", expanded=False):
        with st.form("manual_add_mistake"):
            st.info("💡 提示：上传题目图片后，系统将尝试自动识别题目内容和选项。")
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
                    with st.spinner("正在处理..."):
                        import base64
                        from openai import OpenAI
                        from config import OPENAI_API_KEY, OPENAI_API_BASE, VL_MODEL_NAME
                        
                        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
                        
                        final_question = q_content
                        final_options = q_options
                        final_correct = q_correct
                        final_explanation = q_explanation
                        
                        # 1. Image Processing (Extraction)
                        if uploaded_q_image and (not q_content or not q_options):
                            try:
                                img_b64 = base64.b64encode(uploaded_q_image.getvalue()).decode('utf-8')
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
                                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
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
                                st.warning(f"图片识别失败: {e}")
                        
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
                                # Use standard model for solving if text is available
                                from config import MODEL_NAME
                                solve_resp = client.chat.completions.create(
                                    model=MODEL_NAME,
                                    messages=[{"role": "user", "content": solve_prompt}],
                                    response_format={"type": "json_object"}
                                )
                                solution = json.loads(solve_resp.choices[0].message.content)
                                
                                if not final_correct: final_correct = solution.get("correct_answer", "")
                                # User requested "Always generate explanation" (LLM自己生成解析)
                                # So we prefer LLM explanation unless user provided one?
                                # User said: "始终自己生成解析" -> Assuming if user left it blank, generate. 
                                # But actually "始终" implies overwrite? Let's stick to "if blank" for better UX, or append.
                                # Let's overwrite if blank.
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
                            # Use existing logic to generate summary
                            sum_prompt = f"请用不超过20个字总结以下题目的核心考点或问题大意：\n{final_question}"
                            
                            # Use standard model for summarization
                            from config import MODEL_NAME
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

                        question_db.add_result(
                            kb_name="Manual_Upload", 
                            question_data=question_data,
                            user_answer="（手动添加）",
                            is_correct=False,
                            summary=summary
                        )
                        st.success("添加成功！")
                        time.sleep(1)
                        st.rerun()

    st.markdown("---")

    for i, item in enumerate(wrong_questions):
        q = item["question"]
        question_text = q.get('question')
        
        # Summary logic: Use LLM summary if available, else truncate
        summary = item.get("summary")
        if not summary:
            summary = question_text[:20] + "..." if len(question_text) > 20 else question_text
        
        with st.expander(f"❌ 错题 {i+1}: {summary}", expanded=expand_all):
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
                        question_db.update_correct_answer(item['id'], new_correct)
                        st.rerun()

            st.info(f"💡 **解析：** {q.get('explanation')}")
            
            if st.button("🗑️ 我已掌握，移出错题本", key=f"del_{item['id']}"):
                question_db.remove_wrong_question(item['id'])
                st.rerun()

# --- Mode: Quiz View ---
elif st.session_state.mistake_mode == "quiz":
    # Reload in case some were deleted
    wrong_questions = question_db.get_wrong_questions()
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
                question_db.remove_wrong_question(item['id'])
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

