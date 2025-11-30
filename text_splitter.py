from typing import List, Dict
from tqdm import tqdm


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int, size_error: int, overlap_error: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap  
        self.size_error = size_error
        self.overlap_error = overlap_error

    def split_text(self, text: str) -> List[str]:
        """将文本切分为块

        TODO: 实现文本切分算法
        要求：
        1. 将文本按照chunk_size切分为多个块
        2. 相邻块之间要有chunk_overlap的重叠（用于保持上下文连续性）
        3. 尽量在句子边界处切分（查找句子结束符：。！？.!?\n\n）
        4. 返回切分后的文本块列表
        """
        if not text:
            return []
        chunks = []
        text_len = len(text)
        start_idx = 0
        
        # 句子边界标记
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n\n']
        
        while start_idx < text_len:
            # 确定开始点
            if start_idx == 0:
                # 第一个chunk，开始点就是开头
                chunk_start = 0
            else:
                # 不是第一个chunk，开始点是上一个chunk结束点之前 chunk_overlap~chunk_overlap+overlap_error这个范围内
                # 上一个chunk的结束点是start_idx
                # 我们需要从 start_idx - chunk_overlap - overlap_error 到 start_idx - chunk_overlap 之间找句子边界
                overlap_start = max(0, start_idx - self.chunk_overlap - self.overlap_error)
                overlap_end = start_idx - self.chunk_overlap
                
                # 在这个范围内查找句子边界（从后往前找）
                chunk_start = overlap_end  # 默认在chunk_overlap处
                for i in range(overlap_end, overlap_start - 1, -1):
                    if i < text_len:
                        # 检查单个字符的句子结束符
                        if text[i] in sentence_endings:
                            chunk_start = i + 1
                            break
                        # 检查双换行符
                        if i + 1 < text_len and text[i:i+2] == '\n\n':
                            chunk_start = i + 2
                            break
            
            # 确定结束点
            if chunk_start + self.chunk_size >= text_len:
                # 最后一个chunk，结束点就是结尾
                chunk_end = text_len
            else:
                # 不是最后一个chunk，结束点是开始点之后chunk_size~chunk_size+size_error这个范围内
                size_start = chunk_start + self.chunk_size - self.size_error
                size_end = min(chunk_start + self.chunk_size, text_len)
                
                # 在这个范围内查找句子边界（从前往后找）
                chunk_end = size_start  # 默认在chunk_size处
                for i in range(size_start, size_end + 1):
                    if i < text_len:
                        # 检查单个字符的句子结束符
                        if text[i] in sentence_endings:
                            chunk_end = i + 1
                            break
                        # 检查双换行符
                        if i + 1 < text_len and text[i:i+2] == '\n\n':
                            chunk_end = i + 2
                            break
            
            # 提取chunk
            chunk = text[chunk_start:chunk_end]
            if chunk:  # 确保chunk不为空
                chunks.append(chunk)
            
            # 更新下一个chunk的开始点（当前chunk的结束点）
            start_idx = chunk_end
            
            # 防止无限循环：如果chunk_end没有前进，强制前进至少1个字符
            if start_idx == chunk_start:
                start_idx += 1

        return chunks

    def split_by_markdown_headers(self, text: str) -> List[str]:
        """按照markdown标题切分文本
        
        按照 # ## ### 等标题将markdown文本切分为多个部分
        每个部分包含标题及其内容，直到下一个同级或更高级标题
        """
        if not text:
            return []
        
        sections = []
        lines = text.split('\n')
        current_section = []
        
        for line in lines:
            # 检查是否是标题行（以 # 开头，且 # 后面有空格或直接是内容）
            stripped = line.lstrip()
            if stripped.startswith('#'):
                # 计算标题级别（# 的数量）
                header_level = 0
                for char in stripped:
                    if char == '#':
                        header_level += 1
                    else:
                        break
                
                # 如果当前section有内容，保存它
                if current_section:
                    section_text = '\n'.join(current_section)
                    if section_text.strip():  # 确保section不为空
                        sections.append(section_text)
                    current_section = []
            
            current_section.append(line)
        
        # 添加最后一个section
        if current_section:
            section_text = '\n'.join(current_section)
            if section_text.strip():  # 确保section不为空
                sections.append(section_text)
        
        # 如果没有找到任何标题，返回整个文本
        return sections if sections else [text]

    def split_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """切分多个文档。
        对于PDF和PPT，已经按页/幻灯片分割，不再进行二次切分
        对于DOCX和TXT，进行文本切分
        """
        chunks_with_metadata = []

        for doc in tqdm(documents, desc="处理文档", unit="文档"):
            content = doc.get("content", "")
            filetype = doc.get("filetype", "")

            if filetype in [".pdf", ".pptx"]:
                chunk_data = {
                    "content": content,
                    "filename": doc.get("filename", "unknown"),
                    "filepath": doc.get("filepath", ""),
                    "filetype": filetype,
                    "page_number": doc.get("page_number", 0),
                    "chunk_id": 0,
                    "images": doc.get("images", []),
                }
                chunks_with_metadata.append(chunk_data)

            elif filetype in [".docx", ".txt"]:
                chunks = self.split_text(content)
                for i, chunk in enumerate(chunks):
                    chunk_data = {
                        "content": chunk,
                        "filename": doc.get("filename", "unknown"),
                        "filepath": doc.get("filepath", ""),
                        "filetype": filetype,
                        "page_number": 0,
                        "chunk_id": i,
                        "images": [],
                    }
                    chunks_with_metadata.append(chunk_data)

            elif filetype in [".md"]:
                # 先按照markdown标题切分
                sections = self.split_by_markdown_headers(content)
                chunk_id = 0
                for section in sections:
                    # 对每个section再调用split_text进行切分
                    section_chunks = self.split_text(section)
                    for chunk in section_chunks:
                        chunk_data = {
                            "content": chunk,
                            "filename": doc.get("filename", "unknown"),
                            "filepath": doc.get("filepath", ""),
                            "filetype": filetype,
                            "page_number": 0,
                            "chunk_id": chunk_id,
                            "images": [],
                        }
                        chunks_with_metadata.append(chunk_data)
                        chunk_id += 1

        print(f"\n文档处理完成，共 {len(chunks_with_metadata)} 个块")
        return chunks_with_metadata
