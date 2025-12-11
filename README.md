# CS4314 智能课程助教系统

基于 RAG（检索增强生成）技术的智能课程助教系统，支持多模态输入、知识库检索和智能问答。

## 📋 项目简介

本项目是一个完整的 RAG 系统实现，旨在为课程学习提供智能化的问答助手。系统能够：
- 从多种格式的课程文档中提取知识
- 构建向量知识库进行语义检索
- 基于检索到的上下文生成准确回答
- 支持文本和图片多模态输入
- 提供随堂测验和作业批改功能

## ✨ 功能特性

### 核心功能
- 📚 **多格式文档支持**：支持 PDF、PPTX、DOCX、TXT、Markdown 等格式
- 🔍 **智能检索**：基于向量相似度的语义检索，快速定位相关知识
- 💬 **智能问答**：结合知识库和对话历史，生成准确、有依据的回答
- 🖼️ **多模态输入**：支持文本问题和图片题目上传
- 📝 **随堂测验**：自动生成基于课程知识的单选题
- ✅ **作业批改**：自动判断选择题答案并给出解析

### 技术亮点
- 使用 ChromaDB 作为向量数据库
- 支持 OpenAI 兼容 API（包括通义千问等模型）
- 基于 LangChain 的文本处理流程
- Streamlit 构建的现代化 Web 界面
- 智能文本分块和重叠策略

## 🛠️ 技术栈

- **Python 3.8+**
- **向量数据库**：ChromaDB
- **LLM API**：OpenAI 兼容 API（支持通义千问等）
- **Web 框架**：Streamlit
- **文档处理**：
  - PyPDF2 / PyMuPDF：PDF 处理
  - python-pptx：PPT 处理
  - docx2txt：Word 处理
- **文本处理**：LangChain、sentence-transformers
- **PDF 生成**：Pandoc + LaTeX（xelatex 引擎，支持中文和数学公式）
- **其他**：tiktoken、pandas、tqdm

## 📁 项目结构

```
.
├── app.py                 # Streamlit Web 应用入口
├── main.py                # 命令行交互入口
├── config.py              # 配置文件（环境变量读取）
├── rag_agent.py           # RAG Agent 核心逻辑
├── document_loader.py     # 文档加载器（支持多种格式）
├── text_splitter.py       # 文本分块器
├── vector_store.py        # 向量数据库封装
├── process_data.py        # 数据处理脚本（构建知识库）
├── requirements.txt       # Python 依赖包
├── .gitignore            # Git 忽略文件
├── .env                  # 环境变量配置（需自行创建）
├── data/                 # 课程文档目录（需自行创建）
└── vector_db/            # 向量数据库存储目录（自动创建）
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.8 或更高版本。

### 2. 安装系统依赖

#### Pandoc（用于 PDF 生成）

**macOS：**
```bash
brew install pandoc
```

**Linux (Ubuntu/Debian)：**
```bash
sudo apt-get install pandoc
```

**Windows：**
从 [Pandoc 官网](https://pandoc.org/installing.html) 下载安装程序。

#### LaTeX（用于 PDF 渲染，支持中文和数学公式）

**macOS：**
```bash
# 完整版（推荐，约 4GB）
brew install --cask mactex

# 或轻量版（约 100MB，功能较少）
brew install --cask basictex
# 安装后可能需要安装额外包：
sudo tlmgr update --self
sudo tlmgr install collection-langcjk  # 中文字体支持
```

**Linux (Ubuntu/Debian)：**
```bash
sudo apt-get install texlive-full
# 或轻量版：
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-lang-chinese
```

**Windows：**
从 [MiKTeX 官网](https://miktex.org/download) 或 [TeX Live 官网](https://www.tug.org/texlive/) 下载安装。

**验证安装：**
```bash
pandoc --version
xelatex --version  # macOS/Linux
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件，配置以下变量：

```env
# API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.example.com/v1
MODEL_NAME=qwen3-omni-flash
OPENAI_EMBEDDING_MODEL=text-embedding-v4

# 数据目录配置
DATA_DIR=./data

# 向量数据库配置
VECTOR_DB_PATH=./vector_db
COLLECTION_NAME=course_materials

# 文本处理配置
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
SIZE_ERROR=100
OVERLAP_ERROR=20
MAX_TOKENS=4096

# RAG 配置
TOP_K=6
```

