# -*- coding: utf-8 -*-
"""
GIF播放器组件
基于PIL/Pillow的高性能GIF播放器
"""

import io
from typing import List, Optional, Callable
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image, ImageSequence


class GifPlayer(QObject):
    """
    高性能GIF播放器
    使用PIL/Pillow进行帧提取和缓存
    """
    
    # 信号
    frame_changed = pyqtSignal(QPixmap)  # 帧变化信号
    playback_finished = pyqtSignal()     # 播放完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 播放控制
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)
        
        # GIF数据
        self.gif_image: Optional[Image.Image] = None
        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        
        # 播放状态
        self.current_frame = 0
        self.total_frames = 0
        self.loop_count = 0
        self.current_loop = 0
        self.is_playing = False
        
        # 配置
        self.default_duration = 100  # 默认帧持续时间(ms)
        
    def load_gif(self, data: bytes) -> bool:
        """
        加载GIF数据
        
        Args:
            data: GIF文件的字节数据
            
        Returns:
            bool: 加载是否成功
        """
        try:
            # 停止当前播放
            self.stop()
            
            # 清空之前的数据
            self._clear_data()
            
            # 使用PIL打开GIF
            gif_io = io.BytesIO(data)
            self.gif_image = Image.open(gif_io)
            
            # 检查是否为动画GIF
            if not getattr(self.gif_image, 'is_animated', False):
                # 静态图片，只有一帧
                frame_pixmap = self._pil_to_qpixmap(self.gif_image)
                self.frames = [frame_pixmap]
                self.frame_durations = [0]
                self.total_frames = 1
                self.loop_count = 1
                return True
            
            # 提取所有帧
            self._extract_frames()
            
            # 获取循环次数
            self.loop_count = getattr(self.gif_image, 'loop', 0)
            
            print(f"[GIF] 加载成功: {self.total_frames}帧, 循环次数: {self.loop_count}")
            return True
            
        except Exception as e:
            print(f"[GIF] 加载失败: {e}")
            self._clear_data()
            return False
    
    def _extract_frames(self):
        """提取GIF的所有帧"""
        self.frames = []
        self.frame_durations = []
        
        for frame in ImageSequence.Iterator(self.gif_image):
            # 转换为RGBA模式以确保透明度支持
            if frame.mode != 'RGBA':
                frame = frame.convert('RGBA')
            
            # 转换为QPixmap
            pixmap = self._pil_to_qpixmap(frame)
            self.frames.append(pixmap)
            
            # 获取帧持续时间
            duration = frame.info.get('duration', self.default_duration)
            if duration <= 0:
                duration = self.default_duration
            self.frame_durations.append(duration)
        
        self.total_frames = len(self.frames)
        print(f"[GIF] 提取了 {self.total_frames} 帧")
    
    def _pil_to_qpixmap(self, pil_image: Image.Image) -> QPixmap:
        """
        将PIL图像转换为QPixmap
        
        Args:
            pil_image: PIL图像对象
            
        Returns:
            QPixmap: Qt像素图
        """
        # 确保图像为RGBA模式
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        # 获取图像数据
        width, height = pil_image.size
        img_data = pil_image.tobytes('raw', 'RGBA')
        
        # 创建QImage
        qimage = QImage(img_data, width, height, QImage.Format.Format_RGBA8888)
        
        # 转换为QPixmap
        return QPixmap.fromImage(qimage)
    
    def play(self):
        """开始播放"""
        if not self.frames or self.is_playing:
            return
        
        self.is_playing = True
        self.current_frame = 0
        self.current_loop = 0
        
        # 发送第一帧
        if self.frames:
            self.frame_changed.emit(self.frames[0])
        
        # 如果只有一帧，不需要定时器
        if self.total_frames <= 1:
            return
        
        # 启动定时器
        duration = self.frame_durations[0]
        self.timer.start(duration)
        
        print(f"[GIF] 开始播放，首帧延迟: {duration}ms")
    
    def stop(self):
        """停止播放"""
        if self.timer.isActive():
            self.timer.stop()
        self.is_playing = False
        self.current_frame = 0
        self.current_loop = 0
    
    def pause(self):
        """暂停播放"""
        if self.timer.isActive():
            self.timer.stop()
        self.is_playing = False
    
    def resume(self):
        """恢复播放"""
        if not self.is_playing and self.frames and self.total_frames > 1:
            self.is_playing = True
            duration = self.frame_durations[self.current_frame]
            self.timer.start(duration)
    
    def _next_frame(self):
        """切换到下一帧"""
        if not self.frames or not self.is_playing:
            return
        
        # 移动到下一帧
        self.current_frame += 1
        
        # 检查是否到达结尾
        if self.current_frame >= self.total_frames:
            self.current_loop += 1
            
            # 检查循环次数
            if self.loop_count > 0 and self.current_loop >= self.loop_count:
                # 播放完成
                self.stop()
                self.playback_finished.emit()
                print("[GIF] 播放完成")
                return
            
            # 重新开始循环
            self.current_frame = 0
            print(f"[GIF] 开始第 {self.current_loop + 1} 次循环")
        
        # 发送当前帧
        current_pixmap = self.frames[self.current_frame]
        self.frame_changed.emit(current_pixmap)
        
        # 设置下一帧的定时器
        duration = self.frame_durations[self.current_frame]
        self.timer.start(duration)
    
    def get_current_frame(self) -> Optional[QPixmap]:
        """获取当前帧"""
        if self.frames and 0 <= self.current_frame < len(self.frames):
            return self.frames[self.current_frame]
        return None
    
    def get_frame_count(self) -> int:
        """获取总帧数"""
        return self.total_frames
    
    def is_animated(self) -> bool:
        """检查是否为动画GIF"""
        return self.total_frames > 1
    
    def _clear_data(self):
        """清空数据"""
        if self.gif_image:
            self.gif_image.close()
            self.gif_image = None
        
        self.frames.clear()
        self.frame_durations.clear()
        self.current_frame = 0
        self.total_frames = 0
        self.loop_count = 0
        self.current_loop = 0
        self.is_playing = False
    
    def __del__(self):
        """析构函数"""
        self.stop()
        self._clear_data()