# -*- coding: utf-8 -*-
"""
图片网格组件
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QPushButton, QScrollArea, QFrame, QSizePolicy, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QResizeEvent, QGuiApplication
from .image_loader import ImageLoader
from .thumbnail import ImageThumbnail
from .thumbnail_cache import ThumbnailCache
from .thumbnail_events import ThumbnailEventManager
from ...core.cache_manager import CacheManager
from ...core.i18n import I18n

class ImageGridWidget(QWidget):
    """图片网格组件"""
    
    image_selected = pyqtSignal(dict)  # 图片选择信号
    favorite_added = pyqtSignal(dict)  # 收藏添加信号
    page_changed = pyqtSignal(int)     # 页面变化信号
    download_requested = pyqtSignal(dict)  # 下载请求信号（交由主窗口处理）
    refresh_requested = pyqtSignal()   # 刷新请求（主窗口执行当前站点刷新）
    
    def __init__(self, cache_manager: CacheManager = None, i18n: I18n = None, use_advanced_cache: bool = True, use_event_manager: bool = True):
        super().__init__()
        self.images = []
        self.current_page = 1
        self.total_pages = 1
        self.columns = 4  # 默认列数
        self.min_columns = 1  # 最小列数
        self.max_columns = 8  # 最大列数
        self.thumbnail_size = (200, 200)
        self.selected_image = None  # 当前选中的图片
        self.selected_thumbnail = None  # 当前选中的缩略图组件
        
        # 缩略图组件缓存
        self.thumbnail_widgets = []  # 缓存的缩略图组件列表
        
        # 事件管理器
        self.event_manager = None
        if use_event_manager:
            self.event_manager = ThumbnailEventManager()
            self._connect_event_manager()
        
        # 响应式布局相关
        self.auto_columns = True  # 是否自动调整列数
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.update_columns_for_width)
        self.resize_debounce_delay = 150  # 150ms延迟（防抖机制）

        # 滚动状态与降质缩放
        self.is_scrolling = False
        self.scroll_settle_timer = QTimer()
        self.scroll_settle_timer.setSingleShot(True)
        self.scroll_settle_timer.timeout.connect(self._on_scroll_settled)
        
        # i18n
        self.i18n = i18n or I18n()

        # 初始化缓存管理器和图片加载器
        if cache_manager is None:
            from ...core.config import Config
            config = Config()
            cache_dir = config.app_dir / "cache" / "images"
            max_disk_mb = config.get("cache.max_size", 1000)
            max_mem_mb = config.get("cache.max_memory", 200)
            cache_manager = CacheManager(str(cache_dir), max_size_mb=int(max_disk_mb), max_memory_cache_mb=int(max_mem_mb))
        
        self.cache_manager = cache_manager
        
        # 选择加载器类型
        if use_advanced_cache:
            # 使用高级缓存管理器
            try:
                from ...core.config import Config
                cfg = Config()
                concurrent = int(cfg.get("network.concurrent_downloads", 5))
            except Exception:
                concurrent = 5
            self.image_loader = ThumbnailCache(cache_manager, max_concurrent=concurrent)
            # 连接缓存管理器的信号
            self.image_loader.thumbnail_loaded.connect(self.on_image_loaded)
            self.image_loader.thumbnail_failed.connect(self.on_image_failed)
        else:
            # 使用普通图片加载器
            try:
                from ...core.config import Config
                cfg = Config()
                concurrent = int(cfg.get("network.concurrent_downloads", 5))
            except Exception:
                concurrent = 5
            self.image_loader = ImageLoader(cache_manager, max_concurrent=concurrent)
            # 连接普通加载器的信号
            self.image_loader.image_loaded.connect(self.on_image_loaded)
            self.image_loader.load_failed.connect(self.on_image_failed)
        
        self.setup_ui()
    
    def _connect_event_manager(self):
        """连接事件管理器的信号"""
        if self.event_manager:
            self.event_manager.thumbnail_clicked.connect(self._on_event_thumbnail_clicked)
            self.event_manager.thumbnail_double_clicked.connect(self._on_event_thumbnail_double_clicked)
            self.event_manager.thumbnail_hovered.connect(self._on_event_thumbnail_hovered)
            self.event_manager.thumbnail_unhovered.connect(self._on_event_thumbnail_unhovered)
            self.event_manager.thumbnail_selected.connect(self._on_event_thumbnail_selected)
            self.event_manager.thumbnail_favorite_toggled.connect(self._on_event_thumbnail_favorite_toggled)
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 网格容器
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)

        # 为网格容器启用自定义右键菜单
        try:
            self.grid_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.grid_widget.customContextMenuRequested.connect(self._show_context_menu)
        except Exception:
            pass
        
        self.scroll_area.setWidget(self.grid_widget)
        layout.addWidget(self.scroll_area)
        try:
            vs = self.scroll_area.verticalScrollBar()
            hs = self.scroll_area.horizontalScrollBar()
            if vs:
                vs.valueChanged.connect(self._on_scroll_changed)
            if hs:
                hs.valueChanged.connect(self._on_scroll_changed)
        except Exception:
            pass
        QTimer.singleShot(200, self._preload_viewport)

        # 分页控制
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton(self.i18n.t("上一页"))
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        
        self.page_label = QLabel(self.i18n.t("第 {page} 页 / 共 {total} 页").format(page=1, total=1))
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_button = QPushButton(self.i18n.t("下一页"))
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.next_button)
        
        layout.addLayout(pagination_layout)
    
    def resizeEvent(self, event: QResizeEvent):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        if self.auto_columns:
            # 使用定时器延迟更新，避免频繁重绘（防抖机制）
            self.resize_timer.start(self.resize_debounce_delay)
    
    def calculate_optimal_columns(self, width: int) -> int:
        """根据宽度计算最优列数"""
        # 计算单个缩略图的总宽度（包括边距和间距）
        thumbnail_width = self.thumbnail_size[0] + 20  # 缩略图宽度 + 边框
        spacing = self.grid_layout.spacing()  # 网格间距
        margins = self.grid_layout.contentsMargins()
        available_width = width - margins.left() - margins.right() - 20  # 减去滚动条宽度
        
        # 计算可以容纳的列数
        if available_width <= 0:
            return self.min_columns
        
        # 考虑间距的列数计算
        columns = max(1, (available_width + spacing) // (thumbnail_width + spacing))
        
        # 限制在最小和最大列数之间
        return max(self.min_columns, min(self.max_columns, columns))
    
    def update_columns_for_width(self):
        """根据当前宽度更新列数"""
        if not self.auto_columns:
            return
        
        current_width = self.scroll_area.width()
        optimal_columns = self.calculate_optimal_columns(current_width)
        
        # 只有在列数真正改变时才更新布局
        if optimal_columns != self.columns:
            self.columns = optimal_columns
            # 只重新排列，不重新创建组件
            if self.thumbnail_widgets:
                self.rearrange_existing_thumbnails()
                # 添加弹性空间
                self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
                # 更新最小宽度
                self.update_minimum_width()
    
    def set_images(self, images: list, page: int = 1, total_pages: int = 1):
        """设置图片列表"""
        self.images = images
        self.current_page = page
        self.total_pages = total_pages
        
        self.update_grid()
        self.update_pagination()
        
        if hasattr(self.image_loader, 'preload_thumbnails') and images:
            urls = []
            for img in images:
                url = (img.get('thumbnail_url') or
                       img.get('preview_url') or
                       img.get('file_url'))
                if url:
                    urls.append(url)
            if urls:
                first_count = max(self.columns, min(len(urls), self.columns * 2))
                for u in urls[:first_count]:
                    if hasattr(self.image_loader, 'load_thumbnail'):
                        self.image_loader.load_thumbnail(u, self.thumbnail_size, priority=True)
                remaining = urls[first_count:]
                if remaining:
                    self.image_loader.preload_thumbnails(remaining, self.thumbnail_size)
        QTimer.singleShot(100, self._preload_viewport)
    
    def clear_thumbnail_cache(self):
        """清除缓存的缩略图组件"""
        for thumbnail in self.thumbnail_widgets:
            thumbnail.setParent(None)
        self.thumbnail_widgets.clear()
        self.selected_image = None
        self.selected_thumbnail = None
    
    def update_grid(self):
        """更新网格显示"""
        if not self.thumbnail_widgets:
            self.recreate_thumbnails()
        else:
            prev_keys = [self._image_key(w.image_data) for w in self.thumbnail_widgets]
            new_keys = [self._image_key(img) for img in self.images]
            if prev_keys == new_keys:
                self.rearrange_existing_thumbnails()
            else:
                self._update_thumbnails_incremental()
        
        # 添加弹性空间
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
        
        # 更新最小宽度以确保至少显示1列
        self.update_minimum_width()

    def rearrange_existing_thumbnails(self):
        """重新排列现有的缩略图组件"""
        # 从布局中移除所有组件，但不删除
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                self.grid_layout.removeItem(item)
        
        # 若当前无缩略图，直接返回，避免未定义变量
        if not self.thumbnail_widgets:
            return

        # 重新添加到新的位置
        for i, thumbnail in enumerate(self.thumbnail_widgets):
            row = i // self.columns
            col = i % self.columns
            self.grid_layout.addWidget(thumbnail, row, col)
    
    def _show_context_menu(self, pos):
        """显示右键菜单：区分卡片与空白区域。
        优先从点击点向上回溯查找 ImageThumbnail，避免命中子控件导致识别失败。"""
        try:
            target = self.grid_widget.childAt(pos)
        except Exception:
            target = None
        # 回溯到父级以命中缩略图根组件
        thumb_widget = target
        try:
            while thumb_widget and not isinstance(thumb_widget, ImageThumbnail) and thumb_widget != self.grid_widget:
                thumb_widget = thumb_widget.parentWidget()
        except Exception:
            pass

        menu = QMenu(self)

        if isinstance(thumb_widget, ImageThumbnail) and hasattr(thumb_widget, 'image_data'):
            img = thumb_widget.image_data
            # 卡片菜单：以当前卡片为作用对象，不改变选择状态
            act_refresh = menu.addAction(self.i18n.t("刷新"))
            act_preview = menu.addAction(self.i18n.t("预览图片"))
            act_fav = menu.addAction(self.i18n.t("添加到收藏"))
            act_copy = menu.addAction(self.i18n.t("复制图片链接"))
            act_download = menu.addAction(self.i18n.t("下载图片"))
            act_open = menu.addAction(self.i18n.t("在浏览器打开"))

            action = menu.exec(self.grid_widget.mapToGlobal(pos))
            if not action:
                return
            if action == act_refresh:
                try:
                    self.refresh_requested.emit()
                except Exception:
                    pass
            elif action == act_preview:
                self.image_selected.emit(img)
            elif action == act_fav:
                self.favorite_added.emit(img)
            elif action == act_copy:
                self._copy_image_link(img)
            elif action == act_download:
                self.download_requested.emit(img)
            elif action == act_open:
                try:
                    import webbrowser
                    url = img.get('post_url') or img.get('file_url') or img.get('preview_url') or img.get('thumbnail_url')
                    if url:
                        webbrowser.open(url)
                except Exception:
                    pass
        else:
            # 空白区域菜单：不涉及具体图片，避免误操作
            act_refresh = menu.addAction(self.i18n.t("刷新"))
            act_prev = menu.addAction(self.i18n.t("上一页"))
            act_next = menu.addAction(self.i18n.t("下一页"))
            act_clear = menu.addAction(self.i18n.t("清除选择"))

            action = menu.exec(self.grid_widget.mapToGlobal(pos))
            if not action:
                return
            if action == act_refresh:
                try:
                    self.refresh_requested.emit()
                except Exception:
                    pass
            elif action == act_prev:
                self.prev_page()
            elif action == act_next:
                self.next_page()
            elif action == act_clear:
                self.clear_selection()

    def _copy_image_link(self, image_data: dict):
        """复制图片有效链接到剪贴板（优先 file_url）"""
        url = image_data.get('file_url') or image_data.get('preview_url') or image_data.get('thumbnail_url')
        if not url:
            return
        try:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(url)
        except Exception:
            pass
    
    def recreate_thumbnails(self):
        """重新创建缩略图组件"""
        # 清除现有组件
        self.clear_thumbnail_cache()
        
        # 创建新的缩略图组件
        for i, image_data in enumerate(self.images):
            row = i // self.columns
            col = i % self.columns
            
            thumbnail = ImageThumbnail(
                image_data=image_data, 
                thumbnail_size=self.thumbnail_size, 
                image_loader=self.image_loader,
                event_manager=self.event_manager,
                transform_mode_getter=self.get_transform_mode
            )
            
            # 连接信号（如果没有使用事件管理器）
            if not self.event_manager:
                thumbnail.clicked.connect(self.image_selected.emit)
                thumbnail.favorite_clicked.connect(self.favorite_added.emit)
                thumbnail.selected.connect(self.on_thumbnail_selected)
            
            self.thumbnail_widgets.append(thumbnail)
            self.grid_layout.addWidget(thumbnail, row, col)

    def _image_key(self, image_data: dict) -> str:
        url = image_data.get('thumbnail_url') or image_data.get('preview_url') or image_data.get('file_url')
        if url:
            return url
        return str(image_data.get('id', ''))

    def _update_thumbnails_incremental(self):
        existing = {}
        for w in self.thumbnail_widgets:
            k = self._image_key(w.image_data)
            existing[k] = w

        new_widgets = []
        used_keys = set()
        for img in self.images:
            k = self._image_key(img)
            w = existing.get(k)
            if w:
                if w.image_data is not img:
                    w.update_image_data(img)
                new_widgets.append(w)
                used_keys.add(k)
            else:
                row = len(new_widgets) // self.columns
                col = len(new_widgets) % self.columns
                w = ImageThumbnail(
                    image_data=img,
                    thumbnail_size=self.thumbnail_size,
                    image_loader=self.image_loader,
                    event_manager=self.event_manager,
                    transform_mode_getter=self.get_transform_mode
                )
                if not self.event_manager:
                    w.clicked.connect(self.image_selected.emit)
                    w.favorite_clicked.connect(self.favorite_added.emit)
                    w.selected.connect(self.on_thumbnail_selected)
                new_widgets.append(w)

        for w in self.thumbnail_widgets:
            k = self._image_key(w.image_data)
            if k not in used_keys:
                w.setParent(None)

        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                self.grid_layout.removeItem(item)

        self.thumbnail_widgets = new_widgets
        for i, w in enumerate(self.thumbnail_widgets):
            row = i // self.columns
            col = i % self.columns
            self.grid_layout.addWidget(w, row, col)

    def _on_scroll_changed(self, *args):
        try:
            self.is_scrolling = True
            self.scroll_settle_timer.start(120)
            if hasattr(self.image_loader, 'set_paused'):
                self.image_loader.set_paused(True)
        except Exception:
            pass

    def _on_scroll_settled(self):
        try:
            self.is_scrolling = False
            if hasattr(self.image_loader, 'set_paused'):
                self.image_loader.set_paused(False)
            self._preload_viewport()
        except Exception:
            pass

    def get_transform_mode(self):
        from PyQt6.QtCore import Qt as _Qt
        return _Qt.TransformationMode.FastTransformation if self.is_scrolling else _Qt.TransformationMode.SmoothTransformation

    def _preload_viewport(self):
        try:
            vp = self.scroll_area.viewport()
            if not vp:
                return
            h = vp.height()
            tile_h = self.thumbnail_size[1] + 80
            y = self.scroll_area.verticalScrollBar().value()
            start_row = max(0, y // tile_h)
            vis_rows = max(1, (h // tile_h) + 2)
            end_row = start_row + vis_rows
            urls = []
            for i, img in enumerate(self.images):
                row = i // max(1, self.columns)
                if start_row - 1 <= row <= end_row + 1:
                    u = img.get('thumbnail_url') or img.get('preview_url') or img.get('file_url')
                    if u:
                        urls.append(u)
            if urls and hasattr(self.image_loader, 'preload_thumbnails'):
                self.image_loader.preload_thumbnails(urls, self.thumbnail_size)
        except Exception:
            pass
    
    # 事件管理器的事件处理方法
    def _on_event_thumbnail_clicked(self, event_data):
        """处理缩略图点击事件"""
        thumbnail = event_data.thumbnail_widget
        if hasattr(thumbnail, 'image_data'):
            self.on_thumbnail_selected(thumbnail)
    
    def _on_event_thumbnail_double_clicked(self, event_data):
        """处理缩略图双击事件"""
        thumbnail = event_data.thumbnail_widget
        if hasattr(thumbnail, 'image_data'):
            # 双击时发送选择信号并可能触发预览
            self.image_selected.emit(thumbnail.image_data)
    
    def _on_event_thumbnail_hovered(self, event_data):
        """处理缩略图悬停事件"""
        # 可以在这里添加悬停效果，比如显示工具提示
        pass
    
    def _on_event_thumbnail_unhovered(self, event_data):
        """处理缩略图取消悬停事件"""
        # 清理悬停效果
        pass
    
    def _on_event_thumbnail_selected(self, event_data):
        """处理缩略图选择事件"""
        thumbnail = event_data.thumbnail_widget
        if hasattr(thumbnail, 'image_data'):
            self.on_thumbnail_selected(thumbnail)
    
    def _on_event_thumbnail_favorite_toggled(self, event_data):
        """处理缩略图收藏状态切换事件"""
        thumbnail = event_data.thumbnail_widget
        if hasattr(thumbnail, 'image_data'):
            self.favorite_added.emit(thumbnail.image_data)
    
    def update_minimum_width(self):
        """更新最小宽度以确保至少显示1列"""
        thumbnail_width = self.thumbnail_size[0] + 20  # 缩略图宽度 + 边框
        margins = self.grid_layout.contentsMargins()
        min_width = thumbnail_width + margins.left() + margins.right() + 40  # 额外空间
        
        # 设置主窗口的最小宽度
        main_window = self.window()
        if main_window:
            current_min_width = main_window.minimumWidth()
            if min_width > current_min_width:
                main_window.setMinimumWidth(min_width)

    def on_image_loaded(self, url: str, pixmap: QPixmap):
        """图片加载完成处理"""
        # 查找对应的缩略图组件并更新
        for thumbnail in self.thumbnail_widgets:
            if isinstance(thumbnail, ImageThumbnail):
                # 使用新的ImageThumbnail组件的属性
                thumb_url = thumbnail.image_data.get('thumbnail_url')
                preview_url = thumbnail.image_data.get('preview_url')
                file_url = thumbnail.image_data.get('file_url')
                if url in (thumb_url, preview_url, file_url):
                    thumbnail.on_image_loaded(url, pixmap)
                    break
    
    def on_image_failed(self, url: str, error: str):
        """图片加载失败处理"""
        # 查找对应的缩略图组件并显示错误
        for thumbnail in self.thumbnail_widgets:
            if isinstance(thumbnail, ImageThumbnail):
                # 使用新的ImageThumbnail组件的属性
                thumb_url = thumbnail.image_data.get('thumbnail_url')
                preview_url = thumbnail.image_data.get('preview_url')
                file_url = thumbnail.image_data.get('file_url')
                if url in (thumb_url, preview_url, file_url):
                    thumbnail.on_image_failed(url, error)
                    break
    
    def update_pagination(self):
        """更新分页控制"""
        try:
            text = self.i18n.t("第 {page} 页 / 共 {total} 页").format(page=self.current_page, total=self.total_pages)
        except Exception:
            text = f"第 {self.current_page} 页 / 共 {self.total_pages} 页"
        self.page_label.setText(text)
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.page_changed.emit(self.current_page)
    
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.page_changed.emit(self.current_page)
    
    def set_columns(self, columns: int):
        """设置列数"""
        self.columns = columns
        self.update_grid()
    
    def set_thumbnail_size(self, size: tuple):
        """设置缩略图大小"""
        self.thumbnail_size = size
        self.update_grid()
    
    def on_thumbnail_selected(self, thumbnail):
        """处理缩略图选择"""
        # 取消之前选中的缩略图
        if self.selected_thumbnail and self.selected_thumbnail != thumbnail:
            self.selected_thumbnail.set_selected(False)
        
        # 设置新的选中状态
        self.selected_thumbnail = thumbnail
        if hasattr(thumbnail, 'image_data'):
            self.selected_image = thumbnail.image_data
        else:
            self.selected_image = None
        
        # 确保缩略图有set_selected方法
        if hasattr(thumbnail, 'set_selected'):
            thumbnail.set_selected(True)
    
    def get_selected_image(self):
        """获取当前选中的图片数据"""
        return self.selected_image
    
    def clear_selection(self):
        """清除选择"""
        if self.selected_thumbnail:
            self.selected_thumbnail.set_selected(False)
        self.selected_thumbnail = None
        self.selected_image = None
    
    def select_first_image(self):
        """选择第一张图片"""
        if self.thumbnail_widgets:
            first_thumbnail = self.thumbnail_widgets[0]
            if isinstance(first_thumbnail, ImageThumbnail):
                self.on_thumbnail_selected(first_thumbnail)
    
    @property
    def current_images(self):
        """当前显示的图片列表（兼容性属性）"""
        return self.images
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.image_loader:
            if hasattr(self.image_loader, 'cleanup'):
                self.image_loader.cleanup()
            else:
                self.image_loader.stop()
        # 退出时清理已保存的缩略图目录
        try:
            if hasattr(self, 'cache_manager') and self.cache_manager and hasattr(self.cache_manager, 'clear_thumbnails'):
                self.cache_manager.clear_thumbnails()
        except Exception:
            pass
        self.clear_thumbnail_cache()
        super().closeEvent(event)
