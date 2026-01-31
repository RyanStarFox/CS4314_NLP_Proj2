import streamlit as st
import os
import base64
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
    
    st.info("""本项目测试了 **Qwen** 和 **智谱清言** 的文本模型、Embedding、视觉模型。\n请参考 [阿里百炼平台（bailian.console.aliyun.com）](https://bailian.console.aliyun.com/cn-beijing/doc?tab=doc#/doc) 和 [智谱清言开放平台（docs.bigmodel.cn）](https://docs.bigmodel.cn/cn/guide/start/quick-start) 配置。\n*阿里百炼平台为新注册用户提供免费 Token，智谱清言有永久免费模型。*\n经测试，图像模型只要能够正常OCR就可以获得良好体验，文本模型建议使用高性能模型，不建议免费模型""")
    
    # Level 1 Tabs
    t_api, t_rag, t_txt, t_tool = st.tabs(["🤖 AI模型配置", "🔍 检索与RAG配置", "📄 文本处理配置", "🛠️ 工具配置"])
    
    with t_api:
        # Level 2 Tabs for API
        st_llm, st_emb, st_vl = st.tabs(["文本模型", "向量模型（Embedding）", "多模态模型"])
        
        with st_llm:
            st.markdown("#### 文本生成模型 (LLM)")
            new_settings["MODEL_NAME"] = st.text_input("模型名称 (MODEL_NAME)", value=get_val("MODEL_NAME", ""), placeholder="例如: qwen3-max, GLM-4.7-Flash", key="s_model_name")
            new_settings["OPENAI_API_KEY"] = st.text_input("API Key (OPENAI_API_KEY)", value=get_val("OPENAI_API_KEY", ""), type="password", key="s_api_key")
            new_settings["OPENAI_API_BASE"] = st.text_input("API Base URL (OPENAI_API_BASE)", value=get_val("OPENAI_API_BASE", ""), placeholder="例如: https://api.openai.com/v1", key="s_api_base")
            
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
            new_settings["OPENAI_EMBEDDING_MODEL"] = st.text_input("向量模型名称 (OPENAI_EMBEDDING_MODEL)", value=get_val("OPENAI_EMBEDDING_MODEL", ""), placeholder="例如: text-embedding-v3, text-embedding-v4", key="s_emb_model")
            new_settings["EMBEDDING_API_KEY"] = st.text_input("Embedding API Key", value=get_val("EMBEDDING_API_KEY", ""), type="password", help="留空则使用文本模型的KEY", key="s_emb_key")
            new_settings["EMBEDDING_API_BASE"] = st.text_input("Embedding API Base", value=get_val("EMBEDDING_API_BASE", ""), placeholder="例如: https://api.openai.com/v1", key="s_emb_base")

            if st.button("🧪 测试 Embedding 连接", key="btn_test_emb"):
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
                        st.error(f"❌ 连接失败: {e}")

        with st_vl:
            st.markdown("#### 多模态/图像理解模型 (VL)")
            new_settings["VL_MODEL_NAME"] = st.text_input("模型名称 (VL_MODEL_NAME)", value=get_val("VL_MODEL_NAME", ""), placeholder="例如: qwen-vl-plus, glm-4v", key="s_vl_model")
            new_settings["IMAGE_CAPTION_MODEL"] = st.text_input("课件描述模型 (IMAGE_CAPTION_MODEL)", value=get_val("IMAGE_CAPTION_MODEL", ""), placeholder="例如: qwen-vl-flash, glm-4v", key="s_img_cap_model")
            
            enable_cap = get_val("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
            new_settings["ENABLE_IMAGE_CAPTIONING"] = str(st.checkbox("开启课件自动图片描述", value=enable_cap, key="s_enable_cap"))
            
            st.divider()
            st.caption("👇 以下可选填，如果留空将默认使用文本模型的 Key/Base")
            new_settings["VL_API_KEY"] = st.text_input("独立 API Key", value=get_val("VL_API_KEY"), type="password", key="s_vl_key")
            new_settings["VL_API_BASE"] = st.text_input("独立 API Base URL", value=get_val("VL_API_BASE"), key="s_vl_base")
            
            if st.button("🧪 测试 VL 模型连接", key="btn_test_vl"):
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
        enable_hybrid = get_val("ENABLE_HYBRID_SEARCH", "True").lower() == "true"
        new_settings["ENABLE_HYBRID_SEARCH"] = str(st.checkbox("开启混合检索 (向量+关键词)", value=enable_hybrid, key="s_hybrid"))
        new_settings["HYBRID_SEARCH_ALPHA"] = st.text_input("混合检索权重 (Alpha 0~1，默认0.5)", value=get_val("HYBRID_SEARCH_ALPHA", "0.5"), key="s_hybrid_alpha")
        st.divider()
        st.markdown("##### RAG 参数")
        new_settings["TOP_K"] = st.text_input("单次检索文档数 (TOP_K，默认6)", value=get_val("TOP_K", "6"), key="s_top_k")
        new_settings["EXERCISE_TOP_K"] = st.text_input("随机出题候选池 (默认100)", value=get_val("EXERCISE_TOP_K", "100"), help="未指定主题时，从多少个相关文档中采样。", key="s_ex_top_k")
        new_settings["EXERCISE_TOP_K_TOPIC"] = st.text_input("指定主题候选池 (默认30)", value=get_val("EXERCISE_TOP_K_TOPIC", "30"), help="指定主题时，从多少个最相关的文档中采样（越小越聚焦）。", key="s_ex_top_k_topic")
        new_settings["QUIZ_CONTEXT_LENGTH"] = st.text_input("出题上下文长度 (默认2000)", value=get_val("QUIZ_CONTEXT_LENGTH", "2000"), help="截取多少字符发给 AI 用于出题。太短可能导致信息不足，太长可能导致Token消耗过大。", key="s_quiz_ctx_len")
        new_settings["MEMORY_WINDOW_SIZE"] = st.text_input("对话记忆轮数（默认10）", value=get_val("MEMORY_WINDOW_SIZE", "10"), key="s_mem_win")

    with t_txt:
        st.subheader("知识库切分参数")
        new_settings["CHUNK_SIZE"] = st.text_input("切分块大小 (默认1000)", value=get_val("CHUNK_SIZE", "1000"), key="s_chunk_size")
        new_settings["CHUNK_OVERLAP"] = st.text_input("重叠大小 (默认200)", value=get_val("CHUNK_OVERLAP", "200"), key="s_chunk_lap")
        new_settings["MAX_TOKENS"] = st.text_input("模型最大上下文 (默认4096)", value=get_val("MAX_TOKENS", "4096"), key="s_max_tok")
        new_settings["SIZE_ERROR"] = st.text_input("长度容错 (默认100)", value=get_val("SIZE_ERROR", "100"), key="s_size_err")
        new_settings["OVERLAP_ERROR"] = st.text_input("重叠容错 (默认20)", value=get_val("OVERLAP_ERROR", "20"), key="s_lap_err")
    
    with t_tool:
        st.subheader("Pandoc 配置")
        st.caption("PDF生成依赖 Pandoc。通常情况下系统会自动找到，如果报错，请在此手动指定路径。")
        st.markdown("**Pandoc 安装指南**: [pandoc.org/installing.html](https://pandoc.org/installing.html) (如无法打开请手动复制链接)")
        
        new_settings["PANDOC_PATH"] = st.text_input(
            "Pandoc 可执行文件路径", 
            value=get_val("PANDOC_PATH", ""), 
            placeholder="例如: /usr/local/bin/pandoc 或 C:\\Program Files\\Pandoc\\pandoc.exe",
            help="留空则使用系统默认 PATH 查找",
            key="s_pandoc_path"
        )
        
        if st.button("🧪 测试 Pandoc 路径", key="btn_test_pandoc"):
            import subprocess
            import os
            
            # Update PATH for the test process to match export logic
            common_paths = [
                "/opt/homebrew/bin", 
                "/usr/local/bin",    
                "/Library/TeX/texbin" 
            ]
            for p in common_paths:
                if os.path.exists(p) and p not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + p

            path_to_test = new_settings["PANDOC_PATH"] or "pandoc"
            try:
                # Construct command based on whether it is a full path or command name
                cmd = [path_to_test, "--version"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0]
                    st.success(f"✅ Pandoc 可用！\n\n版本信息: {version_line}\n\n实际路径: {path_to_test if path_to_test != 'pandoc' else '系统 PATH'}")
                else:
                    st.error(f"❌ 执行失败: 返回码 {result.returncode}\n\n错误输出: {result.stderr}")
            except FileNotFoundError:
                st.error(f"❌ 未找到命令: {path_to_test}\n请检查路径是否正确，或是否已安装 Pandoc。")
            except Exception as e:
                st.error(f"❌ 测试出错: {e}")
        
    st.divider()
    if st.button("💾 保存并应用配置", type="primary", use_container_width=True):
        current.update(new_settings)
        settings_utils.save_settings_to_env(current)
        from dotenv import load_dotenv
        load_dotenv(override=True)
        for k, v in new_settings.items():
            os.environ[k] = v
        import importlib
        import config
        importlib.reload(config)
        st.success("配置已保存并生效！")
        st.rerun()

def render_sidebar():
    # 注入 Javascript 强制移动 Logo 到侧栏最顶部 (比 CSS order 更可靠)
    # 同时处理 "Link Button" 的样式
    # 注入 CSS Hack 将 "app" 改名为 "首页"
    st.markdown("""
        <style>
        /* Rename 'app' to '首页' in Sidebar Nav */
        [data-testid="stSidebarNav"] a[href="http://localhost:8501/"] span,
        [data-testid="stSidebarNav"] a[href$="/"] span {
            display: none !important;
        }

        /* Target the specific link for the main app page */
        /* Streamlit usually names the main page file 'app' or similar */
        [data-testid="stSidebarNav"] > ul > li:first-child a::after {
            content: "🏠 首页";
            visibility: visible;
            display: block;
            padding-left: 0.5rem;
            font-weight: 600;
        }
        
        /* Fallback: Direct targeting if first-child is reliable */
        div[data-testid="stSidebarNav"] span:contains("app") {
            font-size: 0 !important;
        }
        div[data-testid="stSidebarNav"] span:contains("app")::after {
            content: "🏠 首页";
            font-size: 1rem !important;
            visibility: visible !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Background Task Monitor removed

    # Merge triggers for settings dialog to avoid duplicate calls or state confusion
    should_open = False
    
    # Trigger 1: URL Param (Consume immediately)
    if st.query_params.get("open_settings"):
        should_open = True
        # Clear param to prevent infinite re-opening on rerun
        # note: changing query params typically triggers a rerun script-wide in some versions, 
        # but here we just want to unset it mentally. 
        # Secure way: update only if present.
        if "open_settings" in st.query_params:
             del st.query_params["open_settings"]

    # Trigger 2: Button Click
    # Remove brute force BRs and use CSS flex spacer instead
    # st.sidebar.markdown("<br>" * 15, unsafe_allow_html=True)
    if st.sidebar.button("⚙️ 系统设置", use_container_width=True, key="sidebar_settings_btn"):
        should_open = True
        
    if should_open:
        settings_dialog()

def get_sidebar_css():
    return """
    <style>
    /* 1. Sidebar Global Layout */
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
        height: 100vh;
    }
    
    /* 2. Navigation Order (Second) */
    [data-testid="stSidebarNav"] {
        /* order: 2 !important;  <-- REMOVED order forcing to let elements flow naturally */
        margin-top: 0px !important; /* Reset margin top to align with natural flow, assuming logo is removed */
        padding-top: 2rem !important; /* Consistent top padding for text alignment */
        border-top: 1px solid rgba(255,255,255,0.1);
    }

    /* 3. Logo Order (First) - CSS Fallback if JS fails */
    /* Target the container of our specific logo ID */
    /* Logo CSS Removed */
    
    /* 4. Settings Button - Spacer Method (Robust) */
    /* Select the div containing the settings button AND ensure it pushes to bottom */
    [data-testid="stSidebarContent"] div:has(button[key="sidebar_settings_btn"]) {
        margin-top: auto !important;
        padding-bottom: 20px;
        order: 99 !important; /* Ensure it's last */
        width: 100%;
    }
    
    /* Style the settings button container specifically - STRONG OVERRIDE */
    .stButton button[key="sidebar_settings_btn"] {
        width: 100%;
        border-radius: 8px !important;
        margin-bottom: 1rem;
        /* Ensure border/color matches user expectation everywhere */
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        background-color: transparent !important; 
        color: var(--text-color) !important;
    }
    .stButton button[key="sidebar_settings_btn"]:hover {
        border-color: var(--primary-color) !important;
        background-color: var(--secondary-background-color) !important;
    }

    /* 5. Warning Button (Right Side) */
    /* Make the button fill the height to match the warning box */
    div[data-testid="column"]:has(button[key^="btn_"]) {
        display: flex;
        align-items: stretch;
    }
    
    .stButton button[key^="btn_"] {
        height: 100% !important;
        min-height: 3rem !important; /* Approximate height of standard warning box */
        border: 1px solid rgba(255, 75, 75, 0.2) !important;
        background-color: rgba(255, 75, 75, 0.1) !important;
        color: #ff4b4b !important;
        border-radius: 4px !important;
        margin-top: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-weight: 600 !important;
    }
    
    .stButton button[key^="btn_"]:hover {
        border-color: #ff4b4b !important;
        background-color: rgba(255, 75, 75, 0.2) !important;
    }
    
    /* Hide default divider lines in sidebar */
    [data-testid="stSidebarContent"] hr {
        display: none !important;
    }
    </style>
    """
