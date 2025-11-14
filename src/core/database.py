# -*- coding: utf-8 -*-
"""
数据库管理器
用于管理本地收藏夹和其他数据
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            config_dir = Path.home() / ".falconpy"
            config_dir.mkdir(exist_ok=True)
            db_path = config_dir / "falconpy.db"
        
        self.db_path = str(db_path)
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建收藏夹表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建文件夹表（用于收藏夹分类）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE
                )
            ''')
            
            # 创建收藏图片表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorite_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    favorite_id INTEGER,
                    image_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    image_data TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (favorite_id) REFERENCES favorites (id) ON DELETE CASCADE,
                    UNIQUE(favorite_id, image_id, site)
                )
            ''')
            
            # 创建搜索历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def create_favorite(self, name: str, description: str = "") -> int:
        """创建收藏夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO favorites (name, description) VALUES (?, ?)",
                (name, description)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_favorites(self) -> List[Dict[str, Any]]:
        """获取所有收藏夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM favorites ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            favorites = []
            for row in rows:
                favorites.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })
            return favorites
    
    def delete_favorite(self, favorite_id: int):
        """删除收藏夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
            conn.commit()
    
    def add_image_to_favorite(self, favorite_id: int, image_id: str, site: str, image_data: Dict[str, Any]):
        """添加图片到收藏夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO favorite_images (favorite_id, image_id, site, image_data) VALUES (?, ?, ?, ?)",
                    (favorite_id, image_id, site, json.dumps(image_data))
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # 图片已存在于收藏夹中
                return False
    
    def remove_image_from_favorite(self, favorite_id: int, image_id: str, site: str):
        """从收藏夹移除图片"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM favorite_images WHERE favorite_id = ? AND image_id = ? AND site = ?",
                (favorite_id, image_id, site)
            )
            conn.commit()
    
    def get_favorite_images(self, favorite_id: int) -> List[Dict[str, Any]]:
        """获取收藏夹中的图片"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM favorite_images WHERE favorite_id = ? ORDER BY added_at DESC",
                (favorite_id,)
            )
            rows = cursor.fetchall()
            
            images = []
            for row in rows:
                images.append({
                    'id': row[0],
                    'favorite_id': row[1],
                    'image_id': row[2],
                    'site': row[3],
                    'image_data': json.loads(row[4]) if row[4] else {},
                    'added_at': row[5]
                })
            return images
    
    def is_image_favorited(self, image_id: str, site: str) -> bool:
        """检查图片是否已收藏"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM favorite_images WHERE image_id = ? AND site = ?",
                (image_id, site)
            )
            count = cursor.fetchone()[0]
            return count > 0
    
    def add_search_history(self, site: str, tags: str):
        """添加搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO search_history (site, tags) VALUES (?, ?)",
                (site, tags)
            )
            conn.commit()
    
    def get_search_history(self, site: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if site:
                cursor.execute(
                    "SELECT * FROM search_history WHERE site = ? ORDER BY searched_at DESC LIMIT ?",
                    (site, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM search_history ORDER BY searched_at DESC LIMIT ?",
                    (limit,)
                )
            
            rows = cursor.fetchall()
            history = []
            for row in rows:
                history.append({
                    'id': row[0],
                    'site': row[1],
                    'tags': row[2],
                    'searched_at': row[3]
                })
            return history
    
    def clear_search_history(self, site: str = None):
        """清空搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if site:
                cursor.execute("DELETE FROM search_history WHERE site = ?", (site,))
            else:
                cursor.execute("DELETE FROM search_history")
            conn.commit()
    
    def create_folder(self, name: str, parent_id: int = None) -> int:
        """创建文件夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO folders (name, parent_id) VALUES (?, ?)",
                (name, parent_id)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_folders(self, parent_id: int = None) -> List[Dict[str, Any]]:
        """获取文件夹列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if parent_id is None:
                cursor.execute("SELECT * FROM folders WHERE parent_id IS NULL ORDER BY created_at ASC")
            else:
                cursor.execute("SELECT * FROM folders WHERE parent_id = ? ORDER BY created_at ASC", (parent_id,))
            
            rows = cursor.fetchall()
            folders = []
            for row in rows:
                folders.append({
                    'id': row[0],
                    'name': row[1],
                    'parent_id': row[2],
                    'created_at': row[3]
                })
            return folders
    
    def delete_folder(self, folder_id: int):
        """删除文件夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            conn.commit()
    
    def rename_folder(self, folder_id: int, new_name: str):
        """重命名文件夹"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE folders SET name = ? WHERE id = ?", (new_name, folder_id))
            conn.commit()