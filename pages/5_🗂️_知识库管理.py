import streamlit as st
import os
import base64
import sys

# Fix path to allow importing modules from root
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

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

@st.dialog("⚠️ 确认删除")
def confirm_delete_dialog(kb_name):
    st.warning(f"确定要永久删除知识库 “{kb_name}” 吗？\n此操作将删除所有文件和索引，且不可恢复。")
    if st.button("确认删除", type="primary"):
        # Re-init manager to ensure context
        manager = KBManager()
        if manager.delete_kb(kb_name):
            st.success(f"已删除 {kb_name}")
            st.rerun()
        else:
            st.error("删除失败")

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
                # Use dynamic key to allow clearing after upload
                uploader_key_name = f"uploader_key_{kb}"
                current_key_val = st.session_state.get(uploader_key_name, 0)
                
                uploaded_files = st.file_uploader(
                    f"上传文件到 {kb}", 
                    accept_multiple_files=True, 
                    type=["pdf", "pptx", "docx", "md", "txt"],
                    key=f"up_{kb}_{current_key_val}"
                )

                if uploaded_files:
                    if st.button("确认上传并处理", key=f"btn_up_{kb}"):
                        with st.spinner("正在处理文件并更新向量数据库（请勿关闭页面）..."):
                            for uf in uploaded_files:
                                kb_manager.add_file(kb, uf)
                        
                        st.success("✅ 上传并处理成功！")
                        
                        # Increment key to reset uploader component
                        st.session_state[uploader_key_name] = current_key_val + 1
                        time.sleep(1.5)
                        st.rerun()

            with col2:
                st.markdown("#### 操作")
                
                if st.button("📂 打开本地文件夹", key=f"open_dir_{kb}", use_container_width=True):
                    kb_path = os.path.join(kb_manager.base_dir, kb)
                    import subprocess, platform
                    try:
                        if platform.system() == "Darwin":
                            subprocess.Popen(["open", kb_path])
                        elif platform.system() == "Windows":
                            os.startfile(kb_path)
                        else:
                            subprocess.Popen(["xdg-open", kb_path])
                        st.toast("已打开文件夹，变更文件后请点击【⚡️ 更新增量索引】")
                    except Exception as e:
                        st.error(f"打开文件夹失败: {e}")
                
                if st.button("⚡️ 更新增量索引 (推荐)", key=f"sync_{kb}", use_container_width=True, help="仅处理新增或删除的文件，速度更快"):
                     with st.spinner("正在扫描并同步文件变更..."):
                         added, removed = kb_manager.update_kb_index(kb)
                     if added == 0 and removed == 0:
                         st.info("索引已是最新")
                     else:
                         st.success(f"✅ 同步完成：新增 {added} 个，移除 {removed} 个")
                     time.sleep(1.5)
                     st.rerun()

                if st.button("🔄 重建知识库索引 (全量)", key=f"reindex_{kb}", use_container_width=True, help="清空库并重新扫描所有文件（耗时较长）"):
                     with st.spinner("正在重建索引（文件较多时可能需要几分钟，请耐心等待）..."):
                         kb_manager.rebuild_kb_index(kb)
                     st.success("✅ 索引已全量重建")
                     time.sleep(1.5)
                     st.rerun()

                st.markdown("---")

                if st.button("🗑️ 删除整个知识库", key=f"del_kb_{kb}", type="primary", use_container_width=True):
                    confirm_delete_dialog(kb)

