# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

class Config:
    """应用程序配置管理"""
    
    def __init__(self):
        self.app_dir = Path.home() / ".falconpy"
        self.config_file = self.app_dir / "config.json"
        self.cache_dir = self.app_dir / "cache"
        # 专用缩略图目录（隐藏目录）
        self.thumbnails_dir = self.app_dir / "thumbnail"
        self.favorites_dir = self.app_dir / "favorites"
        
        # 创建必要的目录
        self._create_directories()
        
        # 默认配置
        self.default_config = {
            "window": {
                "width": 1200,
                "height": 800,
                "maximized": False
            },
            "appearance": {
                "theme": "dark",
                "font": "等距更纱黑体,11",
                "scale": 100,
                "show_thumbnails": True,
                "show_image_info": True,
                "animate_transitions": True,
                "language": "zh_CN"
            },
            "network": {
                "use_proxy": False,
                "proxy_type": "HTTP",
                "proxy_host": "",
                "proxy_port": 8080,
                "proxy_username": "",
                "proxy_password": "",
                "timeout": 30,
                "debug": True,
                "max_retries": 3,
                "concurrent_downloads": 5
            },
            "download": {
                "path": "./downloads",
                "auto_rename": True,
                "create_subfolders": True,
                "download_original": True,
                "save_metadata": False,
                "max_file_size": 50
            },
            "sites": {
                "danbooru": {
                    "enabled": True,
                    "api_url": "https://danbooru.donmai.us",
                    "username": "",
                    "api_key": "",
                    "favorite_default": {
                        "destination": "local",  # local | online
                        "folder_id": None
                    }
                },
                "konachan": {
                    "enabled": True,
                    "api_url": "https://konachan.net",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "favorite_default": {
                        "destination": "local",
                        "folder_id": None
                    }
                },
                "yandere": {
                    "enabled": True,
                    "api_url": "https://yande.re",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "favorite_default": {
                        "destination": "local",
                        "folder_id": None
                    }
                }
            },
            "cache": {
                "max_size": 1000,  # MB 磁盘缓存最大体积
                "max_memory": 200,  # MB 内存缓存最大体积
                "cleanup_interval": 7  # days
            },
            "updates": {
                "enabled": True,
                "interval_minutes": 60,
                "feed_url": "https://example.com/falconpy/latest.json",
                "channel": "stable"
            }
        }
        
        # 加载配置
        self.config = self._load_config()
    
    def _create_directories(self):
        """创建必要的目录"""
        self.app_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        # 创建缩略图目录并在 Windows 上设置隐藏属性
        try:
            self.thumbnails_dir.mkdir(exist_ok=True)
            # 仅在 Windows 设置隐藏属性
            import os
            import platform
            if platform.system().lower() == 'windows':
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(str(self.thumbnails_dir), FILE_ATTRIBUTE_HIDDEN)
                except Exception:
                    # 备用方案：使用 attrib 命令
                    try:
                        os.system(f'attrib +h "{self.thumbnails_dir}"')
                    except Exception:
                        pass
        except Exception:
            # 目录创建失败不影响运行，后续保存时再尝试
            pass
        self.favorites_dir.mkdir(exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置和用户配置
                return self._merge_config(self.default_config, config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        
        return self.default_config.copy()
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """合并配置"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.config = self.default_config.copy()
        self.save_config()
