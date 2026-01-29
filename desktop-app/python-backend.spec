# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for building the Python backend.
Run with: pyinstaller python-backend.spec
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

# Collect all necessary data files
datas = [
    # Streamlit app files
    (os.path.join(project_root, 'app.py'), '.'),
    (os.path.join(project_root, 'config.py'), '.'),
    (os.path.join(project_root, 'database.py'), '.'),
    (os.path.join(project_root, 'document_loader.py'), '.'),
    # (os.path.join(project_root, 'exercise_generator.py'), '.'), # REMOVED: File does not exist
    (os.path.join(project_root, 'kb_manager.py'), '.'),
    (os.path.join(project_root, 'question_db.py'), '.'),
    (os.path.join(project_root, 'rag_agent.py'), '.'),
    (os.path.join(project_root, 'settings_utils.py'), '.'),
    (os.path.join(project_root, 'text_splitter.py'), '.'),
    (os.path.join(project_root, 'ui_components.py'), '.'), # ADDED CRITICAL MISSING FILE
    (os.path.join(project_root, 'vector_store.py'), '.'),
    (os.path.join(project_root, 'pages'), 'pages'),
    # Font files
    (os.path.join(project_root, 'simhei.ttf'), '.'),
    (os.path.join(project_root, 'simhei.pkl'), '.'),
    (os.path.join(project_root, 'simhei.cw127.pkl'), '.'),
]

# Add logo if exists
logo_path = os.path.join(project_root, 'logo.png')
if os.path.exists(logo_path):
    datas.append((logo_path, '.'))

# Collect Streamlit data files and metadata
from PyInstaller.utils.hooks import copy_metadata

# Ensure metadata is included for packages that check their version
datas += copy_metadata('streamlit')
datas += copy_metadata('altair')
datas += copy_metadata('tiktoken')

datas += collect_data_files('streamlit')
datas += collect_data_files('altair')
datas += collect_data_files('vega_datasets', include_py_files=True)
datas += collect_data_files('rfc3987_syntax') # Fix rfc3987_syntax error
datas += collect_data_files('jsonschema')

# Collect all chromadb resources (binaries, rust bindings, etc.)
binaries = []
tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports = tmp_ret[2] # Initialize hiddenimports with chromadb's collected imports

# Explicit hidden imports for all required packages
hiddenimports += [
    # Streamlit and web
    'streamlit',
    'streamlit.web',
    'streamlit.web.cli',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.caching',
    'streamlit.components.v1',
    # OpenAI
    'openai',
    'httpx',
    'httpcore',
    'anyio',
    'sniffio',
    # ChromaDB
    'chromadb',
    'chromadb.config',
    'sqlite3',
    'hnswlib',
    # Document processing
    'pypdf2',
    'PyPDF2',
    'python_pptx',
    'pptx',
    'docx2txt',
    'PIL',
    'PIL.Image',
    # NLP
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'jieba',
    'jieba',
    'rank_bm25',
    'fitz',
    'pymupdf',
    'task_manager',
    # Data processing
    'numpy',
    'pandas',
    'tqdm',
    # Utilities
    'dotenv',
    'python_dotenv',
    # Additional dependencies
    'altair',
    'pyarrow',
    'validators',
    'toml',
    'watchdog',
    'packaging',
    'importlib_metadata',
    'typing_extensions',
    'pydeck',
    'protobuf',
    'click',
    'rich',
    'tornado',
    'cachetools',
]

# Collect submodules (minimized to reduce size)
hiddenimports += collect_submodules('streamlit')
# Only collect essential chromadb modules, not test/server modules
hiddenimports += [
    'chromadb',
    'chromadb.api',
    'chromadb.api.segment',
    'chromadb.config',
    'chromadb.db',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.segment',
    'chromadb.segment.impl',
    'chromadb.utils',
]
hiddenimports += collect_submodules('tiktoken')

a = Analysis(
    ['python-backend.py'],
    pathex=[project_root],
    binaries=binaries, # Pass collected binaries here
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Machine Learning frameworks (not needed)
        'matplotlib',
        'scipy',
        'sklearn',
        'tensorflow',
        'torch',
        'cv2',
        'keras',
        # Transformers and HuggingFace (not needed, uses API instead)
        'transformers',
        'datasets',
        'tokenizers',
        'huggingface_hub',
        'safetensors',
        # ONNX (not needed)
        'onnx',
        'onnxruntime',
        # Other large libraries
        'IPython',
        'notebook',
        'jupyter',
        'pytest',
        'sphinx',
        'docutils',
        # Tkinter (not needed for headless server)
        'tkinter',
        '_tkinter',
        'Tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='python-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='python-backend',
)
