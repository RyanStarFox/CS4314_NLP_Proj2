import streamlit as st

st.set_page_config(page_title="使用说明", page_icon="logo.webp", layout="wide")

# Custom CSS for card styling
# Initialize navigation state
if 'help_section' not in st.session_state:
    st.session_state.help_section = None

# Base CSS (Always applies)
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    
    .instruction-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 10px;
        width: 100%;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: pointer;
    }
    
    .instruction-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #FF4B4B;
    }
    
    .card-icon {
        font-size: 2.5rem;
        margin-bottom: 8px;
        display: block;
    }
    
    .card-title {
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 6px;
        color: var(--text-color);
    }
    
    .card-desc {
        font-size: 0.85rem;
        color: #888;
        line-height: 1.35;
        min-height: 3.2em;
    }
    
    .feature-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 20px 0;
        color: #FF4B4B;
    }
    
    .step-item {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 10px 15px;
        border-radius: 6px;
        margin-bottom: 8px;
        border-left: 3px solid #FF4B4B;
    }

</style>
""", unsafe_allow_html=True)

# Conditional CSS for Home View Only (Fixed Layout)
if st.session_state.help_section is None:
    st.markdown("""
    <style>
        /* 核心布局调整：消除滚动条 - 仅在导航页生效 */
        .block-container { 
            padding-bottom: 0rem;
        }
        
        /* 隐藏 Streamlit 自带页脚和 Header */
        footer {display: none;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Header
st.title("📚 使用说明书")
st.caption("点击下方卡片查看详细功能说明")
st.markdown("---")

# Main Navigation Grid
if st.session_state.help_section is None:
    # Feature configurations
    features = [
        {
            "id": "ai_tutor",
            "icon": "🧠",
            "title": "智能助教",
            "desc": "基于 RAG 的智能问答助手，解答课程疑问，提供精准的文献来源追踪"
        },
        {
            "id": "practice",
            "icon": "📝",
            "title": "做题练习",
            "desc": "随机抽取题库题目进行自测，支持选择题与自动判分，实时反馈此题解析"
        },
        {
            "id": "mistakes",
            "icon": "📓",
            "title": "错题整理",
            "desc": "自动或手动记录错题，支持 OCR 图片识别录入，提供个性化复习与归档管理"
        },
        {
            "id": "outline",
            "icon": "📑",
            "title": "大纲生成",
            "desc": "AI 自动分析知识库生成的复习大纲，支持导出 PDF 和个性化定制"
        },
        {
            "id": "kb",
            "icon": "📚",
            "title": "知识库管理",
            "desc": "上传和管理课程资料（PDF/PPT/Word），构建专属的 AI 知识索引"
        },
        {
            "id": "settings",
            "icon": "⚙️",
            "title": "系统设置",
            "desc": "API 配置、模型选择、界面主题调整（开发中...）"
        }
    ]

    # Render grid (3 columns)
    cols = st.columns(3)
    for i, feature in enumerate(features):
        with cols[i % 3]:
            # Create a clickable card using st.button
            # Note: We use a little CSS hack to make the button look like a card
            # Or simpler: Just use container + button
            with st.container(border=True):
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 10px;">{feature['icon']}</div>
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 5px;">{feature['title']}</div>
                    <div style="color: #666; font-size: 0.9rem; min-height: 40px;">{feature['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("查看详情", key=f"btn_{feature['id']}", use_container_width=True):
                    st.session_state.help_section = feature['id']
                    st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.8rem;">
        CS4314 智能课程助教系统 v2.0
    </div>
    """, unsafe_allow_html=True)

else:
    # Detail View
    if st.button("← 返回功能列表"):
        st.session_state.help_section = None
        st.rerun()
    
    section = st.session_state.help_section
    
    if section == "ai_tutor":
        st.header("🧠 智能助教使用指南")
        st.info("核心功能：基于课程资料库回答你的任何问题")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 1. 提问方式")
            st.write("在输入框中直接输入你的问题，例如：")
            st.code("Transformer 的自注意力机制是如何工作的？")
            st.write("或者上传相关的图片（如课件截图），AI 会结合图片内容进行解答。")
            
            st.markdown("### 2. 查看来源")
            st.write("AI 的回答会附带【参考来源】，点击可以查看该知识点出自哪份文档的哪一页，确保信息的准确性。")
            
        with c2:
            st.markdown("### 3. 多轮对话")
            st.write("你可以对 AI 的回答进行追问，系统会记住上下文语境。")
            st.write("例如：")
            st.code("那如果不使用位置编码会怎么样？")

    elif section == "practice":
        st.header("📝 做题练习使用指南")
        st.info("核心功能：随机抽题，自我检测")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🎯 开始练习")
            st.write("1. 选择要练习的知识库或题库")
            st.write("2. 系统会随机抽取一道选择题")
            st.write("3. 点击选项进行作答")
        with c2:
            st.markdown("### 📊 反馈机制")
            st.write("- **答对**：显示绿色提示，加深记忆")
            st.write("- **答错**：显示红色提示，并自动加入错题本")
            st.write("- **解析**：无论对错，下方都会显示详细的题目解析")

    elif section == "mistakes":
        st.header("📓 错题整理使用指南")
        st.info("核心功能：管理你的知识盲区")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 1. 录入错题")
            st.write("除了自动录入，你还可以：")
            st.markdown("""
            - 点击 **"➕ 手动添加错题"**
            - **上传图片**：AI 自动 OCR 识别
            - **填写详情**：微调题目和答案内容
            - **保存**：添加到错题本
            """)
        
        with c2:
            st.markdown("### 2. 复习模式")
            st.write("进入错题本，根据掌握程度推荐复习：")
            st.write("- **陌生度高**：优先复习")
            st.write("- **已掌握**：移入“已归档”区域")

    elif section == "outline":
        st.header("📑 大纲生成使用指南")
        st.info("核心功能：一键生成复习大纲")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🚀 如何生成")
            st.write("1. 选择一个知识库（如：Lecture 1-5）")
            st.write("2. 点击 **“生成大纲”** 按钮")
            st.write("3. 等待约 30-60 秒，AI 生成结构化大纲")
        
        with c2:
            st.markdown("### ✏️ 个性化定制")
            st.write("对大纲不满意？")
            st.write("在右侧栏输入修改意见，例如：")
            st.code("请增加关于 BERT 模型的详细小节")
            st.write("提交后 AI 会在后台重新调整。")

    elif section == "kb":
        st.header("📚 知识库管理指南")
        st.info("核心功能：管理 AI 的大脑数据")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📤 上传文档")
            st.write("- 支持格式：PDF, PPTX, DOCX, TXT, MD")
            st.write("- 建议：文件命名清晰（如 `Lecture01.pdf`）")
        
        with c2:
            st.markdown("### 🔄 建立索引")
            st.write("上传后，必须点击 **“重建索引”** 按钮。")
            st.write("这一步将文档转化为向量数据，是智能问答的基础。")

    elif section == "settings":
        st.header("⚙️ 系统设置")
        st.warning("⚠️ 此功能模块正在开发中")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🔜 未来功能")
            st.markdown("""
            - 🔑 **API Key 管理**：自定义 OpenAI/DeepSeek Key
            - 🎨 **主题切换**：更多配色方案
            """)
            
        with c2:
            st.markdown("### 🛠️ 高级配置")
            st.markdown("""
            - 🤖 **模型选择**：切换 GPT-4, Claude 3 或本地模型
            - ☁️ **云端同步**：多设备同步学习进度
            """)
        
        st.caption("目前请通过修改项目根目录下的 `.env` 文件进行配置。")