### 4. 准备课程文档

将课程相关的 PDF、PPTX、DOCX 等文档放入 `data/` 目录（如果目录不存在，请先创建）。

### 5. 构建知识库

运行数据处理脚本，将文档加载并构建向量知识库：

```bash
python process_data.py
```

该脚本会：
1. 加载 `data/` 目录下的所有支持格式文档
2. 对文档进行文本分块处理
3. 生成向量嵌入并存储到 ChromaDB

### 6. 启动应用

#### 方式一：Web 界面（推荐）

```bash
streamlit run app.py
```

浏览器会自动打开，访问 `http://localhost:8501` 即可使用。

#### 方式二：命令行交互

```bash
python main.py
```

## 📖 使用说明

### Web 界面使用

1. **提问**：在输入框中输入问题，系统会自动检索相关知识并生成回答
2. **上传图片**：在侧边栏上传题目截图，支持图片问答
3. **随堂测验**：点击"生成随堂测验"按钮，系统会基于知识库生成单选题
4. **查看参考资料**：回答下方可展开查看检索到的相关文档片段

### 命令行使用

运行 `python main.py` 后，直接输入问题即可。系统支持：
- 普通问答：直接输入问题
- 选择题作答：输入 A/B/C/D 选项，系统会基于历史对话判断对错

## 🔧 配置说明

### 主要配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `CHUNK_SIZE` | 文本分块大小 | 1000 |
| `CHUNK_OVERLAP` | 分块重叠大小 | 200 |
| `TOP_K` | 检索返回的文档数量 | 6 |
| `MAX_TOKENS` | 生成回答的最大 token 数 | 4096 |

### 模型配置

- **文本模型**：通过 `MODEL_NAME` 配置，用于生成回答
- **视觉模型**：通过 `VL_MODEL_NAME` 配置（在 `config.py` 中），用于图片问答
- **嵌入模型**：通过 `OPENAI_EMBEDDING_MODEL` 配置，用于生成向量嵌入

## 📝 主要模块说明

### `rag_agent.py`
RAG Agent 核心类，负责：
- 检索相关上下文（`retrieve_context`）
- 生成回答（`generate_response`）
- 处理多模态输入（文本+图片）
- 支持随堂测验和作业批改模式

### `document_loader.py`
文档加载器，支持：
- PDF：按页提取文本
- PPTX：按幻灯片提取文本
- DOCX：提取 Word 文档内容
- TXT/MD：直接读取文本

### `text_splitter.py`
文本分块器，将长文档切分为适合检索的文本块，支持：
- 可配置的分块大小和重叠
- 智能处理边界情况

### `vector_store.py`
向量数据库封装，提供：
- 文档向量化存储
- 语义相似度搜索
- 元数据管理（文件名、页码等）

## ⚠️ 注意事项

1. **API 密钥**：确保 `.env` 文件中的 API 密钥配置正确，且不要将 `.env` 文件提交到版本控制
2. **数据目录**：首次使用前需要创建 `data/` 目录并放入课程文档
3. **向量数据库**：运行 `process_data.py` 会清空现有向量数据库，请谨慎操作
4. **模型兼容性**：确保使用的 API 服务支持所需的模型（文本生成、嵌入、视觉理解）
5. **资源消耗**：处理大量文档时，向量化过程可能需要较长时间和较多 API 调用
6. **PDF 生成功能**：大纲生成页面的 PDF 导出功能需要安装 `pandoc` 和 LaTeX（如 MacTeX/BasicTeX）。如果未安装，PDF 导出功能将无法使用，但 Markdown 下载功能不受影响

## 🔄 更新知识库

如果需要更新知识库（添加新文档或更新现有文档）：

1. 将新文档放入 `data/` 目录
2. 运行 `python process_data.py` 重新构建向量数据库

**注意**：该操作会清空现有向量数据库并重新构建。

## 📄 许可证

本项目为课程作业项目，仅供学习使用。

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**开发团队**：CS4314 自然语言处理课程项目组  
**项目时间**：2024年

