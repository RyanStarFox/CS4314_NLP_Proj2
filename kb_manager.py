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

    def add_file(self, kb_name, uploaded_file):
        kb_path = os.path.join(self.base_dir, kb_name)
        if not os.path.exists(kb_path):
            return False
        
        file_path = os.path.join(kb_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Ingest just this file or rebuild KB?
        # Rebuilding is safer for now to keep sync.
        self.rebuild_kb_index(kb_name)
        return True

    def delete_file(self, kb_name, filename):
        file_path = os.path.join(self.base_dir, kb_name, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            self.rebuild_kb_index(kb_name)
            return True
        return False

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

