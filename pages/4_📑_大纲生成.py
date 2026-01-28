import streamlit as st
import time
import base64
import os
import streamlit.components.v1 as components
from kb_manager import KBManager
import ui_components
from rag_agent import RAGAgent

from question_db import QuestionDB # Import DB

# Inject JS for keyboard shortcut (Cmd/Ctrl + ,)
components.html("""
<script>
document.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && (e.key === ',' || e.keyCode === 188)) {
        e.preventDefault();
        window.top.postMessage({type: 'open-settings'}, '*');
    }
}, true);
</script>
""", height=0, width=0)

st.set_page_config(page_title="智能大纲生成", page_icon="logo.png", layout="wide")

st.markdown(f"""
<style>
    .block-container {{ padding-top: 2rem; }}
    img {{ image-rendering: -webkit-optimize-contrast; }}
    
    /* Sidebar Styles from ui_components */
    {ui_components.get_sidebar_css()}
</style>
""", unsafe_allow_html=True)

# sidebar
ui_components.render_sidebar()

st.title("📑 智能大纲生成")

kb_manager = KBManager()
question_db = QuestionDB() # Initialize DB
kbs = kb_manager.list_kbs()

if not kbs:
    st.warning("⚠️ 请先在【知识库管理】中添加知识库")
    st.stop()

selected_kb = st.selectbox("📚 选择知识库", kbs)

def run_background_generate(kb_name):
    """后台生成函数"""
    try:
        # 使用独立的 DB 和 Agent 实例
        db = QuestionDB()
        agent = RAGAgent(kb_name=kb_name)
        # 记录开始处理
        db.save_outline(kb_name, "（大纲正在后台生成中，请耐心等待...）", status="processing")
        
        # 执行生成
        outline_md = agent.generate_outline()
        
        # 记录完成
        db.save_outline(kb_name, outline_md, status="completed")
    except Exception as e:
        # 记录失败
        db = QuestionDB()
        db.save_outline(kb_name, f"❌ 生成失败: {str(e)}", status="failed")

# Check for existing outline and status
existing_outline = question_db.get_outline(selected_kb)
current_status = existing_outline.get("status") if existing_outline else None

# Handle UI based on status
if current_status == "processing":
    st.info("⏳ **大纲正在生成/修改中...** 您可以先去其他页面看看，处理过程可能需要 30-60 秒。")
    if st.button("🔄 刷新查看状态", use_container_width=True):
        st.rerun()
    st.stop()

if existing_outline and current_status == "completed" and "outline_result" not in st.session_state:
    st.session_state.outline_result = existing_outline["content"]
    st.info(f"📅 已加载历史大纲 (生成时间: {time.strftime('%Y-%m-%d %H:%M', time.localtime(existing_outline['timestamp']))})")

if current_status == "failed":
    st.error(existing_outline["content"])

col_gen, _ = st.columns([1, 1])
with col_gen:
    btn_label = "🚀 生成/重新生成大纲" if current_status != "completed" else "🔄 重新生成大纲"
    if st.button(btn_label, type="primary", use_container_width=True):
        # Auto-vectorization check
        temp_agent = RAGAgent(kb_name=selected_kb)
        count = temp_agent.vector_store.get_collection_count()
        if count == 0:
            files = kb_manager.list_files(selected_kb)
            if files:
                st.info(f"📚 检测到知识库 '{selected_kb}' 尚未向量化，正在首次处理...")
                with st.spinner("正在向量化..."):
                    kb_manager.rebuild_kb_index(selected_kb)
            else:
                st.error("⚠️ 该知识库为空，请先上传文档。")
                st.stop()
        
        # Start background thread
        import threading
        thread = threading.Thread(target=run_background_generate, args=(selected_kb,))
        thread.daemon = True
        thread.start()
        
        # Set local status to avoid race condition before first DB write in thread
        question_db.save_outline(selected_kb, "（生成中...）", status="processing")
        st.success("✅ 已开始后台生成！请在几秒后手动刷新页面。")
        time.sleep(1) # Give thread a moment to start
        st.rerun()

