import streamlit as st
import time
import base64
import os
from rag_agent import RAGAgent
from kb_manager import KBManager

st.set_page_config(page_title="智能助教", page_icon="logo.webp", layout="wide")

st.markdown("""
<style>
    .stChatMessage { 
        padding: 1.2rem; 
        border-radius: 16px; 
        margin-bottom: 1rem; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 智能助教")

# KB Selection
kb_manager = KBManager()
kbs = kb_manager.list_kbs()

if not kbs:
    st.warning("⚠️ 未检测到知识库。请先前往【知识库管理】页面上传文档。")
    st.stop()

selected_kb = st.sidebar.selectbox("📚 选择知识库", kbs, index=0)

# Initialize Agent
if "agent" not in st.session_state or st.session_state.get("agent_kb") != selected_kb:
    with st.spinner(f"正在加载知识库 {selected_kb}..."):
        st.session_state.agent = RAGAgent(kb_name=selected_kb)
        st.session_state.agent_kb = selected_kb
        
        # Auto-vectorization check
        count = st.session_state.agent.vector_store.get_collection_count()
        if count == 0:
            files = kb_manager.list_files(selected_kb)
            if files:
                st.info(f"📚 检测到知识库 '{selected_kb}' 尚未向量化，正在首次处理，这可能需要比较久的时间...")
                # Use a new spinner for the long task
                with st.spinner("正在进行向量化处理，请耐心等待..."):
                    kb_manager.rebuild_kb_index(selected_kb)
                st.success("✅ 向量化完成！")
                # Reload agent to see new data
                st.session_state.agent = RAGAgent(kb_name=selected_kb)
        
        st.session_state.messages = [
            {"role": "assistant", "content": f"👋 你好！我是基于 **{selected_kb}** 的智能助教。有什么我可以帮你的吗？"}
        ]
        # Reset uploader key
        st.session_state.uploader_key = 0

agent = st.session_state.agent

# Sidebar - Image Uploader
with st.sidebar:
    st.markdown("### 📸 题目助手")
    uploaded_file = st.file_uploader(
        "上传题目或图表截图", 
        type=["jpg", "png", "jpeg"],
        key=f"uploader_{st.session_state.get('uploader_key', 0)}" 
    )
    
    image_base64 = None
    if uploaded_file:
        st.image(uploaded_file, caption="已添加图片", use_container_width=True)
        image_base64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
    
    st.markdown("---")
    if st.button("🗑️ 清空对话历史"):
        st.session_state.messages = [
            {"role": "assistant", "content": f"对话已重置。我是基于 **{selected_kb}** 的智能助教。"}
        ]
        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
        st.rerun()

# Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍🎓" if message["role"] == "user" else "🤖"):
        if "image_base64" in message and message["image_base64"]:
            st.image(base64.b64decode(message["image_base64"]), width=300)
        st.markdown(message["content"])

# Input
if prompt := st.chat_input("请输入问题..."):
    # User message
    user_msg = {"role": "user", "content": prompt}
    if image_base64:
        user_msg["image_base64"] = image_base64
    st.session_state.messages.append(user_msg)
    
    if uploaded_file:
        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    
    st.rerun()

# Response Logic
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    prompt = last_msg["content"]
    current_image_data = last_msg.get("image_base64", None)
    
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            with st.spinner("思考中..."):
                response_text = agent.answer_question(
                    prompt, 
                    chat_history=st.session_state.messages[:-1],
                    image_data=current_image_data
                )
                
                # Retrieve context only for showing sources (agent.answer_question does it internally but returns string)
                # To show sources nicely, we might need to modify agent or just parse the response if it includes sources?
                # The current agent.answer_question returns text. 
                # Let's trust the agent's internal retrieval for now or manually retrieve to show docs.
                # Actually, agent.answer_question calls retrieve_context internally.
                # If we want to show sources in an expander like before, we should call retrieve_context here.
                
                # Check if it's a simple answer or retrieval needed
                if not (len(prompt) < 10 and "选" in prompt):
                     context_str, docs = agent.retrieve_context(prompt)
                     if docs:
                         with st.expander(f"📚 参考资料 ({len(docs)} 条)", expanded=False):
                             st.markdown(context_str)

                # Streaming simulation
                for char in response_text:
                    full_response += char
                    time.sleep(0.002) 
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
        
        except Exception as e:
            full_response = f"❌ 发生错误: {str(e)}"
            message_placeholder.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
