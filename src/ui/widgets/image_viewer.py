# -*- coding: utf-8 -*-
"""
图片查看器组件
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QWidget, QTextEdit,
                             QSplitter, QFrame, QProgressBar, QTextBrowser,
                             QMenu, QApplication, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QGraphicsTextItem, QStackedLayout,
                             QMainWindow)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QThread, pyqtSlot, QPoint, QPointF
from PyQt6.QtGui import QPixmap, QFont, QKeySequence, QShortcut, QCursor, QFontMetrics
from PyQt6.QtGui import QTransform, QAction, QPainter, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .gif_player import GifPlayer
from .video_controls import VideoControls
from ...core.i18n import I18n
from ...core.config import Config

class ImageDownloadThread(QThread):
    """图片下载线程"""
    
    download_finished = pyqtSignal(bytes)
    download_failed = pyqtSignal(str)
    download_progress = pyqtSignal(int, int)  # current, total
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.session = None
    
    def run(self):
        """运行下载"""
        asyncio.run(self.download_image())
    
    async def download_image(self):
        """异步下载图片"""
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.url) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        data = b''
                        
                        async for chunk in response.content.iter_chunked(8192):
                            data += chunk
                            downloaded += len(chunk)
                            if total_size > 0:
                                self.download_progress.emit(downloaded, total_size)
                        
                        self.download_finished.emit(data)
                    else:
                        self.download_failed.emit(f"HTTP错误: {response.status}")
        except aiohttp.ClientError as e:
            try:
                self.download_failed.emit(f"网络错误: {e}")
            except Exception:
                pass
        except Exception as e:
            try:
                self.download_failed.emit(f"未知错误: {e}")
            except Exception:
                pass



class MoebooruResolveFileUrlThread(QThread):
    """Moebooru（Konachan/Yande.re）原图链接解析线程。
    解析帖子查看页以获取原图直链（file_url）。
    """

    resolved = pyqtSignal(dict)  # {file_url, ext}
    failed = pyqtSignal(str)

    def __init__(self, post_url: str):
        super().__init__()
        self.post_url = post_url

    def run(self):
        try:
            asyncio.run(self._resolve())
        except Exception as e:
            self.failed.emit(f"解析异常: {e}")

    async def _resolve(self):
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.post_url) as resp:
                if resp.status != 200:
                    self.failed.emit(f"HTTP错误: {resp.status}")
                    return
                html = await resp.text()

        file_url = self._extract_file_url(html)
        if not file_url:
            self.failed.emit("未找到原图链接")
            return

        abs_url = urljoin(self.post_url, file_url)
        ext = abs_url.split('?')[0].split('.')[-1].lower()
        self.resolved.emit({'file_url': abs_url, 'ext': ext})

    def _extract_file_url(self, html: str) -> str | None:
        # 采用 lxml 优先解析，失败回退到 html.parser
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')

        # 1) 高分辨率原图链接（常见为 a#highres 或 a.directlink）
        try:
            a = soup.select_one('a#highres')
            if a and a.get('href'):
                return a.get('href')
            a = soup.select_one('a.directlink')
            if a and a.get('href'):
                return a.get('href')
        except Exception:
            pass

        # 2) 图片标签本身可能包含原图或大图链接信息
        try:
            img = soup.select_one('img#image') or soup.select_one('img.image')
            if img:
                for key in ('data-file-url', 'data-original', 'data-large-src', 'data-src', 'src'):
                    if img.get(key):
                        return img.get(key)
        except Exception:
            pass

        # 3) 其它可能的原图链接：/image/、/data/、/jpeg/、/png/ 等
        try:
            for a in soup.find_all('a'):
                href = a.get('href') or ''
                if not href:
                    continue
                text = (a.get_text() or '').strip().lower()
                if any(k in text for k in ('original', 'download', '原图', '下载')):
                    return href
                if any(seg in href for seg in ('/image/', '/data/', '/jpeg/', '/png/')):
                    if href.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        return href
        except Exception:
            pass

        # 4) 作为回退，尝试 og:image（可能是样图，但有时也是原图）
        try:
            meta = soup.find('meta', attrs={'property': 'og:image'})
            if meta and meta.get('content'):
                return meta.get('content')
        except Exception:
            pass

        return None


class ZoomableImageLabel(QGraphicsView):
    """基于 QGraphicsView 的成熟图片查看组件"""
    
    zoom_changed = pyqtSignal(float)  # 缩放变化信号：当前scale_factor

    def __init__(self):
        super().__init__()
        # 场景与图元
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.text_item = QGraphicsTextItem("")
        self.text_item.setDefaultTextColor(QColor("#cccccc"))
        self.text_item.setVisible(False)
        self.scene.addItem(self.text_item)

        # 状态
        self.scale_factor = 1.0
        self.rotation_degrees = 0
        self.flip_horizontal_flag = False
        self.flip_vertical_flag = False
        self.original_pixmap = None
        self.setMinimumSize(400, 300)
        self.setStyleSheet("border: 1px solid #666; background-color: #1e1e1e;")
        # 居中对齐，确保缩小时图片仍保持在中心
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 初始关闭拖拽，缩放>100%时再开启手型拖拽
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        # 视图配置（鼠标位置为缩放中心、无滚动条）
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 鼠标拖拽相关
        self.dragging = False
        self.last_pan_point = QPoint()
        self.image_offset = QPoint(0, 0)
        # 取消拖拽阈值，始终允许拖拽
        self.drag_enable_threshold = 0.0

        # 启用鼠标跟踪和右键菜单
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def get_dpr(self) -> float:
        """获取当前屏幕设备像素比（DPR）"""
        try:
            win = self.window()
            if win and hasattr(win, 'windowHandle') and win.windowHandle():
                screen = win.windowHandle().screen()
                if screen:
                    return float(screen.devicePixelRatio())
        except Exception:
            pass
        try:
            screen = QApplication.primaryScreen()
            if screen:
                return float(screen.devicePixelRatio())
        except Exception:
            pass
        return 1.0
    
    def set_pixmap(self, pixmap: QPixmap):
        """设置图片"""
        self.original_pixmap = pixmap
        self.pixmap_item.setPixmap(pixmap)
        # 隐藏任何错误/提示文本
        self.text_item.setVisible(False)
        self.scale_factor = 1.0
        self.image_offset = QPoint(0, 0)  # 重置偏移
        # 更新场景矩形以便居中对齐
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.update_display()

    def setText(self, text: str):
        """显示提示文本（用于错误或缺失URL）"""
        try:
            # 清空图片并显示文本
            self.original_pixmap = None
            self.pixmap_item.setPixmap(QPixmap())
            self.text_item.setPlainText(text or "")
            # 设置居中位置
            rect = self.text_item.boundingRect()
            view_size = self.viewport().size()
            pos = QPointF(
                max(0.0, (view_size.width() - rect.width()) / 2),
                max(0.0, (view_size.height() - rect.height()) / 2)
            )
            self.text_item.setPos(pos)
            self.text_item.setVisible(True)
            # 场景矩形覆盖视窗大小，保证文本居中
            self.scene.setSceneRect(0, 0, view_size.width(), view_size.height())
            # 重置缩放
            self.scale_factor = 1.0
            self.setTransform(QTransform())
        except Exception:
            # 兜底：若出现异常，至少不崩溃
            self.text_item.setVisible(True)
    
    def update_display(self):
        """更新显示"""
        if self.original_pixmap:
            # 图元变换：仅负责旋转与镜像
            item_transform = QTransform()
            if self.rotation_degrees % 360 != 0:
                item_transform.rotate(self.rotation_degrees)
            if self.flip_horizontal_flag:
                item_transform.scale(-1, 1)
            if self.flip_vertical_flag:
                item_transform.scale(1, -1)
            self.pixmap_item.setTransform(item_transform)

            # 视图缩放：负责缩放并保持居中
            view_transform = QTransform()
            view_transform.scale(self.scale_factor, self.scale_factor)
            self.setTransform(view_transform)
            try:
                self.zoom_changed.emit(self.scale_factor)
            except Exception:
                pass

            # 更新场景矩形；缩放≤100%时居中，>100%时保持用户拖拽位置
            self.scene.setSceneRect(self.pixmap_item.sceneBoundingRect())
            if self.scale_factor <= 1.0:
                self.centerOn(self.pixmap_item)
    
    def zoom_in(self):
        """放大"""
        self.scale_factor = min(self.scale_factor * 1.25, 5.0)
        self.update_display()
    
    def zoom_out(self):
        """缩小"""
        self.scale_factor = max(self.scale_factor / 1.25, 0.1)
        self.update_display()
    
    def reset_zoom(self):
        """重置缩放"""
        # 100% 表示对准屏幕像素：图像像素与设备像素 1:1
        dpr = self.get_dpr()
        self.scale_factor = 1.0 / max(dpr, 1.0)
        self.image_offset = QPoint(0, 0)  # 重置偏移
        self.setTransform(QTransform())
        self.update_display()
    
    def fit_to_window(self):
        """适应窗口"""
        if self.original_pixmap:
            # 计算旋转/镜像后的包围盒（使用图元变换后的场景边界）
            # 需要使用 QPointF 而不是 QPoint
            self.pixmap_item.setTransformOriginPoint(QPointF(self.original_pixmap.rect().center()))
            item_transform = QTransform()
            if self.rotation_degrees % 360 != 0:
                item_transform.rotate(self.rotation_degrees)
            if self.flip_horizontal_flag:
                item_transform.scale(-1, 1)
            if self.flip_vertical_flag:
                item_transform.scale(1, -1)
            self.pixmap_item.setTransform(item_transform)

            rect = self.pixmap_item.sceneBoundingRect()
            view_size = self.viewport().size()
            scale_x = view_size.width() / max(1, rect.width())
            scale_y = view_size.height() / max(1, rect.height())
            self.scale_factor = min(scale_x, scale_y, 1.0)
            self.setTransform(QTransform().scale(self.scale_factor, self.scale_factor))
            self.image_offset = QPoint(0, 0)
            self.scene.setSceneRect(self.pixmap_item.sceneBoundingRect())
            self.centerOn(self.pixmap_item)

    def rotate_left(self):
        """左旋90度"""
        self.rotation_degrees = (self.rotation_degrees - 90) % 360
        self.update_display()

    def rotate_right(self):
        """右旋90度"""
        self.rotation_degrees = (self.rotation_degrees + 90) % 360
        self.update_display()

    def flip_horizontal(self):
        """水平镜像"""
        self.flip_horizontal_flag = not self.flip_horizontal_flag
        self.update_display()

    def flip_vertical(self):
        """垂直镜像"""
        self.flip_vertical_flag = not self.flip_vertical_flag
        self.update_display()
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放（不按Ctrl直接缩放，且不滚动）"""
        old_scale = self.scale_factor
        if event.angleDelta().y() > 0:
            self.scale_factor = min(self.scale_factor * 1.15, 5.0)
        else:
            self.scale_factor = max(self.scale_factor / 1.15, 0.1)
        if self.original_pixmap and old_scale != self.scale_factor:
            self.update_display()
        # 阻止滚轮滚动默认行为
        event.accept()
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_pan_point = event.position().toPoint()
            # 使用自定义拖拽逻辑，不依赖内置ScrollHandDrag（更稳定）
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging:
            # 自定义平移：基于滚动条进行视图平移（不限制缩放阈值）
            current_pos = event.position().toPoint()
            delta = current_pos - self.last_pan_point
            self.last_pan_point = current_pos
            try:
                hbar = self.horizontalScrollBar()
                vbar = self.verticalScrollBar()
                if hbar:
                    hbar.setValue(hbar.value() - delta.x())
                if vbar:
                    vbar.setValue(vbar.value() - delta.y())
            except Exception:
                pass
        else:
            # 鼠标悬停时始终为可拖动手型
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.dragging = False
        # 释放后恢复可拖动手型
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """窗口尺寸变化时保持居中"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.scene.setSceneRect(self.pixmap_item.sceneBoundingRect())
            if self.scale_factor <= 1.0:
                self.centerOn(self.pixmap_item)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            # 保持自定义拖拽逻辑，不使用内置拖拽模式
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().mouseReleaseEvent(event)
    
    def copy_image(self):
        """复制图片到剪贴板"""
        if self.original_pixmap:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.original_pixmap)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 缩放操作
        zoom_in_action = QAction("放大 (+)", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小 (-)", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("重置缩放 (100%)", self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        menu.addAction(reset_zoom_action)
        
        fit_window_action = QAction("适应窗口", self)
        fit_window_action.triggered.connect(self.fit_to_window)
        menu.addAction(fit_window_action)
        
        menu.addSeparator()
        
        # 旋转操作
        rotate_left_action = QAction("左旋 90°", self)
        rotate_left_action.triggered.connect(self.rotate_left)
        menu.addAction(rotate_left_action)
        
        rotate_right_action = QAction("右旋 90°", self)
        rotate_right_action.triggered.connect(self.rotate_right)
        menu.addAction(rotate_right_action)
        
        menu.addSeparator()
        
        # 镜像操作
        flip_h_action = QAction("水平镜像", self)
        flip_h_action.triggered.connect(self.flip_horizontal)
        menu.addAction(flip_h_action)
        
        flip_v_action = QAction("垂直镜像", self)
        flip_v_action.triggered.connect(self.flip_vertical)
        menu.addAction(flip_v_action)
        
        menu.addSeparator()
        
        # 复制操作
        copy_action = QAction("复制图片", self)
        copy_action.triggered.connect(self.copy_image)
        menu.addAction(copy_action)
        
        # 在鼠标位置显示菜单
        menu.exec(self.mapToGlobal(position))
    
    def copy_image_to_clipboard(self):
        """复制图片到剪贴板"""
        if self.original_pixmap:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.original_pixmap)


class ImageViewerDialog(QMainWindow):
    """图片查看器窗口"""
    
    favorite_toggled = pyqtSignal(dict, bool)  # image_data, is_favorite
    download_requested = pyqtSignal(dict)      # image_data
    tag_clicked = pyqtSignal(str)              # tag name
    
    def __init__(self, image_data: dict, parent=None, images_list: list | None = None, current_index: int | None = None):
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
        self.image_data = image_data
        self.images_list = images_list or []
        # 如果未提供索引则尝试通过ID匹配
        if current_index is None and self.images_list:
            try:
                cur_id = image_data.get('id')
                cur_site = image_data.get('site')
                self.current_index = next((i for i, it in enumerate(self.images_list)
                                           if it.get('id') == cur_id and it.get('site') == cur_site), 0)
            except Exception:
                self.current_index = 0
        else:
            self.current_index = current_index or 0
        self.is_favorite = False
        self.download_thread = None
        self.media_player = None
        
        # 新的GIF播放器
        self.gif_player = GifPlayer(self)
        self.gif_player.frame_changed.connect(self._on_gif_frame_changed)
        self.gif_player.playback_finished.connect(self._on_gif_playback_finished)
        
        # 视频控制组件
        self.video_controls = VideoControls(self)
        self.video_controls.hide()  # 默认隐藏，只在播放视频时显示
        self.setup_ui()
        self.setup_shortcuts()
        self.load_image()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.i18n.t("图片查看器"))
        self.setMinimumSize(1000, 700)
        self.resize(1280, 820)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图片显示区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 工具栏（重排为三行：导航/缩放/变换）
        toolbar_top_layout = QHBoxLayout()
        toolbar_mid_layout = QHBoxLayout()
        toolbar_bottom_layout = QHBoxLayout()
        
        self.zoom_in_btn = QPushButton(self.i18n.t("放大 (+)"))
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        self.zoom_out_btn = QPushButton(self.i18n.t("缩小 (-)"))
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        self.reset_zoom_btn = QPushButton(self.i18n.t("重置 (0)"))
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        self.fit_window_btn = QPushButton(self.i18n.t("适应窗口 (F)"))
        self.fit_window_btn.clicked.connect(self.fit_to_window)
        
        self.fullscreen_btn = QPushButton(self.i18n.t("全屏 (F11)"))
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        # 导航
        self.prev_btn = QPushButton(self.i18n.t("上一张"))
        self.prev_btn.clicked.connect(self.prev_image)
        self.next_btn = QPushButton(self.i18n.t("下一张"))
        self.next_btn.clicked.connect(self.next_image)

        # 旋转/镜像
        self.rotate_left_btn = QPushButton(self.i18n.t("左旋↺"))
        self.rotate_left_btn.clicked.connect(self.rotate_left)
        self.rotate_right_btn = QPushButton(self.i18n.t("右旋↻"))
        self.rotate_right_btn.clicked.connect(self.rotate_right)
        self.flip_h_btn = QPushButton(self.i18n.t("水平镜像"))
        self.flip_h_btn.clicked.connect(self.flip_horizontal)
        self.flip_v_btn = QPushButton(self.i18n.t("垂直镜像"))
        self.flip_v_btn.clicked.connect(self.flip_vertical)

        # 缩放显示标签（保留百分比，不使用滑块）
        self.zoom_label = QLabel("100%")
        
        # 顶部：导航 + 全屏
        toolbar_top_layout.setSpacing(8)
        toolbar_top_layout.addWidget(self.prev_btn)
        toolbar_top_layout.addWidget(self.next_btn)
        toolbar_top_layout.addStretch()
        toolbar_top_layout.addWidget(self.fullscreen_btn)

        # 中部：缩放 + 缩放百分比
        toolbar_mid_layout.setSpacing(8)
        toolbar_mid_layout.addWidget(self.zoom_in_btn)
        toolbar_mid_layout.addWidget(self.zoom_out_btn)
        toolbar_mid_layout.addWidget(self.reset_zoom_btn)
        toolbar_mid_layout.addWidget(self.fit_window_btn)
        toolbar_mid_layout.addSpacing(12)
        try:
            self.zoom_label.setStyleSheet("padding: 0 6px;")
        except Exception:
            pass
        toolbar_mid_layout.addWidget(self.zoom_label)
        toolbar_mid_layout.addStretch()

        # 底部：旋转与镜像
        toolbar_bottom_layout.setSpacing(8)
        toolbar_bottom_layout.addWidget(self.rotate_left_btn)
        toolbar_bottom_layout.addWidget(self.rotate_right_btn)
        toolbar_bottom_layout.addWidget(self.flip_h_btn)
        toolbar_bottom_layout.addWidget(self.flip_v_btn)

        left_layout.addLayout(toolbar_top_layout)
        left_layout.addLayout(toolbar_mid_layout)
        left_layout.addLayout(toolbar_bottom_layout)
        # 根据文本自动调整按钮最小宽度，避免多语言下截断
        self._adjust_buttons_width([
            self.prev_btn, self.next_btn, self.fullscreen_btn,
            self.zoom_in_btn, self.zoom_out_btn, self.reset_zoom_btn, self.fit_window_btn,
            self.rotate_left_btn, self.rotate_right_btn, self.flip_h_btn, self.flip_v_btn
        ])
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图片标签或视频播放器（堆叠容器，避免替换导致旧widget被删除）
        self.viewer_container = QWidget()
        self.viewer_stack = QStackedLayout(self.viewer_container)
        self.image_label = ZoomableImageLabel()
        # 连接缩放变化信号以实时更新百分比显示
        try:
            self.image_label.zoom_changed.connect(lambda _sf: self.sync_zoom_ui())
        except Exception:
            pass
        
        # 创建视频播放容器，包含视频播放器和控制组件
        self.video_container = QWidget()
        video_container_layout = QVBoxLayout(self.video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        video_container_layout.setSpacing(0)
        
        self.video_widget = QVideoWidget()
        video_container_layout.addWidget(self.video_widget)
        video_container_layout.addWidget(self.video_controls)
        
        self.viewer_stack.addWidget(self.image_label)
        self.viewer_stack.addWidget(self.video_container)
        self.viewer_stack.setCurrentWidget(self.image_label)
        
        # 进度条（加粗显示）
        self.progress_bar = QProgressBar()
        # 固定高度使进度条更粗
        try:
            self.progress_bar.setFixedHeight(18)
        except Exception:
            pass
        # 基础样式，适配暗色主题；不改动配色体系时仍可生效
        try:
            self.progress_bar.setStyleSheet(
                """
                QProgressBar {
                    min-height: 18px;
                    max-height: 18px;
                    border: 1px solid #3a3a3a;
                    border-radius: 9px;
                    background-color: #1e1e1e;
                    padding: 1px;
                    text-align: right;
                }
                QProgressBar::chunk {
                    background-color: #2aa7ff;
                    border-radius: 9px;
                }
                """
            )
        except Exception:
            pass
        self.progress_bar.hide()
        
        self.scroll_area.setWidget(self.viewer_container)
        left_layout.addWidget(self.scroll_area)
        left_layout.addWidget(self.progress_bar)
        
        # 右侧：信息面板
        right_widget = QWidget()
        right_widget.setFixedWidth(300)
        right_layout = QVBoxLayout(right_widget)
        
        # 基本信息
        info_frame = QFrame()
        # 为右侧信息区域添加边界框以明确分区
        try:
            info_frame.setFrameShape(QFrame.Shape.StyledPanel)
            info_frame.setFrameShadow(QFrame.Shadow.Plain)
        except Exception:
            pass
        info_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #5a5a5a;
                border-radius: 6px;
                padding: 8px;
            }
            """
        )
        info_frame.setFrameStyle(QFrame.Shape.NoFrame)  # 移除边框
        info_layout = QVBoxLayout(info_frame)
        
        # 标题
        title_label = QLabel(self.i18n.t("图片信息"))
        title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        info_layout.addWidget(title_label)
        
        # 详细信息
        self.info_text = QTextBrowser()
        self.info_text.setMaximumHeight(200)
        self.info_text.setReadOnly(True)
        self.info_text.setOpenExternalLinks(True)
        # 统一滚动条样式为标签栏样式，并保持背景透明
        self.info_text.setStyleSheet(
            """
            QTextBrowser {
                background: transparent;
                border: none;
                font-size: 13px;
            }
            QTextBrowser QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 0;
            }
            QTextBrowser QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 20px;
                border-radius: 6px;
            }
            QTextBrowser QScrollBar::handle:vertical:hover {
                background: #787878;
            }
            QTextBrowser QScrollBar::add-line:vertical,
            QTextBrowser QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QTextBrowser QScrollBar::add-page:vertical,
            QTextBrowser QScrollBar::sub-page:vertical {
                background: none;
            }
            """
        )
        self.update_info_text()
        info_layout.addWidget(self.info_text)
        
        # 标签信息（合并到同一框架，不再分两个Box）
        tags_title = QLabel(self.i18n.t("标签"))
        tags_title.setFont(QFont("", 12, QFont.Weight.Bold))
        tags_title.setStyleSheet("margin-top: 10px;")
        info_layout.addWidget(tags_title) # 添加到info_layout
        
        self.tags_text = QTextBrowser()
        self.tags_text.setReadOnly(True)
        self.tags_text.setOpenLinks(False) # 避免点击后内容被清空
        self.tags_text.setOpenExternalLinks(False)
        self.tags_text.anchorClicked.connect(self.on_tag_anchor_clicked)
        
        # 使用“芯片”样式替代文本链接，统一滚动条样式
        self.tags_text.setStyleSheet(
            """
            QTextBrowser { 
                background: transparent; 
                border: none; 
                font-size: 13px; 
            }
            QTextBrowser QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 0;
            }
            QTextBrowser QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 20px;
                border-radius: 6px;
            }
            QTextBrowser QScrollBar::handle:vertical:hover {
                background: #787878;
            }
            QTextBrowser QScrollBar::add-line:vertical,
            QTextBrowser QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QTextBrowser QScrollBar::add-page:vertical,
            QTextBrowser QScrollBar::sub-page:vertical {
                background: none;
            }
            a { 
                color: #e0e0e0; 
                background-color: #3e3e3e; 
                padding: 4px 8px; 
                border-radius: 10px; 
                text-decoration: none; 
                margin-right: 6px; 
            }
            a:hover { 
                background-color: #5a5a5a; 
            }
            """
        )
        self.tags_text.viewport().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_tags_text()
        info_layout.addWidget(self.tags_text) # 添加到info_layout
        
        right_layout.addWidget(info_frame)
        
        # 操作按钮
        button_layout = QVBoxLayout()
        
        self.favorite_btn = QPushButton(self.i18n.t("♡ 添加收藏"))
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        
        self.download_btn = QPushButton(self.i18n.t("下载原图"))
        self.download_btn.clicked.connect(self.download_image)

        self.open_source_btn = QPushButton(self.i18n.t("打开原页面"))
        self.open_source_btn.clicked.connect(self.open_source_page)

        # 复制链接按钮
        self.copy_post_btn = QPushButton(self.i18n.t("复制帖子链接"))
        self.copy_post_btn.clicked.connect(self.copy_post_link)
        self.copy_image_btn = QPushButton(self.i18n.t("复制图片链接"))
        self.copy_image_btn.clicked.connect(self.copy_image_link)
        self.copy_source_btn = QPushButton(self.i18n.t("复制来源链接"))
        self.copy_source_btn.clicked.connect(self.copy_source_link)
        self.copy_tags_btn = QPushButton(self.i18n.t("复制标签"))
        self.copy_tags_btn.clicked.connect(self.copy_tags_text)

        # 原图/大图切换
        self.toggle_original_btn = QPushButton(self.i18n.t("切换为大图"))
        self.toggle_original_btn.clicked.connect(self.toggle_original)
        self.use_original = True
        
        button_layout.addWidget(self.favorite_btn)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.open_source_btn)
        button_layout.addWidget(self.copy_post_btn)
        button_layout.addWidget(self.copy_image_btn)
        button_layout.addWidget(self.copy_source_btn)
        button_layout.addWidget(self.copy_tags_btn)
        button_layout.addWidget(self.toggle_original_btn)
        button_layout.addStretch()
        
        right_layout.addLayout(button_layout)
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([800, 300])
        
        main_layout.addWidget(splitter)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 窗口菜单
        window_menu = menubar.addMenu(self.i18n.t("窗口(&W)"))
        
        # 最小化
        minimize_action = QAction(self.i18n.t("最小化(&M)"), self)
        minimize_action.setShortcut("Ctrl+M")
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)
        
        # 最大化/还原
        self.maximize_action = QAction(self.i18n.t("最大化(&X)"), self)
        self.maximize_action.setShortcut("Ctrl+Shift+M")
        self.maximize_action.triggered.connect(self.toggle_maximize)
        window_menu.addAction(self.maximize_action)
        
        window_menu.addSeparator()
        
        # 全屏
        fullscreen_action = QAction(self.i18n.t("全屏(&F)"), self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        window_menu.addAction(fullscreen_action)
        
        window_menu.addSeparator()
        
        # 关闭
        close_action = QAction(self.i18n.t("关闭(&C)"), self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self.close)
        window_menu.addAction(close_action)
        
        # 视图菜单
        view_menu = menubar.addMenu(self.i18n.t("视图(&V)"))
        
        # 缩放操作
        zoom_in_action = QAction(self.i18n.t("放大(&I)"), self)
        zoom_in_action.setShortcut("+")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction(self.i18n.t("缩小(&O)"), self)
        zoom_out_action.setShortcut("-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction(self.i18n.t("重置缩放(&R)"), self)
        reset_zoom_action.setShortcut("0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        fit_window_action = QAction(self.i18n.t("适应窗口(&F)"), self)
        fit_window_action.setShortcut("F")
        fit_window_action.triggered.connect(self.fit_to_window)
        view_menu.addAction(fit_window_action)
    
    def toggle_maximize(self):
        """切换最大化状态"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_action.setText(self.i18n.t("最大化(&X)"))
        else:
            self.showMaximized()
            self.maximize_action.setText(self.i18n.t("还原(&R)"))
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # 缩放快捷键
        QShortcut(QKeySequence("+"), self, self.zoom_in)
        QShortcut(QKeySequence("-"), self, self.zoom_out)
        QShortcut(QKeySequence("0"), self, self.reset_zoom)
        QShortcut(QKeySequence("F"), self, self.fit_to_window)
        
        # 全屏快捷键
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, self.exit_fullscreen)
        
        # 收藏快捷键
        QShortcut(QKeySequence("Ctrl+D"), self, self.toggle_favorite)
        
        # 下载快捷键
        QShortcut(QKeySequence("Ctrl+S"), self, self.download_image)

        # 旋转/镜像快捷键
        QShortcut(QKeySequence("Ctrl+Left"), self, self.rotate_left)
        QShortcut(QKeySequence("Ctrl+Right"), self, self.rotate_right)
        QShortcut(QKeySequence("Ctrl+H"), self, self.flip_horizontal)
        QShortcut(QKeySequence("Ctrl+V"), self, self.flip_vertical)

        # 导航与播放快捷键（支持视频和图片）
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.handle_left_key)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.handle_right_key)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.handle_space_key)
        
        # 视频专用快捷键
        QShortcut(QKeySequence("M"), self, self.handle_mute_key)
        QShortcut(QKeySequence("Up"), self, self.handle_volume_up)
        QShortcut(QKeySequence("Down"), self, self.handle_volume_down)
    
    def update_info_text(self):
        """更新信息文本"""
        info_lines = []
        info_lines.append(f"<b>{self.i18n.t('ID')}</b>: {self.image_data.get('id', 'N/A')}")
        
        if 'width' in self.image_data and 'height' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('尺寸')}</b>: {self.image_data['width']} × {self.image_data['height']}")
        
        if 'file_size' in self.image_data:
            size_mb = self.image_data['file_size'] / (1024 * 1024)
            info_lines.append(f"<b>{self.i18n.t('文件大小')}</b>: {size_mb:.2f} MB")
        
        if 'file_ext' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('格式')}</b>: {self.image_data['file_ext'].upper()}")
        
        if 'rating' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('评级')}</b>: {self.image_data['rating']}")
        
        if 'score' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('评分')}</b>: {self.image_data['score']}")
        
        if 'created_at' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('创建时间')}</b>: {self.image_data['created_at']}")

        if 'uploader' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('上传者')}</b>: {self.image_data.get('uploader')}")
        
        if 'site' in self.image_data:
            info_lines.append(f"<b>{self.i18n.t('站点')}</b>: {self.image_data.get('site')}")
        
        # 优先显示帖子链接，其次来源链接
        post_url = self.image_data.get('post_url')
        source_url = self.image_data.get('source')
        if post_url:
            info_lines.append(f"<b>{self.i18n.t('帖子链接')}</b>: <a href=\"{post_url}\">{post_url}</a>")
        elif source_url:
            info_lines.append(f"<b>{self.i18n.t('来源')}</b>: <a href=\"{source_url}\">{source_url}</a>")
        
        self.info_text.setHtml('<br/>'.join(info_lines))
    
    def update_tags_text(self):
        """更新标签文本"""
        # 优先使用分组标签详情
        tag_details = self.image_data.get('tag_details')
        if isinstance(tag_details, dict) and tag_details:
            order = ['artist', 'character', 'copyright', 'general', 'meta']
            html_lines = []
            for key in order:
                names = tag_details.get(key, [])
                if names:
                    title = {
                        'artist': self.i18n.t('作者'),
                        'character': self.i18n.t('角色'),
                        'copyright': self.i18n.t('原作'),
                        'general': self.i18n.t('通用'),
                        'meta': self.i18n.t('元数据')
                    }.get(key, key.title())
                    html_lines.append(f"<b>{title}</b>:")
                    # 每个标签渲染为可点击的链接，使用百分号编码并放入路径，避免符号问题
                    from urllib.parse import quote
                    # 使用段落和行内块级元素以实现自动换行
                    spans = ', '.join(f"""<a href="tag:///{quote(name, safe='')}">{name}</a>""" for name in names)
                    html_lines.append(f'<p style="line-height: 2.2;">{spans}</p>')
            html = '<br/>'.join(html_lines).strip()
            self.tags_text.setHtml(html if html else self.i18n.t("无标签信息"))
            return
        
        # 回退到旧的标签列表
        tags = self.image_data.get('tags', [])
        if tags:
            if isinstance(tags[0], dict):
                tag_groups = {}
                for tag in tags:
                    tag_type = tag.get('type', 'general')
                    tag_groups.setdefault(tag_type, []).append(tag.get('name', ''))
                html_lines = []
                for tag_type, names in tag_groups.items():
                    html_lines.append(f"<b>{tag_type.title()}</b>:")
                    spans = ', '.join(f"""<a href="tag:///{quote(n, safe='')}">{n}</a>""" for n in names if n)
                    html_lines.append(f'<p style="line-height: 2.2;">{spans}</p>')
                self.tags_text.setHtml('<br/>'.join(html_lines).strip())
            else:
                from urllib.parse import quote
                spans = ', '.join(f"""<a href="tag:///{quote(n, safe='')}">{n}</a>""" for n in tags)
                self.tags_text.setHtml(f'<p style="line-height: 2.2;">{spans}</p>')
        else:
            self.tags_text.setHtml(self.i18n.t("无标签信息"))
    
    def load_image(self):
        """加载图片"""
        # 先取消任何仍在进行的下载线程，避免重复和销毁时崩溃
        if getattr(self, 'download_thread', None) and self.download_thread.isRunning():
            try:
                self.download_thread.terminate()
                self.download_thread.wait()
            except Exception:
                pass
            self.download_thread = None

        # 若为 Konachan/Yande.re（Moebooru）且缺少 file_url，则自动解析帖子查看页
        site = (self.image_data.get('site') or '').lower()
        file_url = self.image_data.get('file_url') or self.image_data.get('large_file_url')
        post_url = self.image_data.get('post_url')

        # 若为 Konachan/Yande.re（Moebooru）且缺少 file_url，则自动解析帖子查看页
        if site in ('konachan', 'yandere') and (not file_url) and post_url:
            if getattr(self, 'resolve_thread', None) and self.resolve_thread.isRunning():
                try:
                    self.resolve_thread.terminate()
                    self.resolve_thread.wait()
                except Exception:
                    pass
                self.resolve_thread = None

            try:
                self.progress_bar.setRange(0, 0)
                self.progress_bar.show()
            except Exception:
                pass
            try:
                self.image_label.setText(self.i18n.t("正在解析原图链接..."))
            except Exception:
                pass

            self.resolve_thread = MoebooruResolveFileUrlThread(post_url)
            self.resolve_thread.resolved.connect(self._on_moebooru_resolved)
            self.resolve_thread.failed.connect(self._on_moebooru_failed)
            self.resolve_thread.start()
            return

        # 检查是否为视频
        file_ext = self.image_data.get('file_ext', '').lower()
        # 仅将常见视频格式作为视频处理，GIF 仍按静态图处理
        if file_ext in ['mp4', 'webm']:
            self.load_video()
        else:
            self.load_static_image()

    def load_static_image(self):
        """加载静态图片"""
        # 取消任何仍在进行的下载线程
        if getattr(self, 'download_thread', None) and self.download_thread.isRunning():
            try:
                self.download_thread.terminate()
                self.download_thread.wait()
            except Exception:
                pass
            self.download_thread = None
        self.progress_bar.hide()

        # 若有正在播放的 GIF，先停止并清理
        if self.gif_player:
            self.gif_player.stop()

        # 如果之前正在播放视频，先停止并切回图片视图
        if self.media_player:
            try:
                self.media_player.stop()
            except Exception:
                pass
            # 释放旧的播放器资源
            try:
                self.media_player.deleteLater()
            except Exception:
                pass
            self.media_player = None
        
        # 隐藏视频控制组件
        self.video_controls.hide()
        
        # 切换到图片视图
        try:
            self.viewer_stack.setCurrentWidget(self.image_label)
        except Exception:
            pass

        # 根据是否使用原图选择URL
        file_url = self.image_data.get('file_url')
        large_url = self.image_data.get('large_file_url')
        image_url = (file_url if self.use_original else large_url) or file_url or large_url
        if not image_url:
            self.image_label.setText(self.i18n.t("无法获取图片URL"))
            return
        
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        self.download_thread = ImageDownloadThread(image_url)
        self.download_thread.download_finished.connect(self.on_image_downloaded)
        self.download_thread.download_failed.connect(self.on_download_failed)
        self.download_thread.download_progress.connect(self.on_download_progress)
        self.download_thread.start()


    @pyqtSlot(dict)
    def _on_moebooru_resolved(self, info: dict):
        """Konachan/Yande.re 原图解析成功：更新数据并重新加载"""
        try:
            self.progress_bar.hide()
        except Exception:
            pass
        url = info.get('file_url') or info.get('url')
        if not url:
            self._on_moebooru_failed("解析结果为空")
            return
        try:
            self.image_data['file_url'] = url
            ext = info.get('ext') or url.split('?')[0].split('.')[-1].lower()
            self.image_data['file_ext'] = ext
            self.image_label.setText("")
        except Exception:
            pass
        self.load_image()

    @pyqtSlot(str)
    def _on_moebooru_failed(self, error: str):
        """Konachan/Yande.re 原图解析失败：提示错误"""
        try:
            self.progress_bar.hide()
        except Exception:
            pass
        try:
            msg = self.i18n.t("解析原图链接失败: {error}").format(error=error)
        except Exception:
            msg = f"解析原图链接失败: {error}"
        try:
            self.image_label.setText(msg)
        except Exception:
            pass

    def load_video(self):
        """加载视频"""
        # 取消任何仍在进行的下载线程
        if getattr(self, 'download_thread', None) and self.download_thread.isRunning():
            try:
                self.download_thread.terminate()
                self.download_thread.wait()
            except Exception:
                pass
            self.download_thread = None
        self.progress_bar.hide()

        # 若有正在播放的 GIF，先停止并清理
        if self.gif_player:
            self.gif_player.stop()

        video_url = self.image_data.get('file_url')
        if not video_url:
            self.image_label.setText(self.i18n.t("无法获取视频URL"))
            return

        # 若已有播放器实例，先停止并清理
        if self.media_player:
            try:
                self.media_player.stop()
            except Exception:
                pass
            try:
                self.media_player.deleteLater()
            except Exception:
                pass
            self.media_player = None

        # 切换到视频播放器
        try:
            self.viewer_stack.setCurrentWidget(self.video_container)
        except Exception:
            pass
        
        # 初始化媒体播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # 连接视频控制组件
        self.video_controls.set_media_player(self.media_player)
        self.setup_video_controls()
        
        # 显示视频控制组件
        self.video_controls.show()
        
        # 设置媒体源并播放
        self.media_player.setSource(QUrl(video_url))
        self.media_player.play()
    
    def setup_video_controls(self):
        """设置视频控制组件的信号连接"""
        if not self.media_player:
            return
            
        # 连接视频控制信号
        self.video_controls.play_pause_clicked.connect(self._on_video_play_pause)
        self.video_controls.stop_clicked.connect(self._on_video_stop)
        self.video_controls.position_changed.connect(self._on_video_position_changed)
        self.video_controls.volume_changed.connect(self._on_video_volume_changed)
        self.video_controls.mute_toggled.connect(self._on_video_mute_toggled)
        self.video_controls.fullscreen_clicked.connect(self.toggle_fullscreen)
    
    def _on_video_play_pause(self):
        """视频播放/暂停"""
        if not self.media_player:
            return
            
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def _on_video_stop(self):
        """视频停止"""
        if self.media_player:
            self.media_player.stop()
    
    def _on_video_position_changed(self, position):
        """视频位置改变"""
        if self.media_player:
            self.media_player.setPosition(position)
    
    def _on_video_volume_changed(self, volume):
        """音量改变"""
        if self.audio_output:
            self.audio_output.setVolume(volume)
    
    def _on_video_mute_toggled(self, muted):
        """静音切换"""
        if self.audio_output:
            self.audio_output.setMuted(muted)
    
    @pyqtSlot(bytes)
    def on_image_downloaded(self, data: bytes):
        """图片下载完成"""
        self.progress_bar.hide()
        
        # 检查是否为GIF文件
        ext = (self.image_data.get('file_ext') or '').lower()
        if ext == 'gif':
            try:
                # 确保切换到图片视图
                self.viewer_stack.setCurrentWidget(self.image_label)
                self.image_label.show()
                self.video_widget.hide()
                
                # 使用新的GIF播放器
                if self.gif_player.load_gif(data):
                    print(f"[GIF] 成功加载GIF，帧数: {self.gif_player.get_frame_count()}")
                    
                    # 显示第一帧
                    first_frame = self.gif_player.get_current_frame()
                    if first_frame:
                        self.image_label.set_pixmap(first_frame)
                        self.fit_to_window()
                        self.sync_zoom_ui()
                    
                    # 如果是动画GIF，开始播放
                    if self.gif_player.is_animated():
                        self.gif_player.play()
                    
                    return
                else:
                    print("[GIF] GIF加载失败，回退到静态图片处理")
                    
            except Exception as e:
                print(f"[GIF] GIF处理异常: {e}")
        
        # 普通静态图片处理
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # 确保切换到图片视图
            self.viewer_stack.setCurrentWidget(self.image_label)
            self.image_label.show()
            self.video_widget.hide()
            
            self.image_label.set_pixmap(pixmap)
            self.fit_to_window()
            self.sync_zoom_ui()
        else:
            self.image_label.setText(self.i18n.t("无法解析图片数据"))
    
    def _on_gif_frame_changed(self, pixmap: QPixmap):
        """GIF帧变化处理"""
        if pixmap and not pixmap.isNull():
            # 更新当前帧，但保持缩放和位置
            if hasattr(self.image_label, 'pixmap_item') and self.image_label.pixmap_item:
                self.image_label.pixmap_item.setPixmap(pixmap)
                # 更新场景矩形以防尺寸变化
                self.image_label.scene.setSceneRect(self.image_label.pixmap_item.sceneBoundingRect())
    
    def _on_gif_playback_finished(self):
        """GIF播放完成处理"""
        print("[GIF] 播放完成")
    
    @pyqtSlot(str)
    def on_download_failed(self, error: str):
        """下载失败"""
        self.progress_bar.hide()
        self.image_label.setText(self.i18n.t("加载失败: {error}").format(error=self.i18n.t(error)))
    
    @pyqtSlot(int, int)
    def on_download_progress(self, current: int, total: int):
        """下载进度"""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
    
    def zoom_in(self):
        """放大"""
        self.image_label.zoom_in()
        self.sync_zoom_ui()
    
    def zoom_out(self):
        """缩小"""
        self.image_label.zoom_out()
        self.sync_zoom_ui()
    
    def reset_zoom(self):
        """重置缩放"""
        self.image_label.reset_zoom()
        self.sync_zoom_ui()
    
    def fit_to_window(self):
        """适应窗口"""
        self.image_label.fit_to_window()
        self.sync_zoom_ui()

    def rotate_left(self):
        self.image_label.rotate_left()
        self.sync_zoom_ui()

    def rotate_right(self):
        self.image_label.rotate_right()
        self.sync_zoom_ui()

    def flip_horizontal(self):
        self.image_label.flip_horizontal()
        self.sync_zoom_ui()

    def flip_vertical(self):
        self.image_label.flip_vertical()
        self.sync_zoom_ui()
    
    def toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def exit_fullscreen(self):
        """退出全屏"""
        if self.isFullScreen():
            self.showNormal()
    
    def toggle_favorite(self):
        """切换收藏状态"""
        self.is_favorite = not self.is_favorite
        if self.is_favorite:
            self.favorite_btn.setText(self.i18n.t("♥ 已收藏"))
            self.favorite_btn.setStyleSheet("color: red;")
        else:
            self.favorite_btn.setText(self.i18n.t("♡ 添加收藏"))
            self.favorite_btn.setStyleSheet("")
        
        self.favorite_toggled.emit(self.image_data, self.is_favorite)
    
    def download_image(self):
        """下载图片"""
        self.download_requested.emit(self.image_data)
    
    def open_source_page(self):
        """打开原页面"""
        # 优先打开帖子链接
        url = self.image_data.get('post_url') or self.image_data.get('source')
        if url:
            import webbrowser
            webbrowser.open(url)

    # ============ 导航与播放相关 ============
    def show_image_by_index(self, index: int):
        """显示指定索引的图片并刷新界面"""
        if not self.images_list:
            return
        index = max(0, min(index, len(self.images_list) - 1))
        self.current_index = index
        self.image_data = self.images_list[self.current_index]
        # 更新窗口标题
        self.setWindowTitle(self.i18n.t("图片查看器"))
        # 每次切换重置缩放与旋转以避免形变叠加
        self.image_label.reset_zoom()
        self.image_label.rotation_degrees = 0
        self.image_label.flip_horizontal_flag = False
        self.image_label.flip_vertical_flag = False
        # 更新信息与标签
        self.update_info_text()
        self.update_tags_text()
        # 加载图像/视频
        self.load_image()

    def _adjust_buttons_width(self, buttons):
        """根据按钮文本设置最小宽度，提升多语言兼容性"""
        for btn in buttons:
            try:
                fm = QFontMetrics(btn.font())
                text_width = fm.horizontalAdvance(btn.text())
                btn.setMinimumWidth(text_width + 36)
            except Exception:
                pass

    def prev_image(self):
        """显示上一张"""
        if not self.images_list:
            return
        new_index = self.current_index - 1
        if new_index < 0:
            new_index = 0
        self.show_image_by_index(new_index)

    def next_image(self):
        """显示下一张"""
        if not self.images_list:
            return
        new_index = self.current_index + 1
        if new_index >= len(self.images_list):
            new_index = len(self.images_list) - 1
        self.show_image_by_index(new_index)

    # 幻灯片播放功能已移除

    def handle_left_key(self):
        """处理左箭头键：视频时后退10秒，图片时上一张"""
        if hasattr(self, 'media_player') and self.media_player and self.viewer_stack.currentWidget() == self.video_container:
            # 视频模式：后退10秒
            current_pos = self.media_player.position()
            new_pos = max(0, current_pos - 10000)  # 10秒 = 10000毫秒
            self.media_player.setPosition(new_pos)
        else:
            # 图片模式：上一张
            self.prev_image()

    def handle_right_key(self):
        """处理右箭头键：视频时前进10秒，图片时下一张"""
        if hasattr(self, 'media_player') and self.media_player and self.viewer_stack.currentWidget() == self.video_container:
            # 视频模式：前进10秒
            current_pos = self.media_player.position()
            duration = self.media_player.duration()
            new_pos = min(duration, current_pos + 10000)  # 10秒 = 10000毫秒
            self.media_player.setPosition(new_pos)
        else:
            # 图片模式：下一张
            self.next_image()

    def handle_space_key(self):
        """处理空格键：仅在视频模式下播放/暂停，图片模式不处理"""
        if hasattr(self, 'media_player') and self.media_player and self.viewer_stack.currentWidget() == self.video_container:
            # 视频模式：播放/暂停
            if hasattr(self, 'video_controls'):
                self.video_controls.toggle_play_pause()
        else:
            # 图片模式：不处理空格键（已移除幻灯片播放）
            return

    def handle_mute_key(self):
        """处理M键：静音/取消静音"""
        if hasattr(self, 'media_player') and self.media_player and self.viewer_stack.currentWidget() == self.video_container:
            if hasattr(self, 'video_controls'):
                self.video_controls.toggle_mute()

    def handle_volume_up(self):
        """处理上箭头键：音量增加"""
        if hasattr(self, 'media_player') and self.media_player and self.viewer_stack.currentWidget() == self.video_container:
            if hasattr(self, 'video_controls'):
                current_volume = self.video_controls.volume_slider.value()
                new_volume = min(100, current_volume + 10)
                self.video_controls.volume_slider.setValue(new_volume)

    def handle_volume_down(self):
        """处理下箭头键：音量减少"""
        if hasattr(self, 'media_player') and self.media_player and self.viewer_stack.currentWidget() == self.video_container:
            if hasattr(self, 'video_controls'):
                current_volume = self.video_controls.volume_slider.value()
                new_volume = max(0, current_volume - 10)
                self.video_controls.volume_slider.setValue(new_volume)

    def sync_zoom_ui(self):
        """同步缩放UI显示"""
        # 百分比以屏幕物理像素为基准：scale_factor * DPR
        try:
            dpr = self.image_label.get_dpr()
        except Exception:
            dpr = 1.0
        percent = int(self.image_label.scale_factor * max(dpr, 1.0) * 100)
        self.zoom_label.setText(f"{percent}%")

    def on_tag_anchor_clicked(self, url: QUrl):
        """标签点击事件，发出标签信号"""
        if url.scheme() == 'tag':
            # 从路径读取并进行百分号解码，支持含符号标签
            try:
                from urllib.parse import unquote
                path = url.path() or ''
                tag = unquote(path.lstrip('/'))
                if not tag:
                    s = url.toString()
                    s = s.replace('tag:///', '').replace('tag://', '').replace('tag:', '')
                    tag = unquote(s)
            except Exception:
                tag = url.toString().replace('tag://', '')
            self.tag_clicked.emit(tag)

    def copy_post_link(self):
        from PyQt6.QtWidgets import QApplication
        post_url = self.image_data.get('post_url')
        if post_url:
            QApplication.clipboard().setText(post_url)
        
    def copy_image_link(self):
        from PyQt6.QtWidgets import QApplication
        url = self.image_data.get('file_url') or self.image_data.get('large_file_url')
        if url:
            QApplication.clipboard().setText(url)
        
    def copy_source_link(self):
        from PyQt6.QtWidgets import QApplication
        source = self.image_data.get('source')
        if source:
            QApplication.clipboard().setText(source)

    def copy_tags_text(self):
        from PyQt6.QtWidgets import QApplication
        names = []
        try:
            tag_details = self.image_data.get('tag_details')
            if isinstance(tag_details, dict) and tag_details:
                order = ['artist', 'character', 'copyright', 'general', 'meta']
                for key in order:
                    key_names = tag_details.get(key, [])
                    if isinstance(key_names, list):
                        names.extend([n for n in key_names if n])
            else:
                tags = self.image_data.get('tags', [])
                if isinstance(tags, list):
                    names = [n for n in tags if n]
                elif isinstance(tags, str):
                    names = [n for n in tags.split() if n]
        except Exception:
            pass
        if names:
            QApplication.clipboard().setText(', '.join(names))

    def toggle_original(self):
        """切换原图/大图并重新加载"""
        self.use_original = not self.use_original
        self.toggle_original_btn.setText(self.i18n.t("切换为原图") if not self.use_original else self.i18n.t("切换为大图"))
        # 重载图片
        self.load_static_image()
    
    def mouseDoubleClickEvent(self, event):
        """双击事件：切换全屏"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_fullscreen()
        super().mouseDoubleClickEvent(event)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        
        if self.media_player:
            self.media_player.stop()
        # 停止并清理 GIF 播放
        if self.gif_player:
            self.gif_player.stop()
        
        # 从父窗口的图片查看器列表中移除自己
        if self.parent() and hasattr(self.parent(), 'image_viewers'):
            try:
                if self in self.parent().image_viewers:
                    self.parent().image_viewers.remove(self)
            except (ValueError, AttributeError):
                pass
        
        super().closeEvent(event)
