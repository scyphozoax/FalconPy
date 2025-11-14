# -*- coding: utf-8 -*-
"""
缩略图事件管理器
统一处理缩略图的各种事件和状态变化
"""

from typing import Dict, List, Optional, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QMouseEvent, QEnterEvent
from PyQt6.QtWidgets import QWidget
from enum import Enum


class ThumbnailEventType(Enum):
    """缩略图事件类型"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER_ENTER = "hover_enter"
    HOVER_LEAVE = "hover_leave"
    SELECTION_CHANGED = "selection_changed"
    FAVORITE_TOGGLED = "favorite_toggled"
    LOADING_STATE_CHANGED = "loading_state_changed"


class ThumbnailEventData:
    """缩略图事件数据"""
    
    def __init__(self, event_type: ThumbnailEventType, thumbnail_widget, image_data: dict, **kwargs):
        self.event_type = event_type
        self.thumbnail_widget = thumbnail_widget
        self.image_data = image_data
        self.timestamp = kwargs.get('timestamp')
        self.mouse_event = kwargs.get('mouse_event')
        self.extra_data = kwargs


class ThumbnailEventManager(QObject):
    """缩略图事件管理器"""
    
    # 事件信号
    thumbnail_clicked = pyqtSignal(object)  # ThumbnailEventData
    thumbnail_double_clicked = pyqtSignal(object)
    thumbnail_right_clicked = pyqtSignal(object)
    thumbnail_hovered = pyqtSignal(object)
    thumbnail_unhovered = pyqtSignal(object)
    thumbnail_selected = pyqtSignal(object)
    thumbnail_deselected = pyqtSignal(object)
    thumbnail_favorite_toggled = pyqtSignal(object)
    thumbnail_loading_changed = pyqtSignal(object)
    
    # 批量事件信号
    selection_changed = pyqtSignal(list)  # 选中的缩略图列表
    
    def __init__(self):
        super().__init__()
        
        # 状态管理
        self.selected_thumbnails: List[QWidget] = []
        self.hovered_thumbnail: Optional[QWidget] = None
        self.loading_thumbnails: Dict[QWidget, bool] = {}
        
        # 事件处理器注册表
        self.event_handlers: Dict[ThumbnailEventType, List[Callable]] = {
            event_type: [] for event_type in ThumbnailEventType
        }
        
        # 双击检测
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self._handle_single_click)
        self.pending_click_data: Optional[ThumbnailEventData] = None
        self.double_click_interval = 300  # 300ms双击间隔
        
        # 悬停检测
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._handle_hover_timeout)
        self.hover_delay = 200  # 200ms悬停延迟
        
        # 多选支持
        self.multi_select_enabled = False
        self.selection_mode = 'single'  # 'single', 'multi', 'range'
    
    def register_thumbnail(self, thumbnail_widget, image_data: dict):
        """注册缩略图组件"""
        # 设置事件过滤器
        thumbnail_widget.installEventFilter(self)
        
        # 存储图片数据
        if not hasattr(thumbnail_widget, '_event_image_data'):
            thumbnail_widget._event_image_data = image_data
    
    def unregister_thumbnail(self, thumbnail_widget):
        """注销缩略图组件"""
        thumbnail_widget.removeEventFilter(self)
        
        # 清理状态
        if thumbnail_widget in self.selected_thumbnails:
            self.selected_thumbnails.remove(thumbnail_widget)
        
        if thumbnail_widget == self.hovered_thumbnail:
            self.hovered_thumbnail = None
        
        if thumbnail_widget in self.loading_thumbnails:
            del self.loading_thumbnails[thumbnail_widget]
    
    def eventFilter(self, obj: QObject, event) -> bool:
        """事件过滤器"""
        if not hasattr(obj, '_event_image_data'):
            return False
        
        image_data = obj._event_image_data
        
        # 鼠标点击事件
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._handle_mouse_press(obj, image_data, event)
            elif event.button() == Qt.MouseButton.RightButton:
                self._emit_event(ThumbnailEventType.RIGHT_CLICK, obj, image_data, mouse_event=event)
        
        # 鼠标双击事件
        elif event.type() == event.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self._handle_double_click(obj, image_data, event)
        
        # 鼠标进入事件
        elif event.type() == event.Type.Enter:
            self._handle_hover_enter(obj, image_data, event)
        
        # 鼠标离开事件
        elif event.type() == event.Type.Leave:
            self._handle_hover_leave(obj, image_data, event)
        
        return False
    
    def _handle_mouse_press(self, thumbnail_widget, image_data: dict, event: QMouseEvent):
        """处理鼠标按下事件"""
        # 创建事件数据
        event_data = ThumbnailEventData(
            ThumbnailEventType.CLICK,
            thumbnail_widget,
            image_data,
            mouse_event=event
        )
        
        # 启动双击检测定时器
        if self.click_timer.isActive():
            # 如果定时器正在运行，说明可能是双击
            self.click_timer.stop()
            self._handle_double_click(thumbnail_widget, image_data, event)
        else:
            # 延迟处理单击，等待可能的双击
            self.pending_click_data = event_data
            self.click_timer.start(self.double_click_interval)
    
    def _handle_single_click(self):
        """处理单击事件"""
        if self.pending_click_data:
            self._emit_event_data(self.pending_click_data)
            self._handle_selection(self.pending_click_data)
            self.pending_click_data = None
    
    def _handle_double_click(self, thumbnail_widget, image_data: dict, event: QMouseEvent):
        """处理双击事件"""
        event_data = ThumbnailEventData(
            ThumbnailEventType.DOUBLE_CLICK,
            thumbnail_widget,
            image_data,
            mouse_event=event
        )
        self._emit_event_data(event_data)
        self.pending_click_data = None
    
    def _handle_hover_enter(self, thumbnail_widget, image_data: dict, event):
        """处理鼠标进入事件"""
        self.hovered_thumbnail = thumbnail_widget
        
        # 延迟触发悬停事件
        self.hover_timer.start(self.hover_delay)
        
        event_data = ThumbnailEventData(
            ThumbnailEventType.HOVER_ENTER,
            thumbnail_widget,
            image_data
        )
        self._emit_event_data(event_data)
    
    def _handle_hover_leave(self, thumbnail_widget, image_data: dict, event):
        """处理鼠标离开事件"""
        if self.hovered_thumbnail == thumbnail_widget:
            self.hovered_thumbnail = None
        
        self.hover_timer.stop()
        
        event_data = ThumbnailEventData(
            ThumbnailEventType.HOVER_LEAVE,
            thumbnail_widget,
            image_data
        )
        self._emit_event_data(event_data)
    
    def _handle_hover_timeout(self):
        """处理悬停超时"""
        if self.hovered_thumbnail:
            # 可以在这里触发悬停相关的操作，如显示详细信息
            pass
    
    def _handle_selection(self, event_data: ThumbnailEventData):
        """处理选择逻辑"""
        thumbnail = event_data.thumbnail_widget
        
        if self.selection_mode == 'single':
            # 单选模式
            if thumbnail not in self.selected_thumbnails:
                # 清除之前的选择
                for selected in self.selected_thumbnails[:]:
                    self._deselect_thumbnail(selected)
                
                # 选中当前缩略图
                self._select_thumbnail(thumbnail, event_data.image_data)
        
        elif self.selection_mode == 'multi':
            # 多选模式
            if thumbnail in self.selected_thumbnails:
                self._deselect_thumbnail(thumbnail)
            else:
                self._select_thumbnail(thumbnail, event_data.image_data)
        
        # 发送选择变化信号
        self.selection_changed.emit(self.selected_thumbnails[:])
    
    def _select_thumbnail(self, thumbnail_widget, image_data: dict):
        """选中缩略图"""
        if thumbnail_widget not in self.selected_thumbnails:
            self.selected_thumbnails.append(thumbnail_widget)
            
            # 更新缩略图的选中状态
            if hasattr(thumbnail_widget, 'set_selected'):
                thumbnail_widget.set_selected(True)
            
            # 发送选中事件
            event_data = ThumbnailEventData(
                ThumbnailEventType.SELECTION_CHANGED,
                thumbnail_widget,
                image_data,
                selected=True
            )
            self._emit_event_data(event_data)
    
    # 公共接口方法
    def handle_mouse_press(self, thumbnail_widget, event: QMouseEvent):
        """处理鼠标按下事件"""
        if hasattr(thumbnail_widget, '_event_image_data'):
            self._handle_mouse_press(thumbnail_widget, thumbnail_widget._event_image_data, event)
    
    def handle_mouse_enter(self, thumbnail_widget, event):
        """处理鼠标进入事件"""
        if hasattr(thumbnail_widget, '_event_image_data'):
            self._handle_hover_enter(thumbnail_widget, thumbnail_widget._event_image_data, event)
    
    def handle_mouse_leave(self, thumbnail_widget, event):
        """处理鼠标离开事件"""
        if hasattr(thumbnail_widget, '_event_image_data'):
            self._handle_hover_leave(thumbnail_widget, thumbnail_widget._event_image_data, event)
    
    def _deselect_thumbnail(self, thumbnail_widget):
        """取消选中缩略图"""
        if thumbnail_widget in self.selected_thumbnails:
            self.selected_thumbnails.remove(thumbnail_widget)
            
            # 更新缩略图的选中状态
            if hasattr(thumbnail_widget, 'set_selected'):
                thumbnail_widget.set_selected(False)
            
            # 发送取消选中事件
            if hasattr(thumbnail_widget, '_event_image_data'):
                event_data = ThumbnailEventData(
                    ThumbnailEventType.SELECTION_CHANGED,
                    thumbnail_widget,
                    thumbnail_widget._event_image_data,
                    selected=False
                )
                self._emit_event_data(event_data)
    
    def _emit_event_data(self, event_data: ThumbnailEventData):
        """发送事件数据"""
        self._emit_event(
            event_data.event_type,
            event_data.thumbnail_widget,
            event_data.image_data,
            **event_data.extra_data
        )
    
    def _emit_event(self, event_type: ThumbnailEventType, thumbnail_widget, image_data: dict, **kwargs):
        """发送事件信号"""
        event_data = ThumbnailEventData(event_type, thumbnail_widget, image_data, **kwargs)
        
        # 发送对应的信号
        if event_type == ThumbnailEventType.CLICK:
            self.thumbnail_clicked.emit(event_data)
        elif event_type == ThumbnailEventType.DOUBLE_CLICK:
            self.thumbnail_double_clicked.emit(event_data)
        elif event_type == ThumbnailEventType.RIGHT_CLICK:
            self.thumbnail_right_clicked.emit(event_data)
        elif event_type == ThumbnailEventType.HOVER_ENTER:
            self.thumbnail_hovered.emit(event_data)
        elif event_type == ThumbnailEventType.HOVER_LEAVE:
            self.thumbnail_unhovered.emit(event_data)
        elif event_type == ThumbnailEventType.SELECTION_CHANGED:
            if kwargs.get('selected', False):
                self.thumbnail_selected.emit(event_data)
            else:
                self.thumbnail_deselected.emit(event_data)
        elif event_type == ThumbnailEventType.FAVORITE_TOGGLED:
            self.thumbnail_favorite_toggled.emit(event_data)
        elif event_type == ThumbnailEventType.LOADING_STATE_CHANGED:
            self.thumbnail_loading_changed.emit(event_data)
        
        # 调用注册的处理器
        for handler in self.event_handlers.get(event_type, []):
            try:
                handler(event_data)
            except Exception as e:
                print(f"事件处理器错误: {e}")
    
    def register_event_handler(self, event_type: ThumbnailEventType, handler: Callable):
        """注册事件处理器"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: ThumbnailEventType, handler: Callable):
        """注销事件处理器"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def set_selection_mode(self, mode: str):
        """设置选择模式"""
        if mode in ['single', 'multi', 'range']:
            self.selection_mode = mode
    
    def clear_selection(self):
        """清除所有选择"""
        for thumbnail in self.selected_thumbnails[:]:
            self._deselect_thumbnail(thumbnail)
    
    def select_all(self, thumbnails: List[QWidget]):
        """选择所有缩略图（多选模式下）"""
        if self.selection_mode != 'multi':
            return
        
        for thumbnail in thumbnails:
            if hasattr(thumbnail, '_event_image_data'):
                self._select_thumbnail(thumbnail, thumbnail._event_image_data)
    
    def get_selected_thumbnails(self) -> List[QWidget]:
        """获取选中的缩略图列表"""
        return self.selected_thumbnails[:]
    
    def get_selected_image_data(self) -> List[dict]:
        """获取选中的图片数据列表"""
        return [thumb._event_image_data for thumb in self.selected_thumbnails 
                if hasattr(thumb, '_event_image_data')]
    
    def notify_loading_state_changed(self, thumbnail_widget, is_loading: bool):
        """通知加载状态变化"""
        self.loading_thumbnails[thumbnail_widget] = is_loading
        
        if hasattr(thumbnail_widget, '_event_image_data'):
            event_data = ThumbnailEventData(
                ThumbnailEventType.LOADING_STATE_CHANGED,
                thumbnail_widget,
                thumbnail_widget._event_image_data,
                is_loading=is_loading
            )
            self._emit_event_data(event_data)
    
    def notify_favorite_toggled(self, thumbnail_widget, is_favorite: bool):
        """通知收藏状态变化"""
        if hasattr(thumbnail_widget, '_event_image_data'):
            event_data = ThumbnailEventData(
                ThumbnailEventType.FAVORITE_TOGGLED,
                thumbnail_widget,
                thumbnail_widget._event_image_data,
                is_favorite=is_favorite
            )
            self._emit_event_data(event_data)