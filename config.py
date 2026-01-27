import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# API配置 (文本生成模型)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

# Embedding 模型API配置
# 如果未独立设置，默认回退到使用 OPENAI_API_KEY/BASE
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", OPENAI_API_KEY)
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", OPENAI_API_BASE)
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# 多模态模型(VL) API配置
# 如果未独立设置，默认回退到使用 OPENAI_API_KEY/BASE
VL_API_KEY = os.getenv("VL_API_KEY", OPENAI_API_KEY)
VL_API_BASE = os.getenv("VL_API_BASE", OPENAI_API_BASE)
VL_MODEL_NAME = os.getenv("VL_MODEL_NAME", "gpt-4o")

# 课件图像理解配置
ENABLE_IMAGE_CAPTIONING = os.getenv("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
IMAGE_CAPTION_MODEL = os.getenv("IMAGE_CAPTION_MODEL", "gpt-4o") 
# Captioning 也可以有独立的 key，目前复用 VL_API_KEY


# 数据目录配置
# 使用绝对路径，确保指向项目根目录下的 data 文件夹
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
# DATA_DIR = os.getenv("DATA_DIR", "./data")

# 向量数据库配置
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vector_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "")

# 混合检索配置 (Hybrid Search)
ENABLE_HYBRID_SEARCH = os.getenv("ENABLE_HYBRID_SEARCH", "True").lower() == "true"
HYBRID_SEARCH_ALPHA = float(os.getenv("HYBRID_SEARCH_ALPHA", "0.5")) # 0.5 means equal weight to vector and keyword

# 文本处理配置
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
SIZE_ERROR = int(os.getenv("SIZE_ERROR", "100"))
OVERLAP_ERROR = int(os.getenv("OVERLAP_ERROR", "20"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

# RAG配置
TOP_K = int(os.getenv("TOP_K", "6"))
EXERCISE_TOP_K = int(os.getenv("EXERCISE_TOP_K", "30")) # Pool size for quiz generation
MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", "10"))



def get_openai_client(api_key=None, base_url=None):
    """
    Factory function to create an OpenAI client with SSL verification disabled (verify=False).
    Use this instead of creating OpenAI() directly to ensure self-signed certificates are accepted.
    """
    # Fallback to defaults if None is passed
    if api_key is None: api_key = OPENAI_API_KEY
    if base_url is None: base_url = OPENAI_API_BASE
    
    # Prepare arguments
    kwargs = {
        "api_key": api_key,
        "http_client": httpx.Client(verify=False)
    }
    
    # Only pass base_url if it's not empty, otherwise let OpenAI library use its default
    if base_url:
        kwargs["base_url"] = base_url
    
    return OpenAI(**kwargs)
