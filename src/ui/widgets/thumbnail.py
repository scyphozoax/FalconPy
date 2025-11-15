# -*- coding: utf-8 -*-
"""
重构后的缩略图组件
采用更清晰的架构设计，分离关注点
"""

from enum import Enum
from typing import Optional, Dict, Any, Tuple
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QSizePolicy, QGraphicsDropShadowEffect, QGraphicsBlurEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QFont, QCursor, QMouseEvent, QColor


class ThumbnailState(Enum):
    """缩略图状态枚举"""
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    PLACEHOLDER = "placeholder"


class ThumbnailStyle:
    """缩略图样式管理类"""
    
    # 基础样式
    BASE_FRAME_STYLE = """
        QFrame {{
            border: 2px solid {border_color};
            border-radius: 12px;
            background-color: {bg_color};
            padding: 8px;
        }}
        QFrame:hover {{
            border-color: {hover_border_color};
            background-color: {hover_bg_color};
        }}
    """
    
    # 图片标签样式
    IMAGE_LABEL_STYLE = """
        QLabel {{
            border: none;
            background-color: transparent;
            color: {text_color};
            font-size: 12px;
            font-weight: 500;
            padding: 0px;
        }}
    """

    # ID信息毛玻璃风格（拟态）：半透明白背景与细边框
    ID_OVERLAY_STYLE = """
        QLabel {{
            background-color: rgba(255, 255, 255, 28);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 40);
            border-radius: 10px;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: 600;
        }}
    """
    
    # 按钮样式
    VIEW_BUTTON_STYLE = """
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
    """
    
    # 收藏按钮样式
    FAVORITE_BUTTON_NORMAL = """
        QPushButton {{
            background-color: rgba(68, 68, 68, 180);
            color: white;
            border: none;
            border-radius: 18px;
            font-size: 18px;
            font-weight: bold;
            width: 36px;
            height: 36px;
        }}
        QPushButton:hover {{
            background-color: rgba(102, 102, 102, 200);
        }}
        QPushButton:pressed {{
            background-color: rgba(85, 85, 85, 255);
        }}
    """
    
    FAVORITE_BUTTON_ACTIVE = """
        QPushButton {{
            background-color: rgba(231, 76, 60, 200);
            color: white;
            border: none;
            border-radius: 18px;
            font-size: 18px;
            font-weight: bold;
            width: 36px;
            height: 36px;
        }}
        QPushButton:hover {{
            background-color: rgba(192, 57, 43, 255);
        }}
        QPushButton:pressed {{
            background-color: rgba(169, 50, 38, 255);
        }}
    """
    
    # 信息标签样式
    INFO_LABEL_STYLE = """
        QLabel {{
            color: #bbb;
            font-size: 11px;
            font-weight: 400;
            background-color: rgba(0, 0, 0, 0.7);
            border: none;
            border-radius: 4px;
            padding: 2px 6px;
            margin: 2px;
        }}
    """
    
    # 加载状态样式
    LOADING_STYLE = """
        QLabel {{
            color: #0078d4;
            font-size: 14px;
            font-weight: 600;
            background-color: rgba(0, 120, 212, 0.1);
            border: 2px dashed #0078d4;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
    """
    
    # 错误状态样式
    ERROR_STYLE = """
        QLabel {{
            color: #e74c3c;
            font-size: 14px;
            font-weight: 600;
            background-color: rgba(231, 76, 60, 0.1);
            border: 2px dashed #e74c3c;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
    """
    
    @staticmethod
    def get_frame_style(is_selected=False, is_favorite=False, theme='dark'):
        """获取框架样式"""
        if theme == 'dark':
            if is_selected:
                border_color = '#0078d4'
                bg_color = 'rgba(0, 120, 212, 0.1)'
                hover_border_color = '#106ebe'
                hover_bg_color = 'rgba(0, 120, 212, 0.15)'
            elif is_favorite:
                border_color = '#e74c3c'
                bg_color = 'rgba(231, 76, 60, 0.05)'
                hover_border_color = '#c0392b'
                hover_bg_color = 'rgba(231, 76, 60, 0.1)'
            else:
                border_color = '#444'
                bg_color = 'rgba(68, 68, 68, 0.1)'
                hover_border_color = '#666'
                hover_bg_color = 'rgba(102, 102, 102, 0.15)'
        else:  # light theme
            if is_selected:
                border_color = '#0078d4'
                bg_color = 'rgba(0, 120, 212, 0.1)'
                hover_border_color = '#106ebe'
                hover_bg_color = 'rgba(0, 120, 212, 0.15)'
            elif is_favorite:
                border_color = '#e74c3c'
                bg_color = 'rgba(231, 76, 60, 0.05)'
                hover_border_color = '#c0392b'
                hover_bg_color = 'rgba(231, 76, 60, 0.1)'
            else:
                border_color = '#ccc'
                bg_color = 'rgba(255, 255, 255, 0.8)'
                hover_border_color = '#999'
                hover_bg_color = 'rgba(240, 240, 240, 0.9)'
        
        return ThumbnailStyle.BASE_FRAME_STYLE.format(
            border_color=border_color,
            bg_color=bg_color,
            hover_border_color=hover_border_color,
            hover_bg_color=hover_bg_color
        )
    
    @staticmethod
    def get_image_label_style(theme='dark'):
        """获取图片标签样式"""
        text_color = '#fff' if theme == 'dark' else '#333'
        return ThumbnailStyle.IMAGE_LABEL_STYLE.format(text_color=text_color)
    
    @staticmethod
    def get_favorite_button_style(is_favorite=False):
        """获取收藏按钮样式"""
        return ThumbnailStyle.FAVORITE_BUTTON_ACTIVE if is_favorite else ThumbnailStyle.FAVORITE_BUTTON_NORMAL
    
    @staticmethod
    def get_info_label_style():
        """获取信息标签样式"""
        return ThumbnailStyle.INFO_LABEL_STYLE

    @staticmethod
    def get_id_overlay_style():
        """获取ID毛玻璃叠层样式"""
        return ThumbnailStyle.ID_OVERLAY_STYLE
    
    @staticmethod
    def get_loading_style():
        """获取加载状态样式"""
        return ThumbnailStyle.LOADING_STYLE
    
    @staticmethod
    def get_error_style():
        """获取错误状态样式"""
        return ThumbnailStyle.ERROR_STYLE


