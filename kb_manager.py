import os
import shutil
from document_loader import DocumentLoader
from text_splitter import TextSplitter
from vector_store import VectorStore
from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, SIZE_ERROR, OVERLAP_ERROR

class KBManager:
    def __init__(self, base_dir=DATA_DIR):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def list_kbs(self):
        # 列出所有包含文件的子目录，或者直接将所有第一级子目录作为 KB
        # 排除 user_progress.json 等非目录
        # DEBUG LOGIC ADDED
        print(f"DEBUG: Checking KBs in {os.path.abspath(self.base_dir)}")
        if not os.path.exists(self.base_dir):
            print(f"DEBUG: {self.base_dir} does not exist")
            return []
            
        items = os.listdir(self.base_dir)
        print(f"DEBUG: Found items: {items}")
        
        kbs = [d for d in items if os.path.isdir(os.path.join(self.base_dir, d)) and not d.startswith('.')]
        print(f"DEBUG: Filtered KBs: {kbs}")
        return sorted(kbs)

    def create_kb(self, name):
        path = os.path.join(self.base_dir, name)
        if not os.path.exists(path):
            os.makedirs(path)
            return True
        return False

    def delete_kb(self, name):
        path = os.path.join(self.base_dir, name)
        if os.path.exists(path):
            shutil.rmtree(path)
            # Remove from vector store
            try:
                vs = VectorStore(collection_name=name)
                vs.delete_collection(name)
            except Exception as e:
                print(f"Error deleting collection: {e}")
            return True
        return False

    def list_files(self, kb_name):
        path = os.path.join(self.base_dir, kb_name)
        file_list = []
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    if not f.startswith('.'):
                        # Show relative path from KB root
                        rel_path = os.path.relpath(os.path.join(root, f), path)
                        file_list.append(rel_path)
        return sorted(file_list)
    
    def get_kb_total_size(self, kb_name):
        """获取知识库的文件总大小（单位：字节）"""
        path = os.path.join(self.base_dir, kb_name)
        total_size = 0
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    if not f.startswith('.'):
                        file_path = os.path.join(root, f)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError:
                            pass  # 忽略无法访问的文件
        return total_size

    def add_file(self, kb_name, uploaded_file):
        """添加文件到知识库（增量更新模式）"""
        kb_path = os.path.join(self.base_dir, kb_name)
        if not os.path.exists(kb_path):
            return False
        
        file_path = os.path.join(kb_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 使用增量更新，只处理新上传的文件
        self.add_single_file_to_index(kb_name, uploaded_file.name)
        return True

    def delete_file(self, kb_name, filename):
        """删除文件（增量更新模式）"""
        file_path = os.path.join(self.base_dir, kb_name, filename)
        if os.path.exists(file_path):
            # 先从向量数据库中删除该文件的所有文档块
            vector_store = VectorStore(collection_name=kb_name)
            vector_store.delete_documents_by_file(filename)
            
            # 然后删除文件
            os.remove(file_path)
            return True
        return False
    
    def add_single_file_to_index(self, kb_name, filename):
        """将单个文件添加到向量数据库（增量更新）
        
        Args:
            kb_name: 知识库名称
            filename: 文件名（相对于知识库目录）
        """
        kb_path = os.path.join(self.base_dir, kb_name)
        file_path = os.path.join(kb_path, filename)
        
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return
        
        # 初始化组件
        loader = DocumentLoader(data_dir=kb_path)
        splitter = TextSplitter(
            chunk_size=CHUNK_SIZE, 
            chunk_overlap=CHUNK_OVERLAP, 
            size_error=SIZE_ERROR, 
            overlap_error=OVERLAP_ERROR
        )
        vector_store = VectorStore(collection_name=kb_name)
        
        # 先删除该文件的旧数据（如果存在）
        vector_store.delete_documents_by_file(filename)
        
        # 加载并处理单个文件
        print(f"正在处理文件: {filename}")
        documents = loader.load_document(file_path)
        
        if documents:
            chunks = splitter.split_documents(documents)
            vector_store.add_documents(chunks)
            print(f"文件 {filename} 已成功添加到向量数据库")
        else:
            print(f"文件 {filename} 未能提取到内容")

    def rebuild_kb_index(self, kb_name):
        kb_path = os.path.join(self.base_dir, kb_name)
        
        loader = DocumentLoader(data_dir=kb_path)
        splitter = TextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, size_error=SIZE_ERROR, overlap_error=OVERLAP_ERROR)
        
        # Initialize VectorStore with the KB name as collection name
        vector_store = VectorStore(collection_name=kb_name)
        
        # Clear existing
        vector_store.clear_collection()
        
        documents = loader.load_all_documents()
        if documents:
            chunks = splitter.split_documents(documents)
            vector_store.add_documents(chunks)

