"""
Copyright 2025 Dominic Hawgood

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os
import sys
from pathlib import Path

# Get the application's base directory (where run_bridge.py is located)
# This ensures config.json is always in the app directory, not the current working directory
if getattr(sys, 'frozen', False):
    # Running as compiled executable (PyInstaller, etc.)
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as script - find project root (parent of utils/)
    # utils/config.py -> utils/ -> project root
    BASE_DIR = Path(__file__).parent.parent

CONFIG_FILE = BASE_DIR / "config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "comfyui": {
        "url": "http://127.0.0.1:8188"
    },
    "ui": {
        "window_width": 1400,
        "window_height": 900,
        "remember_position": True
    },
    "paths": {
        "comfyui_input_folder": ""
    }
}

_config_cache = None

def get_config():
    """Load configuration from file, creating it with defaults if it doesn't exist."""
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    # CONFIG_FILE is now a Path object, not a string
    config_path = CONFIG_FILE
    
    # Create config file with defaults if it doesn't exist
    if not config_path.exists():
        _config_cache = DEFAULT_CONFIG.copy()
        save_config(_config_cache)
        return _config_cache
    
    # Load existing config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
        
        # Merge with defaults to ensure all keys exist
        _config_cache = _merge_config(DEFAULT_CONFIG, loaded_config)
        return _config_cache
    except Exception as e:
        # If loading fails, use defaults
        _config_cache = DEFAULT_CONFIG.copy()
        return _config_cache

def _merge_config(default, loaded):
    """Recursively merge loaded config with defaults."""
    result = default.copy()
    for key, value in loaded.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result

def save_config(config=None):
    """Save configuration to file."""
    global _config_cache
    
    if config is None:
        config = _config_cache
    
    if config is None:
        return
    
    try:
        # CONFIG_FILE is now a Path object
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        _config_cache = config
    except Exception as e:
        # Silently fail - config saving is not critical
        pass

def get_comfyui_url():
    """Get the ComfyUI API URL from config."""
    config = get_config()
    return config.get("comfyui", {}).get("url", "http://127.0.0.1:8188")

def set_comfyui_url(url):
    """Set the ComfyUI API URL in config."""
    config = get_config()
    if "comfyui" not in config:
        config["comfyui"] = {}
    config["comfyui"]["url"] = url
    save_config(config)
    global _config_cache
    _config_cache = config

def reload_config():
    """Reload configuration from file (clears cache)."""
    global _config_cache
    _config_cache = None
    return get_config()

def get_comfyui_input_folder():
    """Get the ComfyUI input folder path from config."""
    config = get_config()
    return config.get("paths", {}).get("comfyui_input_folder", "")

def set_comfyui_input_folder(path):
    """Set the ComfyUI input folder path in config."""
    config = get_config()
    if "paths" not in config:
        config["paths"] = {}
    config["paths"]["comfyui_input_folder"] = path
    save_config(config)
    global _config_cache
    _config_cache = config

