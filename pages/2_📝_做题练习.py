import streamlit as st
import time
import json
from rag_agent import RAGAgent
from kb_manager import KBManager
from question_db import QuestionDB

st.set_page_config(page_title="做题练习", page_icon="logo.webp", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 4rem; }
    /* 选项按钮样式 - 使其看起来像可点击的卡片，整个选项文本可点击 */
    /* 通过 key 选择器定位选项按钮（key 包含 "q" 和 "_opt_"） */
    div[data-testid="stButton"] > button[kind="secondary"] {
        width: 100%;
        border-radius: 10px;
        padding: 15px 20px;
        margin-bottom: 10px;
        text-align: left !important;
        display: flex;
        justify-content: flex-start !important;
        align-items: center;
        height: auto;
        min-height: 3em;
        white-space: normal !important;
        word-wrap: break-word;
        border: 1px solid rgba(128, 128, 128, 0.3);
        background-color: var(--secondary-background-color, #f0f0f0);
        color: var(--text-color, #000);
        transition: all 0.2s;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: var(--background-color, #f5f5f5);
        border-color: var(--primary-color, #1f77b4);
        transform: translateY(-2px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    /* 暗黑模式下的选项按钮 */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: var(--secondary-background-color, #262730);
            border-color: rgba(255, 255, 255, 0.2);
            color: var(--text-color, #fff);
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background-color: var(--background-color, #0e1117);
            border-color: var(--primary-color, #1f77b4);
        }
    }
    
    .option-card {
        padding: 15px;
        border: 1px solid rgba(128, 128, 128, 0.3);
        border-radius: 10px;
        margin-bottom: 10px;
        transition: all 0.2s;
        background-color: var(--secondary-background-color, #f0f0f0);
        color: var(--text-color, #000);
    }
    /* 暗黑模式下的选项卡片 */
    @media (prefers-color-scheme: dark) {
        .option-card {
            background-color: var(--secondary-background-color, #262730);
            border-color: rgba(255, 255, 255, 0.2);
            color: var(--text-color, #fff);
        }
    }
    .correct {
        background-color: rgba(40, 167, 69, 0.15) !important;
        border-color: rgba(40, 167, 69, 0.5) !important;
    }
    /* 暗黑模式下的正确选项 */
    @media (prefers-color-scheme: dark) {
        .correct {
            background-color: rgba(40, 167, 69, 0.25) !important;
            border-color: rgba(40, 167, 69, 0.6) !important;
        }
    }
    .incorrect {
        background-color: rgba(220, 53, 69, 0.15) !important;
        border-color: rgba(220, 53, 69, 0.5) !important;
    }
    /* 暗黑模式下的错误选项 */
    @media (prefers-color-scheme: dark) {
        .incorrect {
            background-color: rgba(220, 53, 69, 0.25) !important;
            border-color: rgba(220, 53, 69, 0.6) !important;
        }
    }
    
    /* 结果页面的按钮适配暗黑模式 */
    div[data-testid="stButton"] > button[kind="primary"] {
        color: var(--text-color, #fff);
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stButton"] > button[kind="primary"] {
            color: var(--text-color, #fff);
            background-color: var(--primary-color, #ff4b4b);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: var(--primary-color, #ff6b6b);
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📝 智能做题练习") # Title stays same


# Initialize Managers
kb_manager = KBManager()
question_db = QuestionDB()
kbs = kb_manager.list_kbs()

if not kbs:
    st.warning("⚠️ 请先在【知识库管理】中添加知识库")
    st.stop()

# Session State Initialization
if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = "config" # config, quizzing, summary
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {} # {index: {answer: str, correct: bool}}
if "score" not in st.session_state:
    st.session_state.score = 0

# --- Phase 1: Configuration ---
if st.session_state.quiz_state == "config":
    st.subheader("🛠️ 练习配置")
    
    with st.form("quiz_settings_form"):
        selected_kb = st.selectbox("📚 选择知识库", kbs)
        
        col1, col2 = st.columns(2)
        with col1:
            quiz_type = st.radio("🎯 题目类型", ["偏概念 (Concept)", "偏应用 (Application)"])
            q_type_str = "Concept" if "概念" in quiz_type else "Application"
        
        with col2:
            question_format = st.radio("📝 题目格式", ["选择题", "填空题"])
            format_str = "multiple_choice" if question_format == "选择题" else "fill_in_blank"
        
        col3, col4 = st.columns(2)
        with col3:
            num_questions = st.number_input("🔢 题目数量", min_value=1, max_value=10, value=3)
        
        with col4:
            if format_str == "multiple_choice":
                num_options = st.number_input("🔠 选项数量", min_value=2, max_value=6, value=4)
                num_blanks = 3  # 默认值，不显示
            else:  # fill_in_blank
                num_blanks = st.number_input("📋 空格数量", min_value=1, max_value=5, value=3)
                num_options = 4  # 默认值，不显示
        
        # Optional: Topic refinement
        topic_refinement = st.text_input("🔍 重点考察主题 (可选，留空则随机)", placeholder="例如：微积分、矩阵、排序算法...")
        
        submitted = st.form_submit_button("🚀 开始练习", type="primary")
        
        if submitted:
            # Check KB status before starting
            with st.spinner("正在检查知识库状态..."):
                temp_agent = RAGAgent(kb_name=selected_kb)
                count = temp_agent.vector_store.get_collection_count()
                
                # Auto-vectorization check
                if count == 0:
                    files = kb_manager.list_files(selected_kb)
                    if files:
                        st.info(f"📚 检测到知识库 '{selected_kb}' 尚未向量化，正在首次处理，请稍候...")
                        progress_text = st.empty()
                        kb_manager.rebuild_kb_index(selected_kb)
                        st.success("✅ 向量化完成！")
                        # Re-init agent
                        temp_agent = RAGAgent(kb_name=selected_kb)
                    else:
                        st.error("⚠️ 该知识库为空，请先在【知识库管理】中上传文档。")
                        st.stop()

            st.session_state.quiz_config = {
                "kb": selected_kb,
                "type": q_type_str,
                "format": format_str,
                "count": num_questions,
                "options": num_options,
                "blanks": num_blanks,
                "topic": topic_refinement if topic_refinement else "Core Concepts and Key Principles"
            }
            
            # Initialize Agent
            with st.spinner("正在加载智能助教..."):
                agent = RAGAgent(kb_name=selected_kb)
                st.session_state.quiz_agent = agent
            
            # Generate Questions
            status_text = st.empty()
            format_name = "选择题" if format_str == "multiple_choice" else "填空题"
            status_text.text(f"正在并行生成 {num_questions} 道{format_name}，请稍候...")
            
            # Use batch generation with randomization and parallelism
            questions = agent.generate_quiz_batch(
                count=num_questions, 
                topic=st.session_state.quiz_config["topic"], 
                q_type=st.session_state.quiz_config["type"],
                question_format=format_str,
                num_options=num_options,
                num_blanks=num_blanks
            )
            
            if not questions:
                st.error("生成题目失败，请重试或检查知识库内容。")
            else:
                st.session_state.quiz_questions = questions
                st.session_state.current_q_index = 0
                st.session_state.user_answers = {}
                st.session_state.score = 0
                st.session_state.quiz_state = "quizzing"
                st.rerun()

# --- Phase 2: Quizzing ---
elif st.session_state.quiz_state == "quizzing":
    idx = st.session_state.current_q_index
    total = len(st.session_state.quiz_questions)
    
    # Progress
    st.progress((idx) / total)
    st.caption(f"Question {idx + 1} / {total}")
    
    question_data = st.session_state.quiz_questions[idx]
    question_type = question_data.get('question_type', 'multiple_choice')
    
    # 使用 markdown 显示题干，支持 LaTeX 渲染
    question_text = question_data.get('question', '题目加载错误')
    st.markdown(f"### {question_text}")
    
    # Check if already answered
    answered = idx in st.session_state.user_answers
    prev_answer = st.session_state.user_answers[idx]['answer'] if answered else None
    
    # 根据题目类型渲染不同的答题界面
    if question_type == "fill_in_blank":
        # 填空题
        answers = question_data.get("answers", [])
        num_blanks = len(answers)
        
        if not answered:
            # 显示填空输入框
            st.markdown("**请填写答案：**")
            user_inputs = []
            
            # 为每个空格创建输入框
            for i in range(num_blanks):
                blank_input = st.text_input(
                    f"第 {i+1} 个空格", 
                    key=f"blank_{idx}_{i}",
                    placeholder="请输入答案..."
                )
                user_inputs.append(blank_input)
            
            # 提交按钮
            if st.button("提交答案", key=f"submit_blank_{idx}", type="primary"):
                # 检查是否所有空格都已填写
                if all(inp.strip() for inp in user_inputs):
                    # 计算正确的空格数量（模糊匹配）
                    correct_count = 0
                    for user_inp, correct_ans in zip(user_inputs, answers):
                        # 简单的模糊匹配：去除空格和大小写
                        user_normalized = user_inp.strip().lower()
                        correct_normalized = correct_ans.strip().lower()
                        if user_normalized in correct_normalized or correct_normalized in user_normalized:
                            correct_count += 1
                    
                    is_correct = (correct_count == num_blanks)
                    
                    st.session_state.user_answers[idx] = {
                        "answer": user_inputs,
                        "correct": is_correct,
                        "correct_count": correct_count
                    }
                    
                    if is_correct:
                        st.session_state.score += 1
                    else:
                        # Generate Summary for Wrong Question
                        summary = None
                        try:
                            if 'quiz_agent' in st.session_state:
                                sum_agent = st.session_state.quiz_agent
                                sum_prompt = f"请用不超过20个字总结以下题目的核心考点或问题大意：\n{question_data.get('question')}"
                                sum_resp = sum_agent.client.chat.completions.create(
                                    model=sum_agent.model,
                                    messages=[{"role": "user", "content": sum_prompt}],
                                    max_tokens=50,
                                    temperature=0.3
                                )
                                summary = sum_resp.choices[0].message.content.strip()
                        except Exception as e:
                            print(f"Summary generation failed: {e}")
                            summary = question_data.get('question')[:20] + "..."

                        # Save to Wrong Question DB
                        kb_name = st.session_state.quiz_config["kb"]
                        question_db.add_result(
                            kb_name=kb_name,
                            question_data=question_data,
                            user_answer=str(user_inputs),
                            is_correct=False,
                            summary=summary,
                            mistake_book=kb_name  # Explicitly use KB name
                        )
                    st.rerun()
                else:
                    st.warning("请填写所有空格后再提交")
        else:
            # 显示结果
            user_inputs = st.session_state.user_answers[idx]['answer']
            is_correct = st.session_state.user_answers[idx]['correct']
            correct_count = st.session_state.user_answers[idx].get('correct_count', 0)
            
            st.markdown("**你的答案：**")
            for i, (user_inp, correct_ans) in enumerate(zip(user_inputs, answers)):
                user_normalized = user_inp.strip().lower()
                correct_normalized = correct_ans.strip().lower()
                is_blank_correct = user_normalized in correct_normalized or correct_normalized in user_normalized
                
                if is_blank_correct:
                    st.markdown(f'<div class="option-card correct">✅ 第 {i+1} 个空格: {user_inp}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="option-card incorrect">❌ 第 {i+1} 个空格: {user_inp}</div>', unsafe_allow_html=True)
            
            st.markdown("**正确答案：**")
            for i, ans in enumerate(answers):
                st.markdown(f'<div class="option-card correct">第 {i+1} 个空格: {ans}</div>', unsafe_allow_html=True)
            
            if is_correct:
                st.success("全部正确！")
            else:
                st.error(f"答对 {correct_count}/{num_blanks} 个空格")
            
            with st.expander("💡 查看解析", expanded=True):
                explanation = question_data.get("explanation", "暂无解析")
                st.markdown(explanation)
            
            # Next Button
            if idx < total - 1:
                if st.button("下一题 ➡️", type="primary"):
                    st.session_state.current_q_index += 1
                    st.rerun()
            else:
                if st.button("查看结果 🏁", type="primary"):
                    st.session_state.quiz_state = "summary"
                    st.rerun()
    
    else:  # multiple_choice
        # 选择题
        options = question_data.get("options", [])
        correct_option = question_data.get("correct_answer", "")
        
        # Render Options
        # If not answered, show buttons. If answered, show result.
        if not answered:
            # 显示选项内容（整个选项文本可点击，使用 button 显示）
            st.markdown("**请选择答案：**")
            for i, opt in enumerate(options):
                # 使用 button 显示选项文本，整个选项可点击
                # 虽然按钮文本不支持 Markdown，但 LaTeX 格式会被保留
                option_label = f"{chr(65 + i)}. {opt}"
                # 使用 CSS 类名来应用样式
                if st.button(option_label, key=f"q{idx}_opt_{i}", use_container_width=True, type="secondary"):
                    # 添加 CSS 类名（通过 JavaScript 或直接使用内联样式）
                    is_correct = (opt == correct_option)
                    st.session_state.user_answers[idx] = {
                        "answer": opt,
                        "correct": is_correct
                    }
                    if is_correct:
                        st.session_state.score += 1
                    else:
                        # Generate Summary for Wrong Question
                        summary = None
                        try:
                            if 'quiz_agent' in st.session_state:
                                sum_agent = st.session_state.quiz_agent
                                sum_prompt = f"请用不超过20个字总结以下题目的核心考点或问题大意：\n{question_data.get('question')}"
                                sum_resp = sum_agent.client.chat.completions.create(
                                    model=sum_agent.model,
                                    messages=[{"role": "user", "content": sum_prompt}],
                                    max_tokens=50,
                                    temperature=0.3
                                )
                                summary = sum_resp.choices[0].message.content.strip()
                        except Exception as e:
                            print(f"Summary generation failed: {e}")
                            summary = question_data.get('question')[:20] + "..."

                        # Save to Wrong Question DB
                        kb_name = st.session_state.quiz_config["kb"]
                        try:
                            question_db.add_result(
                                kb_name=kb_name,
                                question_data=question_data,
                                user_answer=opt,
                                is_correct=False,
                                summary=summary,
                                mistake_book=kb_name  # Explicitly use KB name as mistake book
                            )
                        except Exception as e:
                            st.error(f"保存错题失败: {e}")
                            print(f"Error saving wrong question: {e}")
                            
                    st.rerun()
        else:
            # Show Result
            user_choice = st.session_state.user_answers[idx]['answer']
            is_correct = st.session_state.user_answers[idx]['correct']
            
            st.markdown("### 📝 答案解析")
            
            for i, opt in enumerate(options):
                option_label = f"**{chr(65 + i)}.** {opt}"
                
                if opt == correct_option:
                    # 正确选项
                    with st.container():
                        st.success(option_label, icon="✅")
                elif opt == user_choice and not is_correct:
                    # 用户选错的选项
                    with st.container():
                        st.error(option_label, icon="❌")
                else:
                    # 其他普通选项
                    with st.container(border=True):
                        st.markdown(option_label)

            if is_correct:
                st.success("回答正确！")
            else:
                # 使用 markdown 显示正确答案，支持 LaTeX 渲染
                st.error("回答错误。正确答案是：")
                st.markdown(f"**{correct_option}**")
                
            with st.expander("💡 查看解析", expanded=True):
                explanation = question_data.get("explanation", "暂无解析")
                st.markdown(explanation)
            
            # Next Button
            if idx < total - 1:
                if st.button("下一题 ➡️", type="primary"):
                    st.session_state.current_q_index += 1
                    st.rerun()
            else:
                if st.button("查看结果 🏁", type="primary"):
                    st.session_state.quiz_state = "summary"
                    st.rerun()

# --- Phase 3: Summary ---
elif st.session_state.quiz_state == "summary":
    st.subheader("📊 练习报告")
    
    total = len(st.session_state.quiz_questions)
    score = st.session_state.score
    accuracy = (score / total) * 100 if total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总题数", total)
    col2.metric("正确数", score)
    col3.metric("正确率", f"{accuracy:.1f}%")
    
    if accuracy == 100:
        st.balloons()
        st.success("太棒了！全对！🎉")
    elif accuracy >= 60:
        st.info("不错，继续加油！")
    else:
        st.warning("还需要多加练习哦，错题已自动加入错题本。")
    
    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 再来一组", type="primary"):
            st.session_state.quiz_state = "config"
            st.session_state.quiz_questions = []
            st.rerun()
    with col_b:
        if st.button("📓 查看错题本", type="primary"):
            st.switch_page("pages/3_📓_错题整理.py")

