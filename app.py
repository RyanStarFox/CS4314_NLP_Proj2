import streamlit as st
import os

st.set_page_config(
    page_title="智能课程助教",
    page_icon="logo.webp",
    layout="wide",
    initial_sidebar_state="collapsed"  # 默认隐藏侧边栏
)

# --- Custom CSS for "Card" Style (Dark Mode Adapted) ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    /* Global Background & Font - CSS Variables for Dark Mode Support */
    .stApp {
        /* No fixed background, let Streamlit theme handle it */
    }
    
    /* Hide Sidebar on Home Page */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Custom Card Class */
    .nav-card {
        background-color: var(--secondary-background-color); 
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin-bottom: 20px;
        text-decoration: none; /* For links */
        color: var(--text-color);
        cursor: pointer;
    }
    
    .nav-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        border-color: var(--primary-color);
    }
    
    .nav-card h3 {
        color: var(--text-color); 
        margin-bottom: 10px;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    .nav-card p {
        color: var(--text-color);
        opacity: 0.8;
        font-size: 0.9rem;
    }

    /* Emoji size */
    .card-icon {
        font-size: 3rem;
        margin-bottom: 10px;
    }
    
    /* Remove default link styles if we use <a> tags */
    a.card-link {
        text-decoration: none;
        color: inherit;
    }
    a.card-link:hover {
        text-decoration: none;
        color: inherit;
    }
    
    /* Title Styling */
    .main-title {
        text-align: center;
        color: var(--text-color);
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        color: var(--text-color); 
        opacity: 0.7;
        font-weight: 400;
        margin-bottom: 3rem;
    }
    
    /* Reduce top padding for main container */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Header Section ---
# if os.path.exists("logo.webp"):
#     col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1])
#     with col_logo_2:
#         st.image("logo.webp", width=120)

st.markdown('<h1 class="main-title">智能课程助教系统</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">基于 RAG 技术的全能学习助手 · 答疑 · 刷题 · 复习 · 管理</p>', unsafe_allow_html=True)
    
st.markdown("---")

# --- Navigation Cards (Clickable Links) ---
# We use HTML <a> tags wrapping the cards to make them clickable.
# Target is _self to reload in the same tab, navigating to the page URL.

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <a href="智能助教" class="card-link" target="_self">
        <div class="nav-card">
            <div class="card-icon">🧠</div>
            <h3>智能助教</h3>
            <p>24h 在线答疑，支持多模态提问与上下文追问</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <a href="做题练习" class="card-link" target="_self">
        <div class="nav-card">
            <div class="card-icon">📝</div>
            <h3>做题练习</h3>
            <p>自定义题型与数量，AI 出题并即时批改解析</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <a href="错题整理" class="card-link" target="_self">
        <div class="nav-card">
            <div class="card-icon">📓</div>
            <h3>错题整理</h3>
            <p>自动收录错题，支持反复练习与掌握标记</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

st.write("") # Spacer

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("""
    <a href="大纲生成" class="card-link" target="_self">
        <div class="nav-card">
            <div class="card-icon">📑</div>
            <h3>大纲生成</h3>
            <p>一键提炼知识库核心内容，生成复习大纲</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col5:
    st.markdown("""
    <a href="知识库管理" class="card-link" target="_self">
        <div class="nav-card">
            <div class="card-icon">🗂️</div>
            <h3>知识库管理</h3>
            <p>上传文档、构建索引，打造专属知识底座</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col6:
    st.markdown("""
    <a href="使用说明" class="card-link" target="_self">
        <div class="nav-card">
            <div class="card-icon">📖</div>
            <h3>使用说明</h3>
            <p>查看系统详细功能介绍与操作指南</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2025 [CS4314 Project, Developed by RyanStarFox and Zhou Zihan](https://github.com/RyanStarFox/CS4314_NLP_Proj2)")
