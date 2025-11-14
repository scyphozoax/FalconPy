# -*- coding: utf-8 -*-
"""
图片加载器
"""

import requests
import time
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt, QTimer
from PyQt6.QtGui import QPixmap
from typing import Optional, Tuple
from ...core.cache_manager import CacheManager

class ImageLoadWorker(QThread):
    """图片加载工作线程"""
    
    image_loaded = pyqtSignal(str, QPixmap)  # url, pixmap
    load_failed = pyqtSignal(str, str)  # url, error_message
    
    def __init__(self, url: str, cache_manager: CacheManager, size: Optional[Tuple[int, int]] = None, parent=None):
        super().__init__(parent)
        self.url = url
        self.cache_manager = cache_manager
        self.size = size
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FalconPy/1.0'
        })
    
    def run(self):
        """运行加载任务"""
        try:
            base_key = self.cache_manager.get_cache_key(self.url)
            # 缩略图尺寸变体的内存键（仅用于内存缓存，不重复写盘）
            variant_key = None
            if self.size:
                variant_key = self.cache_manager.get_cache_key(f"{self.url}|{self.size[0]}x{self.size[1]}")
            
            # 先检查内存缓存
            # 若提供尺寸，优先命中变体缓存；否则命中原始缓存
            pixmap = None
            if variant_key:
                pixmap = self.cache_manager.get_from_memory(variant_key)
            if pixmap is None:
                pixmap = self.cache_manager.get_from_memory(base_key)
            if pixmap:
                # 命中原始缓存但需要尺寸缩略图，做一次缩放并写入变体缓存
                if self.size and variant_key and (pixmap.width() != self.size[0] or pixmap.height() != self.size[1]):
                    scaled = pixmap.scaled(
                        self.size[0], self.size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.cache_manager.put_to_memory(variant_key, scaled)
                    self.image_loaded.emit(self.url, scaled)
                    return
                self.image_loaded.emit(self.url, pixmap)
                return
            
            # 检查磁盘缓存
            cached_data = self.cache_manager.get_from_disk(base_key)
            if cached_data:
                pixmap = QPixmap()
                if pixmap.loadFromData(cached_data):
                    # 若有尺寸需求，缩放并仅将缩放后的版本写入内存（避免双倍占用）
                    if self.size and variant_key:
                        scaled = pixmap.scaled(
                            self.size[0], self.size[1],
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        self.cache_manager.put_to_memory(variant_key, scaled)
                        self.image_loaded.emit(self.url, scaled)
                    else:
                        # 无尺寸需求，缓存原始pixmap到内存
                        self.cache_manager.put_to_memory(base_key, pixmap)
                        self.image_loaded.emit(self.url, pixmap)
                    return
            
            # 从网络下载
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            
            image_data = response.content
            
            # 创建pixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # 存储到缓存
                self.cache_manager.put_to_disk(base_key, image_data)
                if self.size and variant_key:
                    scaled = pixmap.scaled(
                        self.size[0], self.size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.cache_manager.put_to_memory(variant_key, scaled)
                    self.image_loaded.emit(self.url, scaled)
                else:
                    self.cache_manager.put_to_memory(base_key, pixmap)
                    self.image_loaded.emit(self.url, pixmap)
            else:
                self.load_failed.emit(self.url, "无法解析图片数据")
                
        except requests.RequestException as e:
            self.load_failed.emit(self.url, f"网络错误: {str(e)}")
        except Exception as e:
            self.load_failed.emit(self.url, f"加载失败: {str(e)}")

class ImageLoader(QObject):
    """图片加载器管理器"""
    
    image_loaded = pyqtSignal(str, QPixmap)
    load_failed = pyqtSignal(str, str)
    
    def __init__(self, cache_manager: CacheManager, max_concurrent: int = 5):
        super().__init__()
        self.cache_manager = cache_manager
        self.max_concurrent = max_concurrent
        self.active_workers = {}
        self.pending_requests = []  # [(url, size)]
        self._dispatch_timer = QTimer()
        self._dispatch_timer.setSingleShot(True)
        self._dispatch_timer.timeout.connect(self._dispatch_pending)
        self._min_launch_interval_ms = 30
        self._last_launch_ms = 0
        self._start_ts = {}
        self._sum_load_ms = 0.0
        self._count_loaded = 0
        self._cancel_count = 0
    
    def load_image(self, url: str, thumbnail_size: Optional[Tuple[int, int]] = None) -> bool:
        """加载图片（支持缩略图尺寸缓存复用）"""
        # 检查是否已经在加载
        if url in self.active_workers:
            return False
        
        # 先检查内存缓存（优先尺寸变体，其次原始）
        base_key = self.cache_manager.get_cache_key(url)
        variant_key = None
        if thumbnail_size:
            variant_key = self.cache_manager.get_cache_key(f"{url}|{thumbnail_size[0]}x{thumbnail_size[1]}")
        pixmap = None
        if variant_key:
            pixmap = self.cache_manager.get_from_memory(variant_key)
        if pixmap is None:
            pixmap = self.cache_manager.get_from_memory(base_key)
            # 若找到原始但需要缩略图，直接缩放并写入变体缓存，避免启动线程
            if pixmap is not None and variant_key:
                scaled = pixmap.scaled(
                    thumbnail_size[0], thumbnail_size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.cache_manager.put_to_memory(variant_key, scaled)
                self.image_loaded.emit(url, scaled)
                return True
        if pixmap is not None:
            self.image_loaded.emit(url, pixmap)
            return True
        
        if len(self.active_workers) >= self.max_concurrent:
            if (url, thumbnail_size) not in self.pending_requests:
                self.pending_requests.append((url, thumbnail_size))
            if not self._dispatch_timer.isActive():
                self._dispatch_timer.start(self._min_launch_interval_ms)
            return False
        
        # 创建工作线程
        import time
        now_ms = int(time.perf_counter() * 1000)
        if (now_ms - self._last_launch_ms) < self._min_launch_interval_ms:
            if (url, thumbnail_size) not in self.pending_requests:
                self.pending_requests.append((url, thumbnail_size))
            if not self._dispatch_timer.isActive():
                self._dispatch_timer.start(self._min_launch_interval_ms)
            return False
        self._last_launch_ms = now_ms
        worker = ImageLoadWorker(url, self.cache_manager, thumbnail_size)
        worker.image_loaded.connect(self._on_image_loaded)
        worker.load_failed.connect(self._on_load_failed)
        worker.finished.connect(lambda: self._on_worker_finished(url))
        self.active_workers[url] = worker
        self._start_ts[url] = time.perf_counter()
        worker.start()
        return True
    
    def _on_image_loaded(self, url: str, pixmap: QPixmap):
        """图片加载成功"""
        try:
            st = self._start_ts.pop(url, None)
            if st is not None:
                self._sum_load_ms += (time.perf_counter() - st) * 1000.0
                self._count_loaded += 1
        except Exception:
            pass
        self.image_loaded.emit(url, pixmap)
    
    def _on_load_failed(self, url: str, error: str):
        """图片加载失败"""
        try:
            self._start_ts.pop(url, None)
        except Exception:
            pass
        self.load_failed.emit(url, error)
    
    def _on_worker_finished(self, url: str):
        """工作线程完成"""
        if url in self.active_workers:
            worker = self.active_workers.pop(url)
            worker.deleteLater()
        
        if self.pending_requests:
            if not self._dispatch_timer.isActive():
                self._dispatch_timer.start(self._min_launch_interval_ms)

    def _dispatch_pending(self):
        import time
        now_ms = int(time.perf_counter() * 1000)
        if (now_ms - self._last_launch_ms) < self._min_launch_interval_ms:
            self._dispatch_timer.start(self._min_launch_interval_ms)
            return
        while self.pending_requests and len(self.active_workers) < self.max_concurrent:
            next_url, next_size = self.pending_requests.pop(0)
            started = self.load_image(next_url, next_size)
            if started:
                now_ms = int(time.perf_counter() * 1000)
                self._last_launch_ms = now_ms
            else:
                break
    
    def cancel_load(self, url: str):
        """取消加载"""
        if url in self.active_workers:
            worker = self.active_workers.pop(url)
            self._cancel_count += 1
            worker.terminate()
            worker.wait()
            worker.deleteLater()
        
        if url in self.pending_requests:
            self.pending_requests.remove(url)
    
    def cancel_all(self):
        """取消所有加载"""
        # 终止所有活跃的工作线程
        for worker in self.active_workers.values():
            self._cancel_count += 1
            worker.terminate()
            worker.wait()
            worker.deleteLater()
        
        self.active_workers.clear()
        self.pending_requests.clear()
    
    def get_load_stats(self):
        """获取加载统计"""
        avg_ms = (self._sum_load_ms / self._count_loaded) if self._count_loaded > 0 else 0.0
        return {
            "active_loads": len(self.active_workers),
            "pending_loads": len(self.pending_requests),
            "max_concurrent": self.max_concurrent,
            "loaded_count": self._count_loaded,
            "cancel_count": self._cancel_count,
            "avg_load_ms": avg_ms
        }

    def set_max_concurrent(self, n: int):
        try:
            n = int(n)
        except Exception:
            return
        self.max_concurrent = max(1, n)

    def get_max_concurrent(self) -> int:
        return int(self.max_concurrent)

    def stop(self):
        """停止所有加载（兼容关闭事件调用）"""
        try:
            self.cancel_all()
        except Exception:
            pass
