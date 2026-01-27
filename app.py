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

import settings_utils

@st.dialog("⚙️ 系统设置", width="large")
def settings_dialog():
    import os
    import config
    from openai import OpenAI
    current = settings_utils.load_settings_from_env()
    
    # Defaults in case env is empty
    def get_val(key, default=""): return current.get(key, default)
    
    # Container for new values
    new_settings = {}
    
    st.info("""本项目测试了 **Qwen** 和 **智谱清言** 的文本模型、Embedding、视觉模型。\n请参考 [阿里百炼平台](https://bailian.console.aliyun.com/cn-beijing/doc?tab=doc#/doc) 和 [智谱清言开放平台](https://docs.bigmodel.cn/cn/guide/start/quick-start) 配置。\n*阿里百炼平台为新注册用户提供免费 Token，智谱清言有永久免费模型。*\n经测试，图像模型只要能够正常OCR就可以获得良好体验，文本模型建议使用高性能模型，不建议免费模型""")
    
    # Level 1 Tabs
    t_api, t_rag, t_txt = st.tabs(["🤖 AI模型配置", "🔍 检索与RAG配置", "📄 文本处理配置"])
    
    with t_api:
        # Level 2 Tabs for API
        st_llm, st_emb, st_vl = st.tabs(["文本模型", "向量模型（Embedding）", "多模态模型"])
        
        with st_llm:
            st.markdown("#### 文本生成模型 (LLM)")
            new_settings["MODEL_NAME"] = st.text_input("模型名称 (MODEL_NAME)", value=get_val("MODEL_NAME", "gpt-4o"), placeholder="例如: qwen-plus, glm-4", key="s_model_name")
            new_settings["OPENAI_API_KEY"] = st.text_input("API Key (OPENAI_API_KEY)", value=get_val("OPENAI_API_KEY"), type="password", key="s_api_key")
            new_settings["OPENAI_API_BASE"] = st.text_input("API Base URL (OPENAI_API_BASE)", value=get_val("OPENAI_API_BASE", "https://api.openai.com/v1"), key="s_api_base")
            
            if st.button("🧪 测试文本模型连接", key="btn_test_llm"):
                if not new_settings["OPENAI_API_KEY"]:
                    st.error("请先填写 API Key")
                else:
                    try:
                        with st.spinner(f"正在测试 {new_settings['MODEL_NAME']} ..."):
                            import config
                            client = config.get_openai_client(api_key=new_settings["OPENAI_API_KEY"], base_url=new_settings["OPENAI_API_BASE"])
                            client.chat.completions.create(
                                model=new_settings["MODEL_NAME"],
                                messages=[{"role":"user", "content":"Hi"}],
                                max_tokens=5
                            )
                        st.success("✅ 连接成功！")
                    except Exception as e:
                        st.error(f"❌ 连接失败: {e}")
            
        with st_emb:
            st.markdown("#### 向量嵌入模型 (Embedding)")
            new_settings["OPENAI_EMBEDDING_MODEL"] = st.text_input("模型名称", value=get_val("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), key="s_emb_model")
            st.divider()
            st.caption("👇 以下可选填，如果留空将默认使用文本模型的 Key/Base")
            new_settings["EMBEDDING_API_KEY"] = st.text_input("独立 API Key", value=get_val("EMBEDDING_API_KEY"), type="password", key="s_emb_key")
            new_settings["EMBEDDING_API_BASE"] = st.text_input("独立 API Base URL", value=get_val("EMBEDDING_API_BASE"), key="s_emb_base")

            if st.button("🧪 测试 Embedding 连接", key="btn_test_emb"):
                # Fallback logic
                wk = new_settings["EMBEDDING_API_KEY"] or new_settings.get("OPENAI_API_KEY")
                wb = new_settings["EMBEDDING_API_BASE"] or new_settings.get("OPENAI_API_BASE")
                wm = new_settings["OPENAI_EMBEDDING_MODEL"]
                
                if not wk:
                     st.error("请先填写 API Key (或在文本模型中填写)")
                else:
                    try:
                        with st.spinner(f"正在测试 {wm} ..."):
                            client = config.get_openai_client(api_key=wk, base_url=wb)
                            client.embeddings.create(input=["test"], model=wm)
                        st.success("✅ 连接成功！")
                    except Exception as e:
                        import traceback
                        st.error(f"❌ 连接失败: {e}\n\nTraceback:\n{traceback.format_exc()}")
                        
                        # --- Debugging: Raw Request ---
                        st.markdown("🔍 **原始响应调试信息** (帮助排查 URL 或 模型名问题)")
                        try:
                            import httpx
                            # Construct approximate URL (Standard OpenAI is base + /embeddings)
                            debug_url = f"{wb.rstrip('/')}/embeddings"
                            st.write(f"正在尝试直接请求: `{debug_url}`")
                            
                            headers = {
                                "Authorization": f"Bearer {wk[:6]}..." if wk else "None",  # Hide full key
                                "Content-Type": "application/json"
                            }
                            # Use full key for actual request
                            real_headers = {
                                "Authorization": f"Bearer {wk}",
                                "Content-Type": "application/json"
                            }
                            json_data = {"model": wm, "input": "test"}
                            
                            r = httpx.post(debug_url, headers=real_headers, json=json_data, verify=False, timeout=10)
                            
                            st.markdown(f"**Status Code**: `{r.status_code}`")
                            st.text_area("Raw Response Body", value=r.text, height=150)
                            
                            if "<html" in r.text.lower():
                                st.error("⚠️ **严重配置错误**: 服务器返回了 HTML 页面而不是 JSON 数据。")
                                st.info("💡 **解决建议**: 您的 API Base URL 可能缺少 `/v1` 后缀。\n\n"
                                        f"尝试将 `{wb}` 改为 `{wb.rstrip('/')}/v1`")
                        except Exception as raw_e:
                            st.warning(f"无法执行原始请求调试: {raw_e}")

        with st_vl:
            st.markdown("#### 多模态/图像理解模型 (VL)")
            new_settings["VL_MODEL_NAME"] = st.text_input("模型名称 (VL_MODEL_NAME)", value=get_val("VL_MODEL_NAME", "gpt-4o"), key="s_vl_model")
            new_settings["IMAGE_CAPTION_MODEL"] = st.text_input("课件描述模型 (IMAGE_CAPTION_MODEL)", value=get_val("IMAGE_CAPTION_MODEL", "gpt-4o"), key="s_img_cap_model")
            
            enable_cap = get_val("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
            new_settings["ENABLE_IMAGE_CAPTIONING"] = str(st.checkbox("开启课件自动图片描述", value=enable_cap, key="s_enable_cap"))
            
            st.divider()
            st.caption("👇 以下可选填，如果留空将默认使用文本模型的 Key/Base")
            new_settings["VL_API_KEY"] = st.text_input("独立 API Key", value=get_val("VL_API_KEY"), type="password", key="s_vl_key")
            new_settings["VL_API_BASE"] = st.text_input("独立 API Base URL", value=get_val("VL_API_BASE"), key="s_vl_base")
            
            if st.button("🧪 测试 VL 模型连接", key="btn_test_vl"):
                # Fallback logic
                wk = new_settings["VL_API_KEY"] or new_settings.get("OPENAI_API_KEY")
                wb = new_settings["VL_API_BASE"] or new_settings.get("OPENAI_API_BASE")
                wm = new_settings["VL_MODEL_NAME"]
                
                if not wk:
                     st.error("请先填写 API Key (或在文本模型中填写)")
                else:
                    try:
                        with st.spinner(f"正在测试 {wm} ..."):
                            import config
                            client = config.get_openai_client(api_key=wk, base_url=wb)
                            # Simple chat test for VL availability
                            client.chat.completions.create(
                                model=wm,
                                messages=[{"role":"user", "content":"Hi"}],
                                max_tokens=5
                            )
                        st.success("✅ 连接成功！")
                    except Exception as e:
                        st.error(f"❌ 连接失败: {e}")

    with t_rag:
        st.subheader("混合检索 & RAG 参数")
        # 混合检索配置
        st.markdown("##### 混合检索")
        enable_hybrid = get_val("ENABLE_HYBRID_SEARCH", "True").lower() == "true"
        new_settings["ENABLE_HYBRID_SEARCH"] = str(st.checkbox("开启混合检索 (向量+关键词)", value=enable_hybrid, key="s_hybrid"))
        new_settings["HYBRID_SEARCH_ALPHA"] = st.text_input("混合检索权重 (Alpha 0~1)", value=get_val("HYBRID_SEARCH_ALPHA", "0.5"), help="1.0为纯向量，0.0为纯关键词", key="s_hybrid_alpha")
        
        st.divider()
        
        # RAG 参数
        st.markdown("##### RAG 参数")
        new_settings["TOP_K"] = st.text_input("单次检索文档数 (TOP_K)", value=get_val("TOP_K", "6"), key="s_top_k")
        new_settings["EXERCISE_TOP_K"] = st.text_input("出题候选池大小", value=get_val("EXERCISE_TOP_K", "30"), key="s_ex_top_k")
        new_settings["MEMORY_WINDOW_SIZE"] = st.text_input("对话记忆轮数", value=get_val("MEMORY_WINDOW_SIZE", "10"), key="s_mem_win")

    with t_txt:
        st.subheader("知识库切分参数")
        new_settings["CHUNK_SIZE"] = st.text_input("切分块大小 (Chunk Size)", value=get_val("CHUNK_SIZE", "1000"), key="s_chunk_size")
        new_settings["CHUNK_OVERLAP"] = st.text_input("重叠大小 (Overlap)", value=get_val("CHUNK_OVERLAP", "200"), key="s_chunk_lap")
        new_settings["MAX_TOKENS"] = st.text_input("模型最大上下文 (Max Tokens)", value=get_val("MAX_TOKENS", "4096"), key="s_max_tok")
        new_settings["SIZE_ERROR"] = st.text_input("长度容错 (Size Error)", value=get_val("SIZE_ERROR", "100"), key="s_size_err")
        new_settings["OVERLAP_ERROR"] = st.text_input("重叠容错 (Overlap Error)", value=get_val("OVERLAP_ERROR", "20"), key="s_lap_err")
        
    st.divider()
    if st.button("💾 保存并应用配置", type="primary", use_container_width=True):
        # Update current dict with new values and save to .env
        current.update(new_settings)
        settings_utils.save_settings_to_env(current)
        
        # 1. Force reload .env file to ensure consistency
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # 2. Hot reload environment variables in memory (Double assurance)
        for k, v in new_settings.items():
            os.environ[k] = v
        
        # 3. Reload config module to update module-level variables
        import importlib
        import config
        importlib.reload(config)
        
        st.success("配置已保存并生效！")
        st.rerun()

# --- Header Section ---
col_h1, col_h2 = st.columns([20, 1], vertical_alignment="center")
with col_h1:
    st.markdown('<h1 class="main-title">智能课程助教系统</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">基于 RAG 技术的全能学习助手 · 答疑 · 刷题 · 复习 · 管理</p>', unsafe_allow_html=True)

with col_h2:
    if st.button("⚙️", help="系统设置", key="btn_settings_entry"):
        settings_dialog()
    
st.markdown("---")

# --- System Check ---
import config
if not config.OPENAI_API_KEY:
    st.warning("⚠️ **未配置 API Key**：系统检测到核心配置缺失，AI 功能将无法正常使用。请点击右上角 **⚙️ 按钮** 进行配置。")

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
