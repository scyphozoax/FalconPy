# -*- coding: utf-8 -*-
"""
性能监控组件
"""

import psutil
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class PerformanceMonitor(QWidget):
    """性能监控组件"""
    
    def __init__(self, cache_manager=None):
        super().__init__()
        self.cache_manager = cache_manager
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel("性能监控")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 内存使用
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(QLabel("内存:"))
        
        self.memory_bar = QProgressBar()
        self.memory_bar.setMaximum(100)
        self.memory_bar.setTextVisible(True)
        memory_layout.addWidget(self.memory_bar)
        
        layout.addLayout(memory_layout)
        
        # CPU使用
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("CPU:"))
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setMaximum(100)
        self.cpu_bar.setTextVisible(True)
        cpu_layout.addWidget(self.cpu_bar)
        
        layout.addLayout(cpu_layout)
        
        # 缓存信息
        if self.cache_manager:
            cache_layout = QVBoxLayout()
            
            self.cache_size_label = QLabel("缓存大小: 0 MB")
            cache_layout.addWidget(self.cache_size_label)
            
            self.cache_count_label = QLabel("缓存项目: 0")
            cache_layout.addWidget(self.cache_count_label)
            
            self.cache_hit_rate_label = QLabel("命中率: 0%")
            cache_layout.addWidget(self.cache_hit_rate_label)
            
            layout.addLayout(cache_layout)
    
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)  # 每2秒更新一次
    
    def update_stats(self):
        """更新统计信息"""
        try:
            # 更新内存使用
            memory_percent = psutil.virtual_memory().percent
            self.memory_bar.setValue(int(memory_percent))
            self.memory_bar.setFormat(f"{memory_percent:.1f}%")
            
            # 更新CPU使用
            cpu_percent = psutil.cpu_percent()
            self.cpu_bar.setValue(int(cpu_percent))
            self.cpu_bar.setFormat(f"{cpu_percent:.1f}%")
            
            # 更新缓存信息
            if self.cache_manager:
                stats = self.cache_manager.get_stats()
                
                # 缓存大小
                cache_size_mb = stats.get('disk_size', 0) / (1024 * 1024)
                self.cache_size_label.setText(f"缓存大小: {cache_size_mb:.1f} MB")
                
                # 缓存项目数
                cache_count = stats.get('memory_count', 0) + stats.get('disk_count', 0)
                self.cache_count_label.setText(f"缓存项目: {cache_count}")
                
                # 命中率
                hits = stats.get('hits', 0)
                misses = stats.get('misses', 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                self.cache_hit_rate_label.setText(f"命中率: {hit_rate:.1f}%")
                
        except Exception as e:
            print(f"更新性能统计失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        if not self.timer.isActive():
            self.timer.start(2000)
    
    def stop_monitoring(self):
        """停止监控"""
        if self.timer.isActive():
            self.timer.stop()