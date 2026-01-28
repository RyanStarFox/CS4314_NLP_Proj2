import streamlit as st
import os
import base64
import streamlit.components.v1 as components
import time
from kb_manager import KBManager
import ui_components

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

st.set_page_config(page_title="知识库管理", page_icon="logo.png", layout="wide")

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

st.title("🗂️ 知识库管理")

kb_manager = KBManager()
kbs = kb_manager.list_kbs()

# --- Create New KB ---
with st.expander("➕ 新建知识库", expanded=False):
    new_kb_name = st.text_input("知识库名称", placeholder="例如: MyKnowledgeBase")
    if st.button("创建"):
        if new_kb_name:
            if kb_manager.create_kb(new_kb_name):
                st.success(f"知识库 {new_kb_name} 创建成功！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("创建失败：知识库已存在或名称非法")
        else:
            st.warning("请输入名称")

st.markdown("---")

# --- Manage Existing KBs ---
if not kbs:
    st.info("暂无知识库")
else:
    st.markdown("### 现有知识库")
    
    # 按照您的要求，每个一级子文件夹（如 cs_math, docx_test 等）都是一个独立的知识库
    for kb in kbs:
        with st.expander(f"📁 {kb}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                files = kb_manager.list_files(kb)
                st.markdown(f"**包含文档 ({len(files)}):**")
                for f in files:
                    c1, c2 = st.columns([4, 1])
                    c1.text(f"📄 {f}")
                    if c2.button("🗑️", key=f"del_file_{kb}_{f}"):
                        kb_manager.delete_file(kb, f)
                        st.rerun()
                
                st.markdown("---")
                st.markdown("**📤 上传新文档:**")
                st.caption("💡 支持格式：PDF, PPTX, DOCX, MD, TXT")
                uploaded_files = st.file_uploader(
                    f"上传文件到 {kb}", 
                    accept_multiple_files=True, 
                    type=["pdf", "pptx", "docx", "md", "txt"],
                    key=f"up_{kb}"
                )
                
                if uploaded_files:
                    if st.button("确认上传并处理", key=f"btn_up_{kb}"):
                        with st.spinner("正在处理文件并更新向量数据库..."):
                            for uf in uploaded_files:
                                kb_manager.add_file(kb, uf)
                        st.success("上传成功！")
                        time.sleep(1)
                        st.rerun()

            with col2:
                st.markdown("#### 操作")
                if st.button("🗑️ 删除整个知识库", key=f"del_kb_{kb}", type="primary"):
                    kb_manager.delete_kb(kb)
                    st.rerun()
                
                if st.button("🔄 重建索引", key=f"reindex_{kb}"):
                     with st.spinner("重建中..."):
                         kb_manager.rebuild_kb_index(kb)
                     st.success("索引已重建")

