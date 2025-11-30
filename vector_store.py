import os
from typing import List, Dict

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from tqdm import tqdm

from config import (
    VECTOR_DB_PATH,
    COLLECTION_NAME,
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    OPENAI_EMBEDDING_MODEL,
    TOP_K,
)


class VectorStore:

    def __init__(
        self,
        db_path: str = VECTOR_DB_PATH,
        collection_name: str = COLLECTION_NAME,
        api_key: str = OPENAI_API_KEY,
        api_base: str = OPENAI_API_BASE,
    ):
        self.db_path = db_path
        self.collection_name = collection_name

        # 初始化OpenAI客户端
        self.client = OpenAI(api_key=api_key, base_url=api_base)

        # 初始化ChromaDB
        os.makedirs(db_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=db_path, settings=Settings(anonymized_telemetry=False)
        )

        # 获取或创建collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name, metadata={"description": "课程材料向量数据库"}
        )

    def get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示

        TODO: 使用OpenAI API获取文本的embedding向量

        """
        # 调用OpenAI API获取embedding
        response = self.client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text
        )
        # 返回embedding向量
        return response.data[0].embedding

    def add_documents(self, chunks: List[Dict[str, str]]) -> None:
        """添加文档块到向量数据库
        TODO: 实现文档块添加到向量数据库
        要求：
        1. 遍历文档块
        2. 获取文档块内容
        3. 获取文档块元数据
        5. 打印添加进度
        """
        if not chunks:
            return
        documents = []
        embeddings = []
        metadatas = []
        ids = []

        # 遍历文档块，准备数据
        for chunk in tqdm(chunks, desc="添加文档到向量数据库", unit="块"):
            # 获取文档块内容
            content = chunk.get("content", "")
            if not content:
                continue

            # 获取文档块元数据
            metadata = {
                "filename": chunk.get("filename", "unknown"),
                "filepath": chunk.get("filepath", ""),
                "filetype": chunk.get("filetype", ""),
                "page_number": str(chunk.get("page_number", 0)),
                "chunk_id": str(chunk.get("chunk_id", 0)),
            }

            # 生成唯一ID：包含filename、page_number和chunk_id以确保唯一性
            chunk_id = chunk.get("chunk_id", 0)
            page_number = chunk.get("page_number", 0)
            filename = chunk.get("filename", "unknown")
            # 对于PDF和PPT，page_number很重要；对于其他文件，page_number通常是0
            unique_id = f"{filename}_p{page_number}_c{chunk_id}"

            # 获取embedding向量
            embedding = self.get_embedding(content)

            documents.append(content)
            embeddings.append(embedding)
            metadatas.append(metadata)
            ids.append(unique_id)

        # 批量添加到ChromaDB
        if documents:
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"\n成功添加 {len(documents)} 个文档块到向量数据库")

    def search(self, query: str, top_k: int = TOP_K) -> List[Dict]:
        """搜索相关文档

        TODO: 实现向量相似度搜索
        要求：
        1. 首先获取查询文本的embedding向量（调用self.get_embedding）
        2. 使用self.collection进行向量搜索, 得到top_k个结果
        3. 格式化返回结果，每个结果包含：
           - content: 文档内容
           - metadata: 元数据（文件名、页码等）
        4. 返回格式化的结果列表
        """
        embedding = self.get_embedding(query)
        results = self.collection.query(
            query_embeddings=embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def clear_collection(self) -> None:
        """清空collection"""
        self.chroma_client.delete_collection(name=self.collection_name)
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name, metadata={"description": "课程向量数据库"}
        )
        print("向量数据库已清空")

    def get_collection_count(self) -> int:
        """获取collection中的文档数量"""
        return self.collection.count()
