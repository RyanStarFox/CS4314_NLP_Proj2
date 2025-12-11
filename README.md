# CS4314 智能课程助教系统

基于 RAG（检索增强生成）技术的智能课程助教系统，支持多模态输入、知识库检索和智能问答。

## 📋 项目简介

本项目是一个完整的 RAG 系统实现，旨在为课程学习提供智能化的学习助手。系统提供五大核心功能模块：
- 🧠 **智能助教**：24小时在线答疑，支持文本和图片多模态提问，结合知识库上下文生成准确回答
- 📝 **做题练习**：自定义题型（概念辨析/应用计算）、题目数量和选项数，AI 自动生成题目并即时批改解析
- 📓 **错题整理**：自动收录练习中的错题，支持反复练习、掌握标记和手动添加题目
- 📑 **大纲生成**：基于知识库内容自动生成复习大纲，支持 Markdown 和 PDF 格式导出（PDF 完美支持 LaTeX 公式）
- 🗂️ **知识库管理**：多知识库管理，支持上传文档、自动向量化、文档增删等操作

## ✨ 功能特性

### 核心功能模块

#### 🧠 智能助教
- 💬 **智能问答**：结合知识库和对话历史，生成准确、有依据的回答
- 🖼️ **多模态输入**：支持文本问题和图片题目上传，视觉模型自动理解图片内容
- 📚 **多知识库切换**：可选择不同的知识库进行问答
- 🔗 **上下文追问**：支持多轮对话，保持上下文连贯性

#### 📝 做题练习
- 🎯 **自定义配置**：选择知识库、题型（概念辨析/应用计算）、题目数量、选项数量
- 🤖 **AI 自动出题**：基于知识库内容生成多样化题目，支持并行生成提升效率
- ✅ **即时批改**：提交答案后立即判断对错并给出详细解析
- 📊 **成绩统计**：完成练习后显示正确率

#### 📓 错题整理
- 📝 **自动收录**：练习中的错题自动保存到错题本
- 🔄 **反复练习**：支持错题复习模式，可标记已掌握题目
- ➕ **手动添加**：支持上传题目图片或手动输入，AI 自动识别题目内容和选项
- 📋 **智能摘要**：AI 自动生成题目摘要，方便快速浏览

#### 📑 大纲生成
- 📚 **智能提炼**：基于知识库内容自动生成结构化的复习大纲
- 📥 **多格式导出**：支持 Markdown 和 PDF 格式下载
- ✨ **完美渲染**：PDF 导出使用 Pandoc + LaTeX，完美支持中文、数学公式、代码高亮等

#### 🗂️ 知识库管理
- 📁 **多知识库支持**：支持创建和管理多个独立的知识库
- 📤 **文档上传**：支持 PDF、PPTX、DOCX、TXT、Markdown 等多种格式
- 🔄 **自动向量化**：上传文档后自动进行文本提取和向量化处理
- 🖼️ **图像理解**：自动识别课件中的图片并生成文字描述（可选功能）

### 技术亮点
- 🔍 **混合检索策略**：结合稀疏检索（BM25）和密集向量检索，提升文档召回准确率
- 🗄️ **ChromaDB 向量数据库**：高效的向量存储和相似度搜索
- 🤖 **OpenAI 兼容 API**：支持通义千问、GPT-4 等多种模型
- 🔗 **LangChain 集成**：基于 LangChain 的文本处理流程
- 🎨 **现代化 Web 界面**：Streamlit 多页面应用，美观易用
- 📦 **智能文本分块**：可配置的分块大小和重叠策略
- 🌐 **中文优化**：使用 jieba 分词，针对中文场景优化
- ⚡ **并行处理**：题目生成支持并行调用，提升效率

## 🛠️ 技术栈

- **Python 3.8+**
- **向量数据库**：ChromaDB
- **LLM API**：OpenAI 兼容 API（支持通义千问等）
- **Web 框架**：Streamlit
- **文档处理**：
  - PyPDF2 / PyMuPDF：PDF 处理
  - python-pptx：PPT 处理
  - docx2txt：Word 处理
