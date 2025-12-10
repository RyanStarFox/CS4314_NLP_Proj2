import streamlit as st
import time
import os
import base64
import random
import re 
from rag_agent import RAGAgent

# ================= 1. 页面配置 =================
st.set_page_config(
    page_title="CS4314 智能课程助教",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; color: #004098; text-align: center; margin-bottom: 0.5rem; font-weight: 700; }
    .sub-title { font-size: 1.1rem; color: #666; text-align: center; margin-bottom: 2rem; }
    .stChatMessage { padding: 1rem; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .stMarkdown p { line-height: 1.8; margin-bottom: 1em; }
    .katex { font-size: 1.1em; }
    .stButton button { width: 100%; border-radius: 8px; }
    .streamlit-expanderHeader { font-size: 0.9em; color: #666; }
</style>
""", unsafe_allow_html=True)

# ================= 2. 初始化 =================

@st.cache_resource
def get_agent():
    return RAGAgent()

try:
    agent = get_agent()
except Exception as e:
    st.error(f"⚠️ 系统初始化失败: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我是你的智能课程助教。\n\n我可以帮你解答课程概念、作业难题，也支持 **上传题目截图** 提问，或者点击侧边栏进行 **随堂测验**！"}
    ]

# [新增] 初始化上传控件的 Key，用于重置控件
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ================= 3. 侧边栏 =================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    else:
        st.markdown("## 🎓 SJTU NLP")
    
    st.title("🎛️ 控制面板")
    st.success("✅ RAG 引擎在线")
    
    st.markdown("---")
    st.markdown("### 📝 互动练习")
    
    if st.button("📝 生成随堂测验", type="primary"):
        search_keywords = [
            "定义", "核心概念", "算法原理", "优缺点", "公式计算", 
            "应用场景", "分类", "区别", "性质", "定理"
        ]
        random_topic = random.choice(search_keywords)
        quiz_prompt = f"请检索关于【{random_topic}】的相关知识，并据此出一道单项选择题。包含题干、4个选项（A,B,C,D）。不要直接给出答案，请等待我作答。"
        
        st.session_state.messages.append({"role": "user", "content": quiz_prompt})
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📸 多模态输入")
    
    # [关键修改] 使用 key=st.session_state.uploader_key 来绑定状态
    uploaded_file = st.file_uploader(
        "上传题目或图表截图", 
        type=["jpg", "png", "jpeg"],
        key=f"uploader_{st.session_state.uploader_key}" 
    )
    
    image_base64 = None
    if uploaded_file:
        st.image(uploaded_file, caption="已添加图片", use_container_width=True)
        # 立即转为 Base64
        image_base64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
    
    st.markdown("---")
    if st.button("🗑️ 清空对话历史"):
        st.session_state.messages = [
            {"role": "assistant", "content": "对话已重置。"}
        ]
        # 重置上传控件
        st.session_state.uploader_key += 1
        st.rerun()

# ================= 4. 主逻辑 =================

st.markdown('<div class="main-title">CS4314 智能课程助教系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">基于 RAG 技术 · 支持文本/图片多模态提问 · 随堂测验</div>', unsafe_allow_html=True)

# 展示历史
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍🎓" if message["role"] == "user" else "🤖"):
        display_content = message["content"]
        if "请检索关于" in display_content and "出一道单项选择题" in display_content:
            display_content = "🙋‍♂️ **我想做一道随堂练习题，请考考我！**"
        
        # [关键修改] 从历史记录里读取 Base64 字符串来显示图片，而不是读取 UploadedFile 对象
        if "image_base64" in message and message["image_base64"]:
            st.image(base64.b64decode(message["image_base64"]), width=300)
            
        st.markdown(display_content)

# 处理用户输入
if prompt := st.chat_input("请输入问题..."):
    # 1. 构造用户消息
    user_msg = {"role": "user", "content": prompt}
    
    # [关键修复] 只存 Base64 字符串，绝对不要存 uploaded_file 对象！
    if image_base64:
        user_msg["image_base64"] = image_base64
        
    st.session_state.messages.append(user_msg)
    
    # [关键修改] 消息发送后，让 uploader_key + 1，强制在下一次 rerun 时清空上传框
    if uploaded_file:
        st.session_state.uploader_key += 1
        
    st.rerun()

# 生成回答逻辑
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    last_msg = st.session_state.messages[-1]
    prompt = last_msg["content"]
    # 从历史消息里拿刚才存进去的 base64
    current_image_data = last_msg.get("image_base64", None)
    
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 判断逻辑...
            is_quiz_mode = "出一道单项选择题" in prompt
            
            is_answering = False
            user_input_pattern = re.compile(r'^(我?选|答案是|选项)?\s*[a-dA-D]\s*$')
            last_assistant_msg = ""
            if len(st.session_state.messages) > 1:
                last_assistant_msg = st.session_state.messages[-2]["content"]
            
            if ("A." in last_assistant_msg or "A)" in last_assistant_msg) and user_input_pattern.match(prompt):
                is_answering = True

            context_str = ""
            
            if is_answering:
                 st.caption("🧠 正在批改作业... (基于历史对话)")
            else:
                with st.spinner("🔍 正在检索知识库..."):
                    context_str, docs = agent.retrieve_context(prompt)
                
                if context_str:
                    with st.expander(f"📚 点击查看参考资料 ({len(docs)} 条线索)", expanded=False):
                        st.markdown(context_str)
                elif is_quiz_mode:
                    st.caption("⚠️ 未检索到强相关资料，题目将基于通用知识生成。")

            # 清理出题模式的图片干扰
            if is_quiz_mode or is_answering:
                current_image_data = None

            # 调用 Agent
            response_text = agent.generate_response(
                prompt, 
                context_str, 
                chat_history=st.session_state.messages[:-1],
                image_data=current_image_data, # 传入 Base64 字符串
                is_quiz=is_quiz_mode,
                skip_retrieval=is_answering 
            )
            
            for char in response_text:
                full_response += char
                time.sleep(0.002) 
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            full_response = f"❌ 发生错误: {str(e)}"
            message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})