if "outline_result" in st.session_state:
    outline = st.session_state.outline_result
    
    st.markdown("### 📥 下载大纲")
    col1, col2 = st.columns(2)
    
    # Download Markdown
    with col1:
        st.download_button(
            label="⬇️ 下载 Markdown (.md)",
            data=outline,
            file_name=f"{selected_kb}_复习大纲.md",
            mime="text/markdown",
            use_container_width=True,
            type="secondary"
        )
    
    # Download PDF
    with col2:
        if st.button("⬇️ 下载 PDF (.pdf)", use_container_width=True):
            import subprocess
            import tempfile
            import os
            
            pdf_bytes = b""
            
            try:
                # Create temporary files for markdown input and PDF output
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as md_file:
                    md_file.write(outline)
                    md_path = md_file.name
                
                pdf_path = md_path.replace('.md', '.pdf')
                
                # Use pandoc to convert Markdown to PDF
                # xelatex engine supports Chinese and LaTeX math
                cmd = [
                    'pandoc',
                    md_path,
                    '-o', pdf_path,
                    '--pdf-engine=xelatex',
                    '-V', 'CJKmainfont=Heiti SC',  # macOS 中文字体
                    '-V', 'geometry:margin=2.5cm',
                    '-V', 'fontsize=11pt',
                    '--highlight-style=tango',  # 代码高亮
                ]
                
                with st.spinner("正在使用 Pandoc 生成 PDF（支持完整 Markdown + LaTeX）..."):
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0 and os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    st.success("✅ PDF 生成成功！")
                else:
                    error_msg = result.stderr if result.stderr else "未知错误"
                    st.error(f"Pandoc 转换失败: {error_msg}")
                    
                    # 如果 xelatex 失败，尝试使用 pdflatex 作为回退
                    if "xelatex" in error_msg.lower() or "not found" in error_msg.lower():
                        st.info("正在尝试使用 pdflatex 引擎...")
                        cmd_fallback = [
                            'pandoc',
                            md_path,
                            '-o', pdf_path,
                            '--pdf-engine=pdflatex',
                            '-V', 'geometry:margin=2.5cm',
                        ]
                        result_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=120)
                        if result_fb.returncode == 0 and os.path.exists(pdf_path):
                            with open(pdf_path, 'rb') as f:
                                pdf_bytes = f.read()
                            st.success("✅ PDF 生成成功（使用 pdflatex，中文可能显示异常）！")
                        else:
                            st.error(f"pdflatex 也失败了: {result_fb.stderr}")
                
                # Cleanup temp files
                if os.path.exists(md_path):
                    os.unlink(md_path)
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
                    
            except FileNotFoundError:
                st.error("❌ 未找到 pandoc 命令。请确保已安装 pandoc 和 LaTeX (如 MacTeX 或 BasicTeX)。")
            except subprocess.TimeoutExpired:
                st.error("❌ PDF 生成超时，请重试。")
            except Exception as e:
                st.error(f"PDF 生成出错: {e}")

            if pdf_bytes:
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="{selected_kb}_outline.pdf" style="text-decoration:none; color:inherit; display:block; text-align:center; padding:0.5rem; background-color:#f0f2f6; border-radius:0.5rem; border:1px solid rgba(49, 51, 63, 0.2);">📄 点击这里保存 PDF 文件</a>'
                st.markdown(href, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📝 预览与修改")
    
    tab_view, tab_refine = st.tabs(["👁️ 预览大纲", "✏️ 修改大纲"])
    
    with tab_view:
        st.markdown(outline)
        
    with tab_refine:
        st.info("💡 如果对大纲不满意，可以提出修改意见让 AI 进行调整（例如：'增加关于动态规划的章节' 或 '精简第一章的内容'）。")
        user_feedback = st.text_area("请输入你的修改意见：", height=100)
        if st.button("✨ 提交修改意见", type="primary"):
            if user_feedback.strip():
                # 后台修改函数
                def run_background_refine(kb_name, current_outline, feedback):
                    try:
                        db = QuestionDB()
                        db.save_outline(kb_name, "（正在根据您的意见调整大纲...）", status="processing")
                        
                        agent = RAGAgent(kb_name=kb_name)
                        new_outline = agent.refine_outline(current_outline, feedback)
                        
                        db.save_outline(kb_name, new_outline, status="completed")
                    except Exception as e:
                        db = QuestionDB()
                        db.save_outline(kb_name, f"❌ 修改失败: {str(e)}", status="failed")
                
                # 启动后台线程
                import threading
                thread = threading.Thread(target=run_background_refine, args=(selected_kb, outline, user_feedback))
                thread.daemon = True
                thread.start()
                
                question_db.save_outline(selected_kb, "（修改中...）", status="processing")
                st.success("✅ 已开始后台修改！请稍后刷新页面查看结果。")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("请先输入修改意见。")

    st.markdown("---")


