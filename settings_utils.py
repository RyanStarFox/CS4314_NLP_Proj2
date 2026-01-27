import os

def load_settings_from_env(env_path=".env"):
    """直接从 .env 文件读取设置，不依赖 os.environ"""
    settings = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    # Remove inline comments
                    val = val.split("#", 1)[0].strip()
                    settings[key.strip()] = val
    return settings

def save_settings_to_env(settings, env_path=".env"):
    """保存设置到 .env 文件，尽量保留注释"""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    new_lines = []
    processed_keys = set()
    
    # Update existing keys
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
            
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in settings:
                new_lines.append(f"{key}={settings[key]}\n")
                processed_keys.add(key)
            else:
                new_lines.append(line) # keep existing unrelated keys
        else:
            new_lines.append(line)
            
    # Append new keys if any
    # Prepare categories if file is empty or new sections needed?
    # For simplicity, just append.
    
    # Check if we need to add a newline before appending
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines.append("\n")

    for key, val in settings.items():
        if key not in processed_keys:
            new_lines.append(f"{key}={val}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
