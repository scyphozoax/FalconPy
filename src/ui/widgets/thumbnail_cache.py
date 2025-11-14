# -*- coding: utf-8 -*-
"""
缩略图缓存管理器
提供更高级的缓存策略和预加载功能
"""

from typing import Dict, List, Optional, Tuple, Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
from .image_loader import ImageLoader
from ...core.cache_manager import CacheManager


class ThumbnailCache(QObject):
    """缩略图缓存管理器"""
    
    # 信号
    thumbnail_loaded = pyqtSignal(str, QPixmap)  # url, pixmap
    thumbnail_failed = pyqtSignal(str, str)      # url, error
    cache_stats_updated = pyqtSignal(dict)       # 缓存统计信息
    
    def __init__(self, cache_manager: CacheManager, max_concurrent: int = 5):
        super().__init__()
        self.cache_manager = cache_manager
        self.image_loader = ImageLoader(cache_manager, max_concurrent)
        self.base_max_concurrent = int(max_concurrent)
        self._last_adjust_ms = 0
        self._paused = False
        self._ema_hit_rate = 0.0
        self._ema_avg_ms = 0.0
        self._ema_alpha = 0.2
        
        # 预加载相关
        self.preload_queue: List[Tuple[str, Tuple[int, int]]] = []
        self.preload_timer = QTimer()
        self.preload_timer.setSingleShot(True)
        self.preload_timer.timeout.connect(self._process_preload_queue)
        self.preload_delay = 500  # 500ms延迟开始预加载
        
        # 变体预生成
        self.variant_queue: List[Tuple[str, Tuple[int, int]]] = []
        self.variant_timer = QTimer()
        self.variant_timer.setSingleShot(True)
        self.variant_timer.timeout.connect(self._process_variant_queue)
        self.variant_delay = 200

        # 优先级队列
        self.priority_urls: Set[str] = set()  # 高优先级URL集合
        
        # 统计信息
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'preload_hits': 0,
            'total_requests': 0
        }
        
        # 连接信号
        self.image_loader.image_loaded.connect(self._on_image_loaded)
        self.image_loader.load_failed.connect(self._on_image_failed)
    
    def load_thumbnail(self, url: str, size: Tuple[int, int], priority: bool = False) -> bool:
        """
        加载缩略图
        
        Args:
            url: 图片URL
            size: 缩略图尺寸
            priority: 是否高优先级加载
        
        Returns:
            bool: 是否立即从缓存返回
        """
        self.stats['total_requests'] += 1
        
        # 检查内存缓存
        variant_key = self.cache_manager.get_cache_key(f"{url}|{size[0]}x{size[1]}")
        cached_pixmap = self.cache_manager.get_from_memory(variant_key)
        
        if cached_pixmap:
            self.stats['cache_hits'] += 1
            self.thumbnail_loaded.emit(url, cached_pixmap)
            self._update_stats()
            return True
        
        # 检查原始尺寸缓存
        base_key = self.cache_manager.get_cache_key(url)
        base_pixmap = self.cache_manager.get_from_memory(base_key)
        
        if base_pixmap:
            # 缩放并缓存
            scaled_pixmap = self._scale_pixmap(base_pixmap, size)
            self.cache_manager.put_to_memory(variant_key, scaled_pixmap)
            self.stats['cache_hits'] += 1
            self.thumbnail_loaded.emit(url, scaled_pixmap)
            self._update_stats()
            return True
        
        # 缓存未命中，需要加载
        self.stats['cache_misses'] += 1
        
        if priority:
            self.priority_urls.add(url)
        
        # 使用ImageLoader加载
        success = self.image_loader.load_image(url, size)
        self._update_stats()
        return False
    
    def preload_thumbnails(self, urls: List[str], size: Tuple[int, int]):
        """
        预加载缩略图列表
        
        Args:
            urls: 图片URL列表
            size: 缩略图尺寸
        """
        uncached_urls = []
        for url in urls:
            variant_key = self.cache_manager.get_cache_key(f"{url}|{size[0]}x{size[1]}")
            if not self.cache_manager.get_from_memory(variant_key):
                base_key = self.cache_manager.get_cache_key(url)
                base_pm = self.cache_manager.get_from_memory(base_key)
                if not base_pm:
                    uncached_urls.append(url)
                else:
                    if (url, size) not in self.variant_queue:
                        self.variant_queue.append((url, size))
        
        # 添加到预加载队列
        for url in uncached_urls:
            if (url, size) not in self.preload_queue:
                self.preload_queue.append((url, size))
        
        # 启动预加载定时器
        if self.preload_queue and not self.preload_timer.isActive():
            self.preload_timer.start(self.preload_delay)
        if self.variant_queue and not self.variant_timer.isActive():
            self.variant_timer.start(self.variant_delay)
    
    def _process_preload_queue(self):
        """处理预加载队列"""
        if self._paused or not self.preload_queue:
            return
        
        # 获取当前加载统计
        load_stats = self.image_loader.get_load_stats()
        available_slots = load_stats['max_concurrent'] - load_stats['active_loads']
        
        if load_stats['pending_loads'] > max(2, load_stats['active_loads'] * 2):
            self.preload_timer.start(self.preload_delay)
            return
        reserve_ratio = 0.5 if self._ema_hit_rate < 0.4 or self._ema_avg_ms > 600 else 0.3
        reserved_slots = max(1, int(available_slots * reserve_ratio))
        preload_slots = available_slots - reserved_slots
        
        # 处理预加载请求
        processed = 0
        while self.preload_queue and processed < preload_slots:
            url, size = self.preload_queue.pop(0)
            
            # 再次检查是否已缓存（可能在等待期间被加载了）
            variant_key = self.cache_manager.get_cache_key(f"{url}|{size[0]}x{size[1]}")
            if self.cache_manager.get_from_memory(variant_key):
                continue
            
            # 开始预加载
            if self.image_loader.load_image(url, size):
                processed += 1
        
        if load_stats['pending_loads'] > 10 or self._ema_avg_ms > 700:
            self.preload_delay = min(1400, self.preload_delay + 200)
        else:
            self.preload_delay = max(250, self.preload_delay - 100)
        if self.preload_queue:
            self.preload_timer.start(self.preload_delay)

    def _process_variant_queue(self):
        if not self.variant_queue:
            return
        processed = 0
        max_batch = 4
        while self.variant_queue and processed < max_batch:
            url, size = self.variant_queue.pop(0)
            variant_key = self.cache_manager.get_cache_key(f"{url}|{size[0]}x{size[1]}")
            if self.cache_manager.get_from_memory(variant_key):
                continue
            base_key = self.cache_manager.get_cache_key(url)
            base_pm = self.cache_manager.get_from_memory(base_key)
            if base_pm:
                scaled = self._scale_pixmap(base_pm, size)
                self.cache_manager.put_to_memory(variant_key, scaled)
                self.thumbnail_loaded.emit(url, scaled)
                processed += 1
        self._update_stats()
        if self.variant_queue:
            self.variant_timer.start(self.variant_delay)
    
    def _scale_pixmap(self, pixmap: QPixmap, size: Tuple[int, int]) -> QPixmap:
        """缩放图片"""
        from PyQt6.QtCore import Qt
        return pixmap.scaled(
            size[0], size[1],
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    
    def _on_image_loaded(self, url: str, pixmap: QPixmap):
        """图片加载完成处理"""
        # 检查是否是预加载命中
        if url not in self.priority_urls:
            self.stats['preload_hits'] += 1
        else:
            self.priority_urls.discard(url)
        
        self.thumbnail_loaded.emit(url, pixmap)
        self._update_stats()
    
    def _on_image_failed(self, url: str, error: str):
        """图片加载失败处理"""
        self.priority_urls.discard(url)
        self.thumbnail_failed.emit(url, error)
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        load_stats = self.image_loader.get_load_stats()
        combined_stats = {
            **self.stats,
            **load_stats,
            'preload_queue_size': len(self.preload_queue),
            'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['total_requests'])
        }
        self.cache_stats_updated.emit(combined_stats)
        try:
            import time
            now_ms = int(time.perf_counter() * 1000)
            try:
                hr = float(combined_stats['cache_hit_rate'])
                avgms = float(load_stats.get('avg_load_ms', 0.0) or 0.0)
                self._ema_hit_rate = (self._ema_alpha * hr) + ((1 - self._ema_alpha) * self._ema_hit_rate)
                self._ema_avg_ms = (self._ema_alpha * avgms) + ((1 - self._ema_alpha) * self._ema_avg_ms)
            except Exception:
                pass
            if (now_ms - self._last_adjust_ms) >= 500:
                hit = float(combined_stats['cache_hit_rate'])
                active = int(load_stats['active_loads'])
                pending = int(load_stats['pending_loads'])
                current = int(load_stats['max_concurrent'])
                target = self.base_max_concurrent
                if pending > 20 and active >= current:
                    target = max(2, current - 1)
                elif hit > 0.7 and current < self.base_max_concurrent:
                    target = min(self.base_max_concurrent, current + 1)
                if target != current:
                    self.image_loader.set_max_concurrent(target)
                self._last_adjust_ms = now_ms
        except Exception:
            pass
    
    def clear_preload_queue(self):
        """清空预加载队列"""
        self.preload_queue.clear()
        self.preload_timer.stop()
        self.variant_queue.clear()
        self.variant_timer.stop()
    
    def cancel_all_loads(self):
        """取消所有加载"""
        self.image_loader.cancel_all()
        self.clear_preload_queue()
        self.priority_urls.clear()

    def set_paused(self, paused: bool):
        self._paused = bool(paused)
        if not self._paused and self.preload_queue and not self.preload_timer.isActive():
            self.preload_timer.start(self.preload_delay)
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        load_stats = self.image_loader.get_load_stats()
        return {
            **self.stats,
            **load_stats,
            'preload_queue_size': len(self.preload_queue),
            'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['total_requests'])
        }
    
    def cleanup(self):
        """清理资源"""
        self.cancel_all_loads()
        self.image_loader.stop()