class ImageThumbnail(QFrame):
    """重构后的图片缩略图组件"""
    
    # 信号定义
    clicked = pyqtSignal(dict)  # 点击信号，传递图片数据
    favorite_toggled = pyqtSignal(dict, bool)  # 收藏切换信号
    selected = pyqtSignal(object)  # 选中信号，传递自身
    
    def __init__(self, image_data: Dict[str, Any], 
                 thumbnail_size: Tuple[int, int] = (200, 200),
                 image_loader=None, event_manager=None,
                 transform_mode_getter=None,
                 blur_if_e: bool = False,
                 blur_radius: int = 6):
        super().__init__()
        
        # 基础属性
        self._image_data = image_data
        self._thumbnail_size = thumbnail_size
        self._image_loader = image_loader
        self._event_manager = event_manager
        self._transform_mode_getter = transform_mode_getter
        self._blur_if_e = bool(blur_if_e)
        try:
            self._blur_radius = max(0, int(blur_radius))
        except Exception:
            self._blur_radius = 6
        
        # 状态属性
        self._state = ThumbnailState.PLACEHOLDER
        self._is_selected = False
        self._is_favorited = image_data.get('is_favorite', False)
        
        # UI组件
        self._image_label: Optional[QLabel] = None
        self._info_label: Optional[QLabel] = None
        self._id_overlay: Optional[QLabel] = None
        self._view_button: Optional[QPushButton] = None
        self._favorite_button: Optional[QPushButton] = None
        
        # 动画相关
        self._hover_animation = None
        self._click_animation = None
        self._fade_animation = None
        
        # 初始化
        self._setup_ui()
        self._connect_signals()
        self._update_styles()
        
        # 先添加阴影效果（供悬停动画使用），再设置动画
        self._setup_shadow_effect()
        self._setup_animations()
        
        # 注册到事件管理器
        if self._event_manager:
            self._event_image_data = self._image_data  # 为事件管理器设置数据引用
            self._event_manager.register_thumbnail(self, self._image_data)
        
        # 开始加载图片
        if self._image_loader:
            self._load_image()
    
    @property
    def image_data(self) -> Dict[str, Any]:
        """获取图片数据"""
        return self._image_data
    
    @property
    def is_selected(self) -> bool:
        """获取选中状态"""
        return self._is_selected
    
    @property
    def is_favorited(self) -> bool:
        """获取收藏状态"""
        return self._is_favorited
    
    @property
    def state(self) -> ThumbnailState:
        """获取当前状态"""
        return self._state
    
    def _setup_ui(self):
        """设置UI组件"""
        # 设置框架属性
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedSize(
            self._thumbnail_size[0] + 20,
            self._thumbnail_size[1] + 20
        )
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        
        # 图片标签
        self._image_label = QLabel()
        self._image_label.setFixedSize(*self._thumbnail_size)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setScaledContents(False)
        layout.addWidget(self._image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 叠加在图片上的ID毛玻璃标签
        self._id_overlay = QLabel(self._image_label)
        self._id_overlay.setText("")
        self._id_overlay.setStyleSheet(ThumbnailStyle.get_id_overlay_style())
        self._id_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._id_overlay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._id_overlay.hide()  # 初始隐藏，待有ID后显示
        
        # 信息标签（移除：不再在卡片中显示标签框）
        self._info_label = None
        
        # 已移除底部按钮区域，缩略图居中显示
        
        # 更新信息显示
        self._update_info_display()
    
    def _connect_signals(self):
        """连接信号"""
        # 已移除查看按钮，点击缩略图由事件管理器或外部处理
    
    def _update_info_display(self):
        """更新信息显示"""
        if not self._info_label:
            return

        # 构建信息文本
        info_parts = []
        
        # ID信息（仅在图片上显示，不在信息栏重复）
        image_id = self._image_data.get('id', 'N/A')
        
        # 标签信息（最多显示2个）
        tags = self._image_data.get('tags', [])
        if tags:
            display_tags = tags[:2]
            tag_text = ', '.join(display_tags)
            if len(tags) > 2:
                tag_text += f" (+{len(tags) - 2})"
            info_parts.append(f"标签: {tag_text}")
        
        self._info_label.setText('\n'.join(info_parts))

        # 不再显示图片上的ID叠层
        if self._id_overlay:
            self._id_overlay.hide()
    
    def _load_image(self):
        """加载图片"""
        if not self._image_loader:
            self._set_state(ThumbnailState.PLACEHOLDER)
            return
        
        # 优先尝试按ID从本地缩略图目录加载
        try:
            image_id = self._image_data.get('id')
            if image_id and hasattr(self._image_loader, 'cache_manager') and hasattr(self._image_loader.cache_manager, 'load_thumbnail'):
                cached_pm = self._image_loader.cache_manager.load_thumbnail(image_id)
                if cached_pm and not cached_pm.isNull():
                    # 如有需要再进行适配缩放
                    scaled_pm = cached_pm.scaled(
                        self._thumbnail_size[0],
                        self._thumbnail_size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    if self._image_label:
                        self._image_label.setPixmap(scaled_pm)
                        self._image_label.setStyleSheet(ThumbnailStyle.get_image_label_style())
                        try:
                            self._apply_content_blur_if_needed()
                        except Exception:
                            pass
                    self._set_state(ThumbnailState.LOADED)
                    return
        except Exception:
            # 本地缩略图读取异常则回退到网络加载
            pass

        # 获取最佳图片URL
        url = self._get_best_image_url()
        if not url:
            self._set_state(ThumbnailState.PLACEHOLDER)
            return
        
        # 设置加载状态
        self._set_state(ThumbnailState.LOADING)
        
        # 开始加载（支持缓存管理器和普通加载器）
        if hasattr(self._image_loader, 'load_thumbnail'):
            # 使用缓存管理器
            cached = self._image_loader.load_thumbnail(url, self._thumbnail_size, priority=True)
            if not cached:
                # 未从缓存返回，等待加载完成信号
                pass
        else:
            # 使用普通图片加载器
            self._image_loader.load_image(url, thumbnail_size=self._thumbnail_size)
    
    def _get_best_image_url(self) -> Optional[str]:
        """获取最佳图片URL"""
        # 优先级：缩略图 -> 预览图 -> 原图
        for key in ['thumbnail_url', 'preview_url', 'file_url']:
            url = self._image_data.get(key)
            if url:
                return url
        return None
    
    def _set_state(self, state: ThumbnailState):
        """设置状态"""
        if self._state == state:
            return
        
        old_state = self._state
        self._state = state
        self._update_image_display()
        self._update_styles()
        
        # 通知事件管理器状态变化
        if self._event_manager and state in [ThumbnailState.LOADING, ThumbnailState.LOADED]:
            is_loading = (state == ThumbnailState.LOADING)
            self._event_manager.notify_loading_state_changed(self, is_loading)
    
    def _update_image_display(self):
        """更新图片显示"""
        if not self._image_label:
            return
        
        state_text_map = {
            ThumbnailState.LOADING: "加载中...",
            ThumbnailState.ERROR: "加载失败",
            ThumbnailState.PLACEHOLDER: "无图片",
            ThumbnailState.LOADED: ""
        }
        
        if self._state != ThumbnailState.LOADED:
            self._image_label.setText(state_text_map.get(self._state, ""))
            self._image_label.setPixmap(QPixmap())
            
            # 根据状态设置样式
            if self._state == ThumbnailState.LOADING:
                self._image_label.setStyleSheet(ThumbnailStyle.get_loading_style())
            elif self._state == ThumbnailState.ERROR:
                self._image_label.setStyleSheet(ThumbnailStyle.get_error_style())
            else:
                self._image_label.setStyleSheet(ThumbnailStyle.get_image_label_style())
    
    def _update_styles(self):
        """更新样式"""
        # 更新框架样式
        frame_style = ThumbnailStyle.get_frame_style(
            is_selected=self._is_selected,
            is_favorite=False,  # 取消收藏变红效果
            theme='dark'  # 可以从配置中获取
        )
        self.setStyleSheet(frame_style)
        
        # 更新图片标签样式
        if self._image_label:
            self._image_label.setStyleSheet(
                ThumbnailStyle.get_image_label_style(theme='dark')
            )
        
        # 信息标签样式更新已移除

        # 移除ID叠层样式更新（不显示）
        
        # 已移除按钮样式更新
        
        # 已移除收藏按钮样式更新

    # 已移除卡片上的收藏按钮，不再提供卡片内收藏切换
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        if self._is_selected == selected:
            return
        
        self._is_selected = selected
        self._update_styles()
    
    def set_favorited(self, favorited: bool):
        """设置收藏状态"""
        if self._is_favorited == favorited:
            return
        
        self._is_favorited = favorited
        self._update_styles()
    
    def on_image_loaded(self, url: str, pixmap: QPixmap):
        """处理图片加载完成"""
        if url != self._get_best_image_url():
            return
        
        if self._image_label:
            # 缩放图片以适应缩略图大小
            mode = Qt.TransformationMode.SmoothTransformation
            try:
                if callable(self._transform_mode_getter):
                    mode = self._transform_mode_getter()
            except Exception:
                pass
            scaled_pixmap = pixmap.scaled(
                self._thumbnail_size[0], 
                self._thumbnail_size[1], 
                Qt.AspectRatioMode.KeepAspectRatio, 
                mode
            )
            self._image_label.setPixmap(scaled_pixmap)
            # 恢复正常的图片标签样式
            self._image_label.setStyleSheet(ThumbnailStyle.get_image_label_style())
            try:
                self._apply_content_blur_if_needed()
            except Exception:
                pass
            # 不再定位/显示ID叠层

        # 将缩略图按ID保存到隐藏目录，避免刷新后无法加载
        try:
            image_id = self._image_data.get('id')
            if image_id and hasattr(self._image_loader, 'cache_manager') and hasattr(self._image_loader.cache_manager, 'save_thumbnail'):
                # 使用已缩放的缩略图保存
                target_pm = self._image_label.pixmap() if self._image_label and self._image_label.pixmap() else pixmap
                self._image_loader.cache_manager.save_thumbnail(image_id, target_pm)
        except Exception:
            pass
        
        self._set_state(ThumbnailState.LOADED)

    def _apply_content_blur_if_needed(self):
        try:
            if not self._image_label:
                return
            r = str(self._image_data.get('rating', '')).lower()
            if self._blur_if_e and r == 'e' and self._blur_radius > 0:
                eff = QGraphicsBlurEffect()
                eff.setBlurRadius(self._blur_radius)
                self._image_label.setGraphicsEffect(eff)
            else:
                self._image_label.setGraphicsEffect(None)
        except Exception:
            pass

    def update_blur_policy(self, blur_if_e: bool, blur_radius: int):
        try:
            self._blur_if_e = bool(blur_if_e)
            self._blur_radius = max(0, int(blur_radius))
            self._apply_content_blur_if_needed()
        except Exception:
            pass
    
    def on_image_failed(self, url: str, error: str):
        """处理图片加载失败"""
        if url != self._get_best_image_url():
            return
        
        self._set_state(ThumbnailState.ERROR)
    
    def mousePressEvent(self, event: QMouseEvent):
        """处理鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_click()
            # 如果有事件管理器，通过事件管理器处理
            if self._event_manager:
                self._event_manager.handle_mouse_press(self, event)
            else:
                # 传统方式处理
                self.selected.emit(self)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._animate_hover_enter()
        if self._event_manager:
            self._event_manager.handle_mouse_enter(self, event)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._animate_hover_leave()
        if self._event_manager:
            self._event_manager.handle_mouse_leave(self, event)
        super().leaveEvent(event)
    
    def _setup_shadow_effect(self):
        """设置阴影效果"""
        self._shadow_effect = QGraphicsDropShadowEffect()
        self._shadow_effect.setBlurRadius(15)
        self._shadow_effect.setColor(QColor(0, 0, 0, 80))
        self._shadow_effect.setOffset(0, 3)
        self.setGraphicsEffect(self._shadow_effect)

    def _position_id_overlay(self):
        """根据图片大小定位ID毛玻璃叠层"""
        if not self._image_label or not self._id_overlay:
            return
        w = self._image_label.width()
        h = self._image_label.height()
        margin = 8
        overlay_h = 26
        self._id_overlay.setGeometry(margin, h - overlay_h - margin, w - margin * 2, overlay_h)
    
    def _setup_animations(self):
        """设置动画效果"""
        # 悬停动画：改为阴影模糊半径动画，避免修改几何导致布局抖动
        if hasattr(self, '_shadow_effect') and self._shadow_effect:
            self._hover_animation = QPropertyAnimation(self._shadow_effect, b"blurRadius")
            self._hover_animation.setDuration(150)
            self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        else:
            self._hover_animation = None

        # 点击动画：改为不影响布局的透明度闪烁
        self._click_animation = QPropertyAnimation(self, b"windowOpacity")
        self._click_animation.setDuration(100)
        self._click_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 淡入淡出动画（保留）
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    def _animate_hover_enter(self):
        """悬停进入动画（阴影增强）"""
        if self._hover_animation and self._hover_animation.state() != QPropertyAnimation.State.Running:
            start_radius = self._shadow_effect.blurRadius() if hasattr(self, '_shadow_effect') and self._shadow_effect else 15
            end_radius = min(start_radius + 6, 24)
            self._hover_animation.setStartValue(start_radius)
            self._hover_animation.setEndValue(end_radius)
            self._hover_animation.start()
    
    def _animate_hover_leave(self):
        """悬停离开动画（阴影恢复）"""
        if self._hover_animation and self._hover_animation.state() != QPropertyAnimation.State.Running:
            start_radius = self._shadow_effect.blurRadius() if hasattr(self, '_shadow_effect') and self._shadow_effect else 21
            end_radius = 15
            self._hover_animation.setStartValue(start_radius)
            self._hover_animation.setEndValue(end_radius)
            self._hover_animation.start()
    
    def _animate_click(self):
        """点击动画（轻微透明度闪烁，不改变布局）"""
        if self._click_animation and self._click_animation.state() != QPropertyAnimation.State.Running:
            self._click_animation.setStartValue(1.0)
            self._click_animation.setEndValue(0.9)
            self._click_animation.finished.connect(self._animate_click_restore)
            self._click_animation.start()
    
    def _animate_click_restore(self):
        """点击恢复动画"""
        if self._click_animation:
            try:
                self._click_animation.finished.disconnect()
            except Exception:
                pass
            self._click_animation.setStartValue(self.windowOpacity())
            self._click_animation.setEndValue(1.0)
            self._click_animation.start()
    
    def update_image_data(self, image_data: Dict[str, Any]):
        """更新图片数据"""
        self._image_data = image_data
        self._update_info_display()
        
        # 如果URL发生变化，重新加载图片
        if self._image_loader:
            self._load_image()
