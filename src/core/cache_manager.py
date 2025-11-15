# -*- coding: utf-8 -*-
"""
缓存管理器
"""

import os
import time
import hashlib
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
from .config import Config

class CacheManager(QObject):
    """缓存管理器"""
    
    cache_cleared = pyqtSignal()  # 缓存清理信号
    
    def __init__(self, cache_dir: str, max_size_mb: int = 1000, max_memory_cache_mb: int = 200):
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        # 缩略图专用目录（隐藏）
        try:
            cfg = Config()
            self.thumbnails_dir = Path(cfg.thumbnails_dir)
        except Exception:
            # 兜底：使用应用目录下的缩略图目录
            try:
                from .config import Config
                self.thumbnails_dir = Path(Config().app_dir) / "thumbnail"
            except Exception:
                self.thumbnails_dir = Path(__file__).resolve().parents[2] / "thumbnail"
        
        # 内存缓存
        self.memory_cache: Dict[str, QPixmap] = {}
        self.memory_cache_size = 0
        self.max_memory_cache_mb = max_memory_cache_mb  # 允许配置内存缓存上限
        self.max_memory_cache_bytes = self.max_memory_cache_mb * 1024 * 1024
        
        # 访问时间记录
        self.access_times: Dict[str, float] = {}
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        
        # 线程锁
        self.lock = threading.RLock()
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        # 定时清理
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_old_files)
        self.cleanup_timer.start(3600000)  # 每小时清理一次
    
    def get_cache_key(self, url: str) -> str:
        """生成缓存键"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def get_from_memory(self, cache_key: str) -> Optional[QPixmap]:
        """从内存缓存获取"""
        with self.lock:
            if cache_key in self.memory_cache:
                self.access_times[cache_key] = time.time()
                self.hits += 1
                return self.memory_cache[cache_key]
            else:
                self.misses += 1
        return None
    
    def put_to_memory(self, cache_key: str, pixmap: QPixmap):
        """存储到内存缓存"""
        with self.lock:
            # 估算pixmap大小（粗略估算）
            pixmap_size = pixmap.width() * pixmap.height() * 4  # RGBA
            
            # 检查是否超出内存限制
            if self.memory_cache_size + pixmap_size > self.max_memory_cache_bytes:
                self._cleanup_memory_cache()
            
            # 如果还是太大，不缓存
            if pixmap_size > self.max_memory_cache_bytes // 2:
                return
            
            self.memory_cache[cache_key] = pixmap
            self.memory_cache_size += pixmap_size
            self.access_times[cache_key] = time.time()
    
    def _cleanup_memory_cache(self):
        """清理内存缓存"""
        # 按访问时间排序，删除最旧的
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        
        target_size = self.max_memory_cache_bytes // 2  # 清理到一半大小
        
        for cache_key, _ in sorted_items:
            if self.memory_cache_size <= target_size:
                break
            
            if cache_key in self.memory_cache:
                pixmap = self.memory_cache.pop(cache_key)
                pixmap_size = pixmap.width() * pixmap.height() * 4
                self.memory_cache_size -= pixmap_size
                
            if cache_key in self.access_times:
                del self.access_times[cache_key]

    def set_max_memory_cache_mb(self, size_mb: int):
        """动态设置内存缓存上限（MB）并按需清理。"""
        try:
            size_mb = max(50, int(size_mb))  # 设定一个合理的下限，避免过小导致频繁抖动
        except Exception:
            return
        self.max_memory_cache_mb = size_mb
        self.max_memory_cache_bytes = self.max_memory_cache_mb * 1024 * 1024
        # 如果当前已超过上限，执行一次清理
        if self.memory_cache_size > self.max_memory_cache_bytes:
            self._cleanup_memory_cache()

    def set_max_disk_cache_mb(self, size_mb: int):
        """动态设置磁盘缓存上限（MB）。"""
        try:
            size_mb = max(200, int(size_mb))  # 设定一个合理下限
        except Exception:
            return
        self.max_size_mb = size_mb
        self.max_size_bytes = self.max_size_mb * 1024 * 1024
    
    def get_from_disk(self, cache_key: str) -> Optional[bytes]:
        """从磁盘缓存获取"""
        cache_path = self.get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    data = f.read()
                
                # 更新访问时间
                os.utime(cache_path, None)
                return data
            except Exception:
                # 如果读取失败，删除损坏的缓存文件
                try:
                    cache_path.unlink()
                except:
                    pass
        return None
    
    def put_to_disk(self, cache_key: str, data: bytes):
        """存储到磁盘缓存"""
        try:
            cache_path = self.get_cache_path(cache_key)
            
            # 检查磁盘空间
            if self.get_cache_size() + len(data) > self.max_size_bytes:
                self.cleanup_old_files()
            
            with open(cache_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"缓存写入失败: {e}")
    
    def get_cache_size(self) -> int:
        """获取缓存总大小"""
        total_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                total_size += cache_file.stat().st_size
        except Exception:
            pass
        return total_size
    
    def cleanup_old_files(self):
        """清理旧文件"""
        try:
            cache_files = []
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    stat = cache_file.stat()
                    cache_files.append((cache_file, stat.st_mtime, stat.st_size))
                except Exception:
                    continue
            
            # 按修改时间排序
            cache_files.sort(key=lambda x: x[1])
            
            total_size = sum(f[2] for f in cache_files)
            target_size = self.max_size_bytes * 0.8  # 清理到80%
            
            # 删除最旧的文件直到达到目标大小
            for cache_file, _, file_size in cache_files:
                if total_size <= target_size:
                    break
                
                try:
                    cache_file.unlink()
                    total_size -= file_size
                except Exception:
                    continue
            
            self.cache_cleared.emit()
        except Exception as e:
            print(f"缓存清理失败: {e}")
    
    def clear_all_cache(self):
        """清空所有缓存"""
        # 清空内存缓存
        with self.lock:
            self.memory_cache.clear()
            self.memory_cache_size = 0
            self.access_times.clear()
        
        # 清空磁盘缓存
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            print(f"清空缓存失败: {e}")
        
        self.cache_cleared.emit()

    # -------------------------
    # 缩略图（按ID）专用磁盘存储
    # -------------------------
    def get_thumbnail_path(self, image_id: str) -> Path:
        """获取缩略图文件路径（按ID命名）"""
        safe_id = str(image_id) if image_id is not None else "unknown"
        return self.thumbnails_dir / f"{safe_id}.jpg"

    def save_thumbnail(self, image_id: str, pixmap: QPixmap, quality: int = 85) -> bool:
        """保存缩略图到磁盘目录（隐藏目录）"""
        try:
            path = self.get_thumbnail_path(image_id)
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            return pixmap.save(str(path), 'JPEG', quality)
        except Exception:
            return False

    def load_thumbnail(self, image_id: str) -> Optional[QPixmap]:
        """从磁盘缩略图目录加载缩略图"""
        try:
            path = self.get_thumbnail_path(image_id)
            if path.exists():
                pm = QPixmap(str(path))
                if not pm.isNull():
                    return pm
        except Exception:
            pass
        return None

    def clear_thumbnails(self):
        """清空缩略图目录"""
        try:
            for f in self.thumbnails_dir.glob("*.jpg"):
                try:
                    f.unlink()
                except Exception:
                    continue
        except Exception:
            pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        disk_size = self.get_cache_size()
        disk_count = len(list(self.cache_dir.glob("*.cache")))
        
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "memory_count": len(self.memory_cache),
            "memory_size": self.memory_cache_size / (1024 * 1024),
            "disk_count": disk_count,
            "disk_size": disk_size,
            "total_size_mb": (self.memory_cache_size + disk_size) / (1024 * 1024),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息（别名）"""
        return self.get_cache_stats()