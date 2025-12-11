import streamlit as st
import time
from rag_agent import RAGAgent
from kb_manager import KBManager
import base64

st.set_page_config(page_title="大纲生成", page_icon="logo.webp", layout="wide")

st.title("📑 智能大纲生成")

kb_manager = KBManager()
kbs = kb_manager.list_kbs()

if not kbs:
    st.warning("⚠️ 请先在【知识库管理】中添加知识库")
    st.stop()

selected_kb = st.selectbox("📚 选择知识库", kbs)

if st.button("🚀 生成复习大纲", type="primary"):
    # Auto-vectorization check
    temp_agent = RAGAgent(kb_name=selected_kb)
    count = temp_agent.vector_store.get_collection_count()
    if count == 0:
        files = kb_manager.list_files(selected_kb)
        if files:
            st.info(f"📚 检测到知识库 '{selected_kb}' 尚未向量化，正在首次处理，这可能需要比较久的时间...")
            with st.spinner("正在进行向量化处理，请耐心等待..."):
                kb_manager.rebuild_kb_index(selected_kb)
            st.success("✅ 向量化完成！")
        else:
            st.error("⚠️ 该知识库为空，请先在【知识库管理】中上传文档。")
            st.stop()

    with st.spinner("正在分析知识库并生成大纲（可能需要几十秒）..."):
        try:
            agent = RAGAgent(kb_name=selected_kb)
            outline_md = agent.generate_outline()
            st.session_state.outline_result = outline_md
            st.success("✅ 大纲生成完毕！")
        except Exception as e:
            st.error(f"生成失败: {e}")

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
    st.markdown("### 📝 预览")
    st.markdown(outline)
    st.markdown("---")