- **文本处理**：
  - LangChain：文本处理流程
  - sentence-transformers：文本嵌入
  - jieba：中文分词（用于混合检索）
  - rank_bm25：BM25 稀疏检索算法
- **PDF 生成**：Pandoc + LaTeX（xelatex 引擎，支持中文和数学公式）
- **其他**：tiktoken、pandas、tqdm、fpdf（PDF 回退方案）

## 📁 项目结构

```
.
├── app.py                 # Streamlit Web 应用主页面（导航页）
├── main.py                # 命令行交互入口
├── config.py              # 配置文件（环境变量读取）
├── rag_agent.py           # RAG Agent 核心逻辑
├── document_loader.py     # 文档加载器（支持多种格式，含图像理解）
├── text_splitter.py       # 文本分块器
├── vector_store.py        # 向量数据库封装（支持混合检索）
├── kb_manager.py          # 知识库管理器（多知识库管理）
├── question_db.py         # 错题本数据库（JSON 存储）
├── process_data.py        # 数据处理脚本（构建知识库）
├── requirements.txt       # Python 依赖包
├── .gitignore            # Git 忽略文件
├── .env                  # 环境变量配置（需自行创建）
├── .env.example          # 环境变量配置示例
├── pages/                # Streamlit 多页面应用
│   ├── 1_🧠_智能助教.py
│   ├── 2_📝_做题练习.py
│   ├── 3_📓_错题整理.py
│   ├── 4_📑_大纲生成.py
│   └── 5_🗂️_知识库管理.py
├── data/                 # 课程文档目录（需自行创建）
│   └── [知识库名称]/      # 每个知识库一个子目录
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

**推荐使用虚拟环境：**
```bash
# 使用 conda
conda create -n nlp python=3.10
conda activate nlp
pip install -r requirements.txt

# 或使用 venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 配置环境变量

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
EXERCISE_TOP_K=30  # 题目生成时的上下文池大小
MEMORY_WINDOW_SIZE=10  # 对话历史窗口大小

# 混合检索配置（Hybrid Search）
ENABLE_HYBRID_SEARCH=True  # 启用混合检索（BM25 + 向量检索）
HYBRID_SEARCH_ALPHA=0.5  # 混合检索权重（0.5 表示向量和关键词检索权重相等）

# 多模态模型配置
VL_MODEL_NAME=gpt-4o  # 视觉语言模型（用于图片问答）

