import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-omni-flash")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-v4")

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

# 多模态模型配置
VL_MODEL_NAME = os.getenv("VL_MODEL_NAME", "gpt-4o")

# 课件图像理解配置
ENABLE_IMAGE_CAPTIONING = os.getenv("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
IMAGE_CAPTION_MODEL = os.getenv("IMAGE_CAPTION_MODEL", "gpt-4o") # 也可以是 qwen-vl-max 等
