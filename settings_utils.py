import os
import sys
import platform
from pathlib import Path

def get_user_data_dir():
    """Get the user data directory for the application."""
    app_name = "Vulpis"
    
    if platform.system() == "Windows":
        base_path = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    elif platform.system() == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support")
    else:
        base_path = os.path.expanduser("~/.local/share")
        
    data_dir = os.path.join(base_path, app_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def load_settings_from_env():
    """Load settings from .env file in the user data directory."""
    data_dir = get_user_data_dir()
    env_path = os.path.join(data_dir, '.env')
    
    settings = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    settings[key.strip()] = value.strip()
    else:
        # Create empty .env if not exists
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("# Vulpis Configuration\n")
        except Exception as e:
            print(f"Warning: Could not create .env file at {env_path}: {e}")
            
    return settings

def save_settings_to_env(settings):
    """Save settings to .env file in the user data directory."""
    data_dir = get_user_data_dir()
    env_path = os.path.join(data_dir, '.env')
    
    # Read existing file to preserve comments
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
    # Update lines
    new_lines = []
    updated_keys = set()
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            try:
                parts = stripped.split('=', 1)
                key = parts[0].strip()
                if key in settings:
                    new_lines.append(f"{key}={settings[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            except IndexError:
                 new_lines.append(line)
        else:
            new_lines.append(line)
            
    # Append new keys
    for key, value in settings.items():
        if key not in updated_keys:
             new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
