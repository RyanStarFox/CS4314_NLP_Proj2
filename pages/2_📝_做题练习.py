import streamlit as st
import time
import json
from rag_agent import RAGAgent
from kb_manager import KBManager
from question_db import QuestionDB

st.set_page_config(page_title="做题练习", page_icon="logo.webp", layout="wide")

st.markdown("""
<style>
    .stButton button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
    }
    .option-card {
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .option-card:hover {
        background-color: #f5f5f5;
    }
    .correct {
        background-color: #d4edda !important;
        border-color: #c3e6cb !important;
    }
    .incorrect {
        background-color: #f8d7da !important;
        border-color: #f5c6cb !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📝 智能做题练习")

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
            num_questions = st.number_input("🔢 题目数量", min_value=1, max_value=10, value=3)
            num_options = st.number_input("🔠 选项数量", min_value=2, max_value=6, value=4)
        
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
                "count": num_questions,
                "options": num_options,
                "topic": topic_refinement if topic_refinement else "Core Concepts and Key Principles"
            }
            
            # Initialize Agent
            with st.spinner("正在加载智能助教..."):
                agent = RAGAgent(kb_name=selected_kb)
                st.session_state.quiz_agent = agent
            
            # Generate Questions
            status_text = st.empty()
            status_text.text(f"正在并行生成 {num_questions} 道题目，请稍候...")
            
            # Use batch generation with randomization and parallelism
            questions = agent.generate_quiz_batch(
                count=num_questions, 
                topic=st.session_state.quiz_config["topic"], 
                q_type=st.session_state.quiz_config["type"], 
                num_options=num_options
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
    
    st.markdown(f"### {question_data.get('question', '题目加载错误')}")
    
    # Check if already answered
    answered = idx in st.session_state.user_answers
    prev_answer = st.session_state.user_answers[idx]['answer'] if answered else None
    
    # Options
    options = question_data.get("options", [])
    correct_option = question_data.get("correct_answer", "")
    
    # Render Options
    # If not answered, show buttons. If answered, show result.
    if not answered:
        for opt in options:
            if st.button(opt, key=f"q{idx}_opt_{opt}", use_container_width=True):
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
                        # Quick summarization using the same agent instance
                        # Assuming 'agent' is available from session state or recreated
                        if 'quiz_agent' in st.session_state:
                            sum_agent = st.session_state.quiz_agent
                            # A quick call to summarize. Using a very low temp for determinism.
                            # We can use the chat completion directly for speed/cost if needed, 
                            # but re-using agent methods is cleaner if available.
                            # Agent doesn't have a direct 'summarize' method, so we call client directly or add one.
                            # Let's call client directly to be safe and quick.
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
                    question_db.add_result(
                        kb_name=st.session_state.quiz_config["kb"],
                        question_data=question_data,
                        user_answer=opt,
                        is_correct=False,
                        summary=summary
                    )
                st.rerun()
    else:
        # Show Result
        user_choice = st.session_state.user_answers[idx]['answer']
        is_correct = st.session_state.user_answers[idx]['correct']
        
        for opt in options:
            btn_color = "secondary"
            prefix = ""
            
            if opt == correct_option:
                prefix = "✅ "
                # Green style is hard with st.button, use markdown for feedback
            elif opt == user_choice and not is_correct:
                prefix = "❌ "
            
            st.button(f"{prefix}{opt}", key=f"q{idx}_res_{opt}", disabled=True, use_container_width=True)

        if is_correct:
            st.success("回答正确！")
        else:
            st.error(f"回答错误。正确答案是：{correct_option}")
            
        with st.expander("💡 查看解析", expanded=True):
            st.write(question_data.get("explanation", "暂无解析"))
        
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
        if st.button("🔄 再来一组"):
            st.session_state.quiz_state = "config"
            st.session_state.quiz_questions = []
            st.rerun()
    with col_b:
        if st.button("📓 查看错题本"):
            st.switch_page("pages/3_📓_错题整理.py")