# 课件图像理解配置（可选）
ENABLE_IMAGE_CAPTIONING=False  # 是否启用课件图片自动描述
IMAGE_CAPTION_MODEL=gpt-4o  # 图像描述模型
```

### 5. 准备课程文档

有两种方式准备知识库：

**方式一：通过 Web 界面管理（推荐）**
1. 启动应用后，进入"知识库管理"页面
2. 创建新知识库（支持中文名称）
3. 上传文档，系统会自动进行向量化处理

**方式二：手动构建（旧方式）**
将课程相关的 PDF、PPTX、DOCX 等文档放入 `data/` 目录下的子目录（每个知识库一个子目录），然后运行：
```bash
python process_data.py
```

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

#### 🧠 智能助教
1. **选择知识库**：在页面顶部选择要使用的知识库
2. **提问**：在输入框中输入问题，系统会自动检索相关知识并生成回答
3. **上传图片**：点击上传按钮，支持图片题目问答（多模态模型自动识别）
4. **多轮对话**：支持上下文追问，系统会记住对话历史
5. **查看参考资料**：回答下方可展开查看检索到的相关文档片段

#### 📝 做题练习
1. **配置练习**：选择知识库、题型（概念辨析/应用计算）、题目数量、选项数量
2. **开始练习**：系统会并行生成多道题目，依次展示
3. **作答**：选择答案后点击提交，立即显示对错和解析
4. **查看成绩**：完成所有题目后显示正确率和错题统计
5. **错题自动收录**：错题会自动保存到错题本

#### 📓 错题整理
1. **查看错题**：浏览所有错题，支持展开/折叠查看
2. **复习模式**：点击"开始复习模式"，重新练习错题
3. **标记掌握**：已掌握的题目可以标记为"已掌握"
4. **编辑答案**：可以手动编辑正确答案和解析
5. **手动添加**：支持上传题目图片或手动输入，AI 自动识别并生成答案

#### 📑 大纲生成
1. **选择知识库**：选择要生成大纲的知识库
2. **生成大纲**：点击"生成复习大纲"，系统会分析知识库内容并生成结构化大纲
3. **下载大纲**：支持下载 Markdown 或 PDF 格式
   - **Markdown**：纯文本格式，可在任何编辑器中使用
   - **PDF**：完美渲染，支持中文、LaTeX 公式、代码高亮等（需要 Pandoc + LaTeX）

#### 🗂️ 知识库管理
1. **创建知识库**：输入知识库名称（支持中文），创建新的知识库
2. **上传文档**：选择知识库后，上传 PDF、PPTX、DOCX 等格式文档
3. **自动向量化**：首次上传文档时，系统会自动进行向量化处理（可能需要较长时间）
4. **管理文档**：可以查看、删除知识库中的文档
5. **删除知识库**：可以删除整个知识库（包括向量数据）

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
| `EXERCISE_TOP_K` | 题目生成时的上下文池大小 | 30 |
| `MEMORY_WINDOW_SIZE` | 对话历史窗口大小 | 10 |
| `MAX_TOKENS` | 生成回答的最大 token 数 | 4096 |
| `ENABLE_HYBRID_SEARCH` | 是否启用混合检索 | True |
| `HYBRID_SEARCH_ALPHA` | 混合检索权重（0-1，0.5 表示向量和关键词权重相等） | 0.5 |
| `ENABLE_IMAGE_CAPTIONING` | 是否启用课件图片自动描述 | False |

### 模型配置

- **文本模型**：通过 `MODEL_NAME` 配置，用于生成回答、题目、大纲等
- **视觉模型**：通过 `VL_MODEL_NAME` 配置，用于图片问答和图像理解
- **嵌入模型**：通过 `OPENAI_EMBEDDING_MODEL` 配置，用于生成向量嵌入
- **图像描述模型**：通过 `IMAGE_CAPTION_MODEL` 配置，用于课件图片自动描述（可选）

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
- **混合检索**：结合 BM25（稀疏检索）和向量检索（密集检索）
- 元数据管理（文件名、页码等）
- 多知识库支持（通过 collection_name 隔离）

### `kb_manager.py`
知识库管理器，提供：
- 多知识库创建、删除、列表
- 文档上传和向量化
- 自动检测知识库是否需要向量化
- 支持中文知识库名称（自动处理 ChromaDB 命名限制）

### `question_db.py`
错题本数据库，提供：
- 错题存储和管理（JSON 格式）
- 错题查询和筛选
- 掌握状态标记
- AI 自动生成题目摘要

## ⚠️ 注意事项

1. **API 密钥**：确保 `.env` 文件中的 API 密钥配置正确，且不要将 `.env` 文件提交到版本控制
2. **数据目录**：首次使用前需要创建 `data/` 目录并放入课程文档
3. **向量数据库**：运行 `process_data.py` 会清空现有向量数据库，请谨慎操作
4. **模型兼容性**：确保使用的 API 服务支持所需的模型（文本生成、嵌入、视觉理解）
5. **资源消耗**：处理大量文档时，向量化过程可能需要较长时间和较多 API 调用
6. **PDF 生成功能**：大纲生成页面的 PDF 导出功能需要安装 `pandoc` 和 LaTeX（如 MacTeX/BasicTeX）。如果未安装，PDF 导出功能将无法使用，但 Markdown 下载功能不受影响
7. **知识库向量化**：首次使用某个知识库时，系统会自动进行向量化处理，这可能需要较长时间（取决于文档数量和大小）
8. **混合检索**：默认启用混合检索（BM25 + 向量检索），可以提升检索准确率。如果遇到性能问题，可以在 `.env` 中设置 `ENABLE_HYBRID_SEARCH=False` 禁用
9. **中文知识库名称**：系统支持中文知识库名称，会自动处理 ChromaDB 的命名限制

## ❓ 常见问题（FAQ）

### Q: PDF 导出失败怎么办？
**A:** 确保已安装 Pandoc 和 LaTeX。如果使用 BasicTeX，可能需要额外安装中文字体包：
```bash
sudo tlmgr install collection-langcjk
```

### Q: 知识库向量化很慢怎么办？
**A:** 向量化速度取决于文档数量和大小。可以：
- 分批上传文档，避免一次性上传过多
- 检查 API 调用是否正常（网络问题可能导致超时）
- 如果文档很大，考虑先拆分文档

### Q: 检索结果不准确怎么办？
**A:** 可以尝试：
- 启用混合检索（`ENABLE_HYBRID_SEARCH=True`）
- 调整 `TOP_K` 参数（增加检索数量）
- 检查知识库内容是否完整向量化
- 尝试不同的查询表述方式

### Q: 如何切换不同的知识库？
**A:** 在"智能助教"、"做题练习"、"大纲生成"等页面的顶部都有知识库选择下拉框，可以直接切换。

### Q: 错题本数据存储在哪里？
**A:** 错题本数据存储在 `data/user_progress.json` 文件中，是 JSON 格式，可以手动备份或编辑。

### Q: 支持哪些文档格式？
**A:** 目前支持 PDF、PPTX、DOCX、TXT、Markdown 格式。对于 PDF 和 PPTX，系统会自动提取图片并生成描述（如果启用了 `ENABLE_IMAGE_CAPTIONING`）。

### Q: 如何备份知识库？
**A:** 知识库数据包括：
- 文档文件：`data/[知识库名称]/` 目录
- 向量数据：`vector_db/` 目录（ChromaDB 存储）
- 错题本：`data/user_progress.json`

可以备份整个 `data/` 和 `vector_db/` 目录。

## 🔄 更新知识库

### 通过 Web 界面更新（推荐）

1. 进入"知识库管理"页面
2. 选择要更新的知识库
3. 上传新文档，系统会自动进行向量化处理
4. 或删除不需要的文档

### 手动更新（旧方式）

如果需要手动更新知识库：

1. 将新文档放入对应知识库目录（`data/[知识库名称]/`）
2. 在"知识库管理"页面点击"重建索引"，或运行：
   ```bash
   python -c "from kb_manager import KBManager; KBManager().rebuild_kb_index('知识库名称')"
   ```

**注意**：重建索引会清空该知识库的向量数据并重新构建。

## 🎯 功能演示

### 主界面
系统采用多页面设计，主页提供五大功能模块的快速导航。

### 智能助教
- 支持文本和图片多模态提问
- 自动检索相关知识库内容
- 生成有依据的准确回答
- 支持多轮对话和上下文追问

### 做题练习
- 自定义题型（概念辨析 vs 应用计算）
- 可配置题目数量和选项数
- AI 并行生成多样化题目
- 即时批改和详细解析

### 错题整理
- 自动收录练习中的错题
- AI 生成题目摘要，方便快速浏览
- 支持展开/折叠查看
- 可标记已掌握题目
- 支持手动添加题目（图片或文本）

### 大纲生成
- 基于知识库内容智能生成复习大纲
- 支持 Markdown 和 PDF 格式导出
- PDF 完美支持中文、LaTeX 公式、代码高亮

### 知识库管理
- 多知识库独立管理
- 支持中文知识库名称
- 文档上传和自动向量化
- 可视化文档管理界面

## 📄 许可证

本项目为课程作业项目，仅供学习使用。

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

## 🔗 相关链接

- [GitHub 仓库](https://github.com/RyanStarFox/CS4314_NLP_Proj2)
- [问题反馈](https://github.com/RyanStarFox/CS4314_NLP_Proj2/issues)

---

**开发团队**：CS4314 自然语言处理课程项目组  
**项目时间**：2024-2025年

