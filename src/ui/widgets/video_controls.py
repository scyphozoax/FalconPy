# -*- coding: utf-8 -*-
"""
视频播放控制组件
提供完整的视频播放控制功能
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                             QSlider, QLabel, QFrame, QSizePolicy, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtMultimedia import QMediaPlayer
from ...core.i18n import I18n
from ...core.config import Config


class VideoControls(QWidget):
    """视频播放控制组件"""
    
    # 信号
    play_pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    position_changed = pyqtSignal(int)  # 用户拖拽进度条
    volume_changed = pyqtSignal(float)  # 音量变化 (0.0-1.0)
    mute_toggled = pyqtSignal(bool)     # 静音切换
    fullscreen_clicked = pyqtSignal()   # 全屏按钮
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化 i18n（优先使用父窗口的 i18n）
        if parent is not None and hasattr(parent, 'i18n'):
            self.i18n = parent.i18n
        else:
            try:
                cfg = Config()
                lang = cfg.get('appearance.language', 'zh_CN')
            except Exception:
                lang = 'zh_CN'
            self.i18n = I18n(lang)

        # 播放状态
        self.is_playing = False
        self.is_muted = False
        self.duration = 0
        self.position = 0
        self.volume = 1.0
        
        # 更新定时器
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.setInterval(100)  # 100ms更新一次
        
        # 进度条拖拽状态
        self.seeking = False
        
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        from PyQt6.QtWidgets import QSizePolicy
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 5px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 3px;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 50);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 70);
            }
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 50);
                height: 6px;
                background: rgba(255, 255, 255, 30);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid rgba(0, 0, 0, 100);
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -3px 0;
            }
            QSlider::sub-page:horizontal {
                background: #0078d4;
                border-radius: 3px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)
        
        # 进度条和时间显示
        progress_layout = QHBoxLayout()
        
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setMinimumWidth(40)
        progress_layout.addWidget(self.current_time_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setMaximumHeight(20)
        progress_layout.addWidget(self.progress_slider)
        
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setMinimumWidth(40)
        progress_layout.addWidget(self.total_time_label)
        
        main_layout.addLayout(progress_layout)
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        
        # 播放控制
        self.play_pause_btn = QPushButton("")
        self.play_pause_btn.setMinimumSize(28, 24)
        self.play_pause_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.play_pause_btn.setToolTip(self.i18n.t("播放/暂停 (空格)"))
        controls_layout.addWidget(self.play_pause_btn)
        
        self.stop_btn = QPushButton("")
        self.stop_btn.setMinimumSize(28, 24)
        self.stop_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.stop_btn.setToolTip(self.i18n.t("停止"))
        controls_layout.addWidget(self.stop_btn)
        
        # 快进/快退
        self.rewind_btn = QPushButton("")
        self.rewind_btn.setMinimumSize(28, 24)
        self.rewind_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.rewind_btn.setToolTip(self.i18n.t("快退10秒 (←)"))
        controls_layout.addWidget(self.rewind_btn)
        
        self.forward_btn = QPushButton("")
        self.forward_btn.setMinimumSize(28, 24)
        self.forward_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.forward_btn.setToolTip(self.i18n.t("快进10秒 (→)"))
        controls_layout.addWidget(self.forward_btn)
        
        controls_layout.addStretch()
        
        # 音量控制
        self.mute_btn = QPushButton("")
        self.mute_btn.setMinimumSize(28, 24)
        self.mute_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.mute_btn.setToolTip(self.i18n.t("静音/取消静音 (M)"))
        controls_layout.addWidget(self.mute_btn)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.setToolTip(self.i18n.t("音量控制"))
        controls_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("100%")
        self.volume_label.setMinimumWidth(40)
        controls_layout.addWidget(self.volume_label)
        
        # 全屏按钮
        self.fullscreen_btn = QPushButton("")
        self.fullscreen_btn.setMinimumSize(28, 24)
        self.fullscreen_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.fullscreen_btn.setToolTip(self.i18n.t("全屏 (F)"))
        controls_layout.addWidget(self.fullscreen_btn)
        
        main_layout.addLayout(controls_layout)
        self._apply_icons()
    
    def setup_connections(self):
        """设置信号连接"""
        # 播放控制
        self.play_pause_btn.clicked.connect(self.play_pause_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.rewind_btn.clicked.connect(lambda: self._seek_relative(-10000))  # -10秒
        self.forward_btn.clicked.connect(lambda: self._seek_relative(10000))   # +10秒
        
        # 进度条
        self.progress_slider.sliderPressed.connect(self._on_seek_start)
        self.progress_slider.sliderReleased.connect(self._on_seek_end)
        self.progress_slider.valueChanged.connect(self._on_progress_changed)
        
        # 音量控制
        self.mute_btn.clicked.connect(self._toggle_mute)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        
        # 全屏
        self.fullscreen_btn.clicked.connect(self.fullscreen_clicked.emit)
    
    def _seek_relative(self, offset_ms):
        """相对跳转"""
        if self.duration > 0:
            new_position = max(0, min(self.duration, self.position + offset_ms))
            self.position_changed.emit(new_position)
    
    def _on_seek_start(self):
        """开始拖拽进度条"""
        self.seeking = True
    
    def _on_seek_end(self):
        """结束拖拽进度条"""
        self.seeking = False
        if self.duration > 0:
            # 计算新位置
            progress = self.progress_slider.value() / 1000.0
            new_position = int(self.duration * progress)
            self.position_changed.emit(new_position)
    
    def _on_progress_changed(self, value):
        """进度条值变化"""
        if self.seeking and self.duration > 0:
            # 实时更新时间显示
            progress = value / 1000.0
            position = int(self.duration * progress)
            self.current_time_label.setText(self._format_time(position))
    
    def _on_volume_changed(self, value):
        """音量滑块变化"""
        volume = value / 100.0
        self.volume = volume
        self.volume_changed.emit(volume)
        self.is_muted = (volume == 0)
        self._set_mute_icon()
        self._update_volume_label()
    
    def _toggle_mute(self):
        """切换静音"""
        self.is_muted = not self.is_muted
        self.mute_toggled.emit(self.is_muted)
        self._set_mute_icon()
        self._update_volume_label()
    
    def _update_display(self):
        """更新显示"""
        if not self.seeking:
            # 更新进度条
            if self.duration > 0:
                progress = (self.position / self.duration) * 1000
                self.progress_slider.setValue(int(progress))
            
            # 更新时间显示
            self.current_time_label.setText(self._format_time(self.position))
    
    def _format_time(self, ms):
        """格式化时间显示"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    # 公共接口
    def set_media_player(self, player: QMediaPlayer):
        """设置媒体播放器"""
        self.media_player = player
        if player:
            # 连接播放器信号
            player.positionChanged.connect(self.update_position)
            player.durationChanged.connect(self.update_duration)
            player.playbackStateChanged.connect(self.update_playback_state)
    
    def update_position(self, position):
        """更新播放位置"""
        self.position = position
        if not self.seeking:
            self._update_display()
    
    def update_duration(self, duration):
        """更新总时长"""
        self.duration = duration
        self.total_time_label.setText(self._format_time(duration))
        
        # 启动更新定时器
        if duration > 0 and not self.update_timer.isActive():
            self.update_timer.start()
    
    @pyqtSlot(QMediaPlayer.PlaybackState)
    def update_playback_state(self, state):
        """更新播放状态"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.is_playing = True
            size = self._compute_icon_size()
            self.play_pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.play_pause_btn.setIconSize(size)
            self.play_pause_btn.setToolTip(self.i18n.t("暂停 (空格)"))
        else:
            self.is_playing = False
            size = self._compute_icon_size()
            self.play_pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.play_pause_btn.setIconSize(size)
            self.play_pause_btn.setToolTip(self.i18n.t("播放 (空格)"))
            
        # 停止状态时停止更新定时器
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.update_timer.stop()
            self.position = 0
            self.progress_slider.setValue(0)
            self.current_time_label.setText("00:00")
    
    def set_volume(self, volume):
        """设置音量 (0.0-1.0)"""
        self.volume = volume
        self.volume_slider.setValue(int(volume * 100))
        self._update_volume_label()
    
    def set_muted(self, muted):
        """设置静音状态"""
        self.is_muted = muted
        self._set_mute_icon()
        self._update_volume_label()
    
    def reset(self):
        """重置控制器状态"""
        self.update_timer.stop()
        self.duration = 0
        self.position = 0
        self.seeking = False
        self.progress_slider.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self._apply_icons()
        self._update_volume_label()

    def _compute_icon_size(self):
        try:
            from ...core.config import Config
            cfg = Config()
            scale = int(cfg.get('appearance.scale', 100) or 100)
            base = int(cfg.get('appearance.scale_base', 70) or 70)
            eff = max(60, min(150, int(round(base * scale / 100.0))))
            icon_px = max(14, min(24, int(round(16 * eff / 100.0))))
        except Exception:
            icon_px = 16
        return QSize(icon_px, icon_px)

    def _apply_icons(self):
        size = self._compute_icon_size()
        self.play_pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_pause_btn.setIconSize(size)
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.setIconSize(size)
        self.rewind_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        self.rewind_btn.setIconSize(size)
        self.forward_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        self.forward_btn.setIconSize(size)
        self.fullscreen_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.fullscreen_btn.setIconSize(size)
        self._set_mute_icon()
        self._update_volume_label()

    def _set_mute_icon(self):
        size = self._compute_icon_size()
        if self.is_muted:
            self.mute_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        else:
            self.mute_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.mute_btn.setIconSize(size)

    def _update_volume_label(self):
        eff = 0.0 if self.is_muted else max(0.0, min(1.0, self.volume))
        self.volume_label.setText(f"{int(eff * 100)}%")

    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        self.play_pause_btn.click()

    def toggle_mute(self):
        """切换静音状态"""
        self.mute_btn.click()
        try:
            from ...core.config import Config
            cfg = Config()
            scale = int(cfg.get('appearance.scale', 100) or 100)
            base = int(cfg.get('appearance.scale_base', 70) or 70)
            eff = max(60, min(150, int(round(base * scale / 100.0))))
            icon_px = max(14, min(24, int(round(16 * eff / 100.0))))
        except Exception:
            icon_px = 16
        icon_size = QSize(icon_px, icon_px)
        self.play_pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_pause_btn.setIconSize(icon_size)
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.setIconSize(icon_size)
        self.rewind_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        self.rewind_btn.setIconSize(icon_size)
        self.forward_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        self.forward_btn.setIconSize(icon_size)
        self.mute_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.mute_btn.setIconSize(icon_size)
        self.fullscreen_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.fullscreen_btn.setIconSize(icon_size)