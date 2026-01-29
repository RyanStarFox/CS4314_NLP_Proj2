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

    def save_uploaded_file(self, kb_name, uploaded_file):
        """仅保存上传文件到磁盘（不建立索引）"""
        kb_path = os.path.join(self.base_dir, kb_name)
        if not os.path.exists(kb_path):
            os.makedirs(kb_path)
        
        file_path = os.path.join(kb_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return uploaded_file.name

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

    def import_from_directory(self, kb_name, source_dir):
        """递归导入本地文件夹内容到知识库"""
        kb_path = os.path.join(self.base_dir, kb_name)
        if not os.path.exists(source_dir):
            return 0, 0 # files, errors
        
        supported_exts = {'.pdf', '.pptx', '.docx', '.md', '.txt'}
        count = 0
        errors = 0
        
        # 递归遍历源目录
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                # 忽略隐藏文件
                if file.startswith('.'):
                    continue
                    
                if ext in supported_exts:
                    try:
                        src_path = os.path.join(root, file)
                        # 计算相对路径，以保持目录结构
                        rel_path = os.path.relpath(src_path, source_dir)
                        dst_path = os.path.join(kb_path, rel_path)
                        
                        # 确保目标子目录存在
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        
                        # 复制文件
                        shutil.copy2(src_path, dst_path)
                        
                        # 添加到索引
                        # 注意：为了避免每次都重新加载模型，这里可以考虑批量添加，
                        # 但为了代码简单性和复用现有逻辑，暂时逐个添加。
                        # add_single_file_to_index 会处理 DocumentLoader 初始化
                        self.add_single_file_to_index(kb_name, rel_path)
                        count += 1
                        print(f"成功导入: {rel_path}")
                    except Exception as e:
                        print(f"导入文件失败 {file}: {e}")
                        errors += 1
        return count, errors

    def update_kb_index(self, kb_name):
        """增量更新知识库索引（仅处理新增和删除的文件）
        
        Returns:
            tuple: (added_count, removed_count)
        """
        kb_path = os.path.join(self.base_dir, kb_name)
        
        # 1. 获取磁盘上的所有文件 (绝对路径集合)
        disk_files = set()
        supported_exts = {'.pdf', '.pptx', '.docx', '.md', '.txt'}
        
        if os.path.exists(kb_path):
            for root, dirs, files in os.walk(kb_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if not f.startswith('.') and ext in supported_exts:
                        disk_files.add(os.path.abspath(os.path.join(root, f)))
        
        # 2. 获取数据库中的所有文件 (Metadata中的filepath)
        vector_store = VectorStore(collection_name=kb_name)
        db_files = vector_store.get_existing_files()
        
        # 3. 计算差异 (Diff)
        to_add = disk_files - db_files
        to_remove = db_files - disk_files
        
        print(f"[{kb_name}] 增量更新检测: 需新增 {len(to_add)}, 需删除 {len(to_remove)}")
        
        # 4. 执行更新
        count_add = 0
        count_rem = 0
        
        # 处理删除
        if to_remove:
            print("正在清理已删除文件的索引...")
            for fp in to_remove:
                if fp:
                    vector_store.delete_documents_by_filepath(fp)
                    count_rem += 1
        
        # 处理新增
        if to_add:
            print("正在索引新文件...")
            for fp in to_add:
                try:
                    # add_single_file_to_index 需要相对于 kb 目录的路径
                    rel_path = os.path.relpath(fp, kb_path)
                    self.add_single_file_to_index(kb_name, rel_path)
                    count_add += 1
                except Exception as e:
                    print(f"添加文件失败 {fp}: {e}")
                
        return count_add, count_rem

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

