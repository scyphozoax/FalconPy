# -*- coding: utf-8 -*-
"""
图片加载和缓存管理器
"""

import os
import asyncio
import hashlib
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMutex, QTimer
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import aiohttp
from PIL import Image
import io

class ImageCache:
    """图片缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_size: int = 100):
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.memory_cache: Dict[str, QPixmap] = {}
        self.cache_order = []
        self.mutex = QMutex()
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, url: str) -> str:
        """生成缓存键"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.jpg")
    
    def get_from_memory(self, url: str) -> Optional[QPixmap]:
        """从内存缓存获取图片"""
        self.mutex.lock()
        try:
            cache_key = self._get_cache_key(url)
            if cache_key in self.memory_cache:
                # 更新访问顺序
                if cache_key in self.cache_order:
                    self.cache_order.remove(cache_key)
                self.cache_order.append(cache_key)
                return self.memory_cache[cache_key]
            return None
        finally:
            self.mutex.unlock()
    
    def get_from_disk(self, url: str) -> Optional[QPixmap]:
        """从磁盘缓存获取图片"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        if os.path.exists(cache_path):
            try:
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    self.put_to_memory(url, pixmap)
                    return pixmap
            except Exception as e:
                print(f"从磁盘加载图片失败: {e}")
        
        return None
    
    def put_to_memory(self, url: str, pixmap: QPixmap):
        """将图片放入内存缓存"""
        self.mutex.lock()
        try:
            cache_key = self._get_cache_key(url)
            
            # 如果缓存已满，删除最旧的项
            if len(self.memory_cache) >= self.max_size and cache_key not in self.memory_cache:
                if self.cache_order:
                    oldest_key = self.cache_order.pop(0)
                    if oldest_key in self.memory_cache:
                        del self.memory_cache[oldest_key]
            
            self.memory_cache[cache_key] = pixmap
            if cache_key in self.cache_order:
                self.cache_order.remove(cache_key)
            self.cache_order.append(cache_key)
        finally:
            self.mutex.unlock()
    
    def put_to_disk(self, url: str, data: bytes):
        """将图片数据保存到磁盘缓存"""
        try:
            cache_key = self._get_cache_key(url)
            cache_path = self._get_cache_path(cache_key)
            
            # 使用PIL处理图片并保存为JPEG
            image = Image.open(io.BytesIO(data))
            if image.mode in ('RGBA', 'LA', 'P'):
                # 转换为RGB模式
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            
            image.save(cache_path, 'JPEG', quality=85, optimize=True)
            
        except Exception as e:
            print(f"保存图片到磁盘失败: {e}")
    
    def clear_memory_cache(self):
        """清空内存缓存"""
        self.mutex.lock()
        try:
            self.memory_cache.clear()
            self.cache_order.clear()
        finally:
            self.mutex.unlock()
    
    def clear_disk_cache(self):
        """清空磁盘缓存"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.jpg'):
                    os.remove(os.path.join(self.cache_dir, filename))
        except Exception as e:
            print(f"清空磁盘缓存失败: {e}")


class ImageLoader(QObject):
    """异步图片加载器"""
    
    image_loaded = pyqtSignal(str, QPixmap)  # url, pixmap
    image_failed = pyqtSignal(str, str)      # url, error_message
    
    def __init__(self, cache: ImageCache):
        super().__init__()
        self.cache = cache
        self.session = None
        self.loading_tasks = set()
    
    async def _create_session(self):
        """创建HTTP会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': 'FalconPy/1.0 (Image Viewer)'
                }
            )
    
    async def load_image_async(self, url: str, thumbnail_size: tuple = None):
        """异步加载图片"""
        if url in self.loading_tasks:
            return
        
        self.loading_tasks.add(url)
        
        try:
            # 首先检查内存缓存
            pixmap = self.cache.get_from_memory(url)
            if pixmap:
                self.image_loaded.emit(url, pixmap)
                return
            
            # 检查磁盘缓存
            pixmap = self.cache.get_from_disk(url)
            if pixmap:
                self.image_loaded.emit(url, pixmap)
                return
            
            # 从网络下载
            await self._create_session()
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    
                    # 保存到磁盘缓存
                    self.cache.put_to_disk(url, data)
                    
                    # 创建QPixmap
                    image = QImage()
                    if image.loadFromData(data):
                        pixmap = QPixmap.fromImage(image)
                        
                        # 如果需要缩略图，进行缩放
                        if thumbnail_size:
                            pixmap = pixmap.scaled(
                                thumbnail_size[0], thumbnail_size[1],
                                aspectRatioMode=1,  # KeepAspectRatio
                                transformMode=1     # SmoothTransformation
                            )
                        
                        # 保存到内存缓存
                        self.cache.put_to_memory(url, pixmap)
                        
                        self.image_loaded.emit(url, pixmap)
                    else:
                        self.image_failed.emit(url, "无法解析图片数据")
                else:
                    self.image_failed.emit(url, f"HTTP错误: {response.status}")
                    
        except Exception as e:
            self.image_failed.emit(url, str(e))
        finally:
            self.loading_tasks.discard(url)
    
    def load_image(self, url: str, thumbnail_size: tuple = None):
        """加载图片（同步接口）"""
        asyncio.create_task(self.load_image_async(url, thumbnail_size))
    
    async def close(self):
        """关闭加载器"""
        if self.session and not self.session.closed:
            await self.session.close()


class ImageLoaderThread(QThread):
    """图片加载线程"""
    
    image_loaded = pyqtSignal(str, QPixmap)
    image_failed = pyqtSignal(str, str)
    
    def __init__(self, cache: ImageCache):
        super().__init__()
        self.cache = cache
        self.loader = None
        self.loop = None
        self.load_queue = asyncio.Queue()
        self.running = False
    
    def run(self):
        """运行事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.loader = ImageLoader(self.cache)
        self.loader.image_loaded.connect(self.image_loaded)
        self.loader.image_failed.connect(self.image_failed)
        
        self.running = True
        
        try:
            self.loop.run_until_complete(self._process_queue())
        except Exception as e:
            print(f"图片加载线程错误: {e}")
        finally:
            if self.loader:
                self.loop.run_until_complete(self.loader.close())
            self.loop.close()
    
    async def _process_queue(self):
        """处理加载队列"""
        while self.running:
            try:
                # 等待加载任务
                url, thumbnail_size = await asyncio.wait_for(
                    self.load_queue.get(), timeout=1.0
                )
                await self.loader.load_image_async(url, thumbnail_size)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"处理加载队列错误: {e}")
    
    def load_image(self, url: str, thumbnail_size: tuple = None):
        """添加图片加载任务"""
        if self.loop and self.running:
            asyncio.run_coroutine_threadsafe(
                self.load_queue.put((url, thumbnail_size)),
                self.loop
            )
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()