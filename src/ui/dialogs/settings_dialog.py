# -*- coding: utf-8 -*-
"""
设置对话框
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QLabel, QLineEdit, QPushButton, QComboBox, 
                            QCheckBox, QSpinBox, QSlider, QTabWidget, QWidget,
                            QMessageBox, QGroupBox, QRadioButton, QButtonGroup,
                            QFileDialog, QColorDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QProcess
from PyQt6.QtGui import QFont, QColor, QPalette
from ...core.database import DatabaseManager
from ...core.i18n import I18n
from ...core.config import Config


class FavoritesTab(QWidget):
    """收藏默认设置标签页：每站点独立的默认收藏位置"""
    def __init__(self, config, i18n: I18n | None = None):
        super().__init__()
        self.config = config
        self.i18n = i18n or I18n(config.get('appearance.language', 'zh_CN'))
        self.db = DatabaseManager()
        self.site_keys = [
            ("Danbooru", "danbooru"),
            ("Konachan", "konachan"),
            ("Yande.re", "yandere")
        ]
        self.controls = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        group = QGroupBox(self.i18n.t("默认收藏位置（每站点独立）"))
        form = QFormLayout(group)
        form.setContentsMargins(12, 10, 12, 10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(12)
        # 预取本地收藏夹列表
        folders = self.db.get_favorites()
        for title, key in self.site_keys:
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            rb_local = QRadioButton(self.i18n.t("本地"))
            rb_online = QRadioButton(self.i18n.t("在线"))
            folder_box = QComboBox()
            for f in folders:
                folder_box.addItem(f.get('name', f"收藏夹{f.get('id')}"), f.get('id'))
            # 载入配置
            dest = self.config.get(f"sites.{key}.favorite_default.destination", 'local')
            fid = self.config.get(f"sites.{key}.favorite_default.folder_id", None)
            if dest == 'online':
                rb_online.setChecked(True)
                folder_box.setEnabled(False)
            else:
                rb_local.setChecked(True)
                folder_box.setEnabled(True)
                if fid is not None:
                    idx = max(0, folder_box.findData(fid))
                    folder_box.setCurrentIndex(idx)
            # 联动
            rb_local.toggled.connect(lambda checked, fb=folder_box: fb.setEnabled(bool(checked)))
            row.addWidget(rb_local)
            row.addWidget(rb_online)
            row.addWidget(QLabel(self.i18n.t("本地收藏夹：")))
            row.addWidget(folder_box)
            form.addRow(title + ":", row_widget)
            self.controls[key] = {
                'rb_local': rb_local,
                'rb_online': rb_online,
                'folder_box': folder_box
            }
        layout.addWidget(group)
        layout.addStretch(1)

    def save_settings(self):
        for key, ctrl in self.controls.items():
            dest = 'local' if ctrl['rb_local'].isChecked() else 'online'
            fid = ctrl['folder_box'].currentData() if dest == 'local' else None
            self.config.set(f"sites.{key}.favorite_default.destination", dest)
            self.config.set(f"sites.{key}.favorite_default.folder_id", fid)

class AppearanceTab(QWidget):
    """外观设置标签页"""
    
    def __init__(self, config, i18n: I18n | None = None):
        super().__init__()
        self.config = config
        self.i18n = i18n or I18n(config.get('appearance.language', 'zh_CN'))
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 主题设置
        theme_group = QGroupBox(self.i18n.t("主题设置"))
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_group = QButtonGroup()
        
        self.light_theme = QRadioButton(self.i18n.t("浅色主题"))
        self.dark_theme = QRadioButton(self.i18n.t("深色主题"))
        self.auto_theme = QRadioButton(self.i18n.t("跟随系统"))
        
        self.theme_group.addButton(self.light_theme, 0)
        self.theme_group.addButton(self.dark_theme, 1)
        self.theme_group.addButton(self.auto_theme, 2)
        
        theme_layout.addWidget(self.light_theme)
        theme_layout.addWidget(self.dark_theme)
        theme_layout.addWidget(self.auto_theme)
        
        # 设置当前主题
        current_theme = self.config.get('appearance.theme', 'dark')
        if current_theme == 'light':
            self.light_theme.setChecked(True)
        elif current_theme == 'dark':
            self.dark_theme.setChecked(True)
        else:
            self.auto_theme.setChecked(True)
        
        layout.addWidget(theme_group)
        
        
        # 界面设置
        ui_group = QGroupBox(self.i18n.t("界面设置"))
        ui_layout = QFormLayout(ui_group)
        
        # 缩放比例
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(80, 150)
        self.scale_slider.setValue(int(self.config.get('appearance.scale', 100)))
        self.scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.scale_slider.setTickInterval(10)
        
        self.scale_label = QLabel(f"{self.scale_slider.value()}%")
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_label.setText(f"{v}%")
        )
        
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_label)
        
        ui_layout.addRow(self.i18n.t("界面缩放:"), scale_layout)

        from pathlib import Path
        try:
            root = Path(__file__).resolve().parents[3]
        except Exception:
            from pathlib import Path as _P
            root = _P('.')
        fonts_dir = root / 'fonts'
        self.font_file_box = QComboBox()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        try:
            _fs = str(self.config.get('appearance.font', '') or '')
            _size = int(_fs.split(',')[1]) if ',' in _fs else 10
        except Exception:
            _size = 10
        self.font_size_spin.setValue(_size)
        self.font_index_to_family = {}
        selected_idx = -1
        current_font = self.config.get('appearance.font', '')
        cf = current_font.split(',')[0]
        try:
            from PyQt6.QtGui import QFontDatabase
            if fonts_dir.is_dir():
                files = list(sorted(fonts_dir.glob('*.ttf'))) + list(sorted(fonts_dir.glob('*.otf')))
                for i, p in enumerate(files):
                    try:
                        fid = QFontDatabase.addApplicationFont(str(p))
                        fams = QFontDatabase.applicationFontFamilies(fid) if fid != -1 else []
                        fam = fams[0] if fams else None
                        self.font_file_box.addItem(p.name, str(p))
                        if fam:
                            self.font_index_to_family[i] = fam
                            if fam == cf and selected_idx == -1:
                                selected_idx = i
                    except Exception:
                        self.font_file_box.addItem(p.name, str(p))
        except Exception:
            pass
        if selected_idx >= 0:
            self.font_file_box.setCurrentIndex(selected_idx)
        font_row = QWidget()
        font_row_layout = QHBoxLayout(font_row)
        font_row_layout.setContentsMargins(0, 0, 0, 0)
        font_row_layout.addWidget(self.font_file_box)
        font_row_layout.addWidget(QLabel(self.i18n.t("字号")))
        font_row_layout.addWidget(self.font_size_spin)
        ui_layout.addRow(self.i18n.t("字体"), font_row)

        # 语言设置
        self.language_box = QComboBox()
        langs = I18n.supported_languages()
        for code, name in langs.items():
            # 语言名称也做翻译
            self.language_box.addItem(self.i18n.t(name), code)
        current_lang = self.config.get('appearance.language', 'zh_CN')
        idx = max(0, self.language_box.findData(current_lang))
        self.language_box.setCurrentIndex(idx)
        ui_layout.addRow(self.i18n.t("语言"), self.language_box)
        
        # 显示设置
        self.show_thumbnails = QCheckBox(self.i18n.t("显示缩略图"))
        self.show_thumbnails.setChecked(self.config.get('appearance.show_thumbnails', True))
        
        self.show_image_info = QCheckBox(self.i18n.t("显示图片信息"))
        self.show_image_info.setChecked(self.config.get('appearance.show_image_info', True))
        
        self.animate_transitions = QCheckBox(self.i18n.t("启用动画效果"))
        self.animate_transitions.setChecked(self.config.get('appearance.animate_transitions', True))
        
        ui_layout.addRow(self.show_thumbnails)
        ui_layout.addRow(self.show_image_info)
        ui_layout.addRow(self.animate_transitions)
        
        layout.addWidget(ui_group)
        layout.addStretch()
    
    
    
    def save_settings(self):
        """保存设置"""
        # 保存主题设置
        if self.light_theme.isChecked():
            theme = 'light'
        elif self.dark_theme.isChecked():
            theme = 'dark'
        else:
            theme = 'auto'
        
        self.config.set('appearance.theme', theme)
        self.config.set('appearance.scale', self.scale_slider.value())
        self.config.set('appearance.show_thumbnails', self.show_thumbnails.isChecked())
        self.config.set('appearance.show_image_info', self.show_image_info.isChecked())
        self.config.set('appearance.animate_transitions', self.animate_transitions.isChecked())
        # 保存字体（族,字号）
        try:
            idx = self.font_file_box.currentIndex()
            fam = self.font_index_to_family.get(idx)
            size = int(self.font_size_spin.value())
            if fam:
                self.config.set('appearance.font', f"{fam},{size}")
            else:
                self.config.set('appearance.font', "")
        except Exception:
            pass
        # 保存语言
        try:
            self.config.set('appearance.language', self.language_box.currentData())
        except Exception:
            pass

class NetworkTab(QWidget):
    """网络设置标签页（已移除）"""
    pass

class DownloadTab(QWidget):
    """下载设置标签页"""
    
    def __init__(self, config, i18n: I18n | None = None):
        super().__init__()
        self.config = config
        self.i18n = i18n or I18n(config.get('appearance.language', 'zh_CN'))
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 下载路径设置
        path_group = QGroupBox(self.i18n.t("下载路径"))
        path_layout = QFormLayout(path_group)
        path_layout.setContentsMargins(12, 10, 12, 10)
        path_layout.setVerticalSpacing(10)
        path_layout.setHorizontalSpacing(12)
        
        self.download_path = QLineEdit()
        self.download_path.setText(self.config.get('download.path', './downloads'))
        
        browse_button = QPushButton(self.i18n.t("浏览..."))
        browse_button.clicked.connect(self.browse_download_path)
        
        path_widget = QWidget()
        path_widget_layout = QHBoxLayout(path_widget)
        path_widget_layout.setContentsMargins(0, 0, 0, 0)
        path_widget_layout.addWidget(self.download_path)
        path_widget_layout.addWidget(browse_button)
        
        path_layout.addRow(self.i18n.t("下载目录:"), path_widget)
        
        # 文件命名
        self.auto_rename = QCheckBox(self.i18n.t("自动重命名重复文件"))
        self.auto_rename.setChecked(self.config.get('download.auto_rename', True))
        
        self.create_subfolders = QCheckBox(self.i18n.t("按网站创建子文件夹"))
        self.create_subfolders.setChecked(self.config.get('download.create_subfolders', True))
        
        path_layout.addRow(self.auto_rename)
        path_layout.addRow(self.create_subfolders)
        
        layout.addWidget(path_group)
        
        # 下载选项
        options_group = QGroupBox(self.i18n.t("下载选项"))
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(12, 10, 12, 10)
        options_layout.setVerticalSpacing(10)
        options_layout.setHorizontalSpacing(12)
        
        self.download_original = QCheckBox(self.i18n.t("下载原图（如果可用）"))
        self.download_original.setChecked(self.config.get('download.download_original', True))
        
        self.save_metadata = QCheckBox(self.i18n.t("保存图片元数据"))
        self.save_metadata.setChecked(self.config.get('download.save_metadata', False))
        
        self.max_file_size = QSpinBox()
        self.max_file_size.setRange(1, 1000)
        self.max_file_size.setValue(self.config.get('download.max_file_size', 50))
        self.max_file_size.setSuffix(" MB")
        
        options_layout.addRow(self.download_original)
        options_layout.addRow(self.save_metadata)
        options_layout.addRow(self.i18n.t("最大文件大小:"), self.max_file_size)
        
        layout.addWidget(options_group)
        layout.addStretch()
    
    def browse_download_path(self):
        """浏览下载路径"""
        path = QFileDialog.getExistingDirectory(
            self, "选择下载目录", self.download_path.text()
        )
        if path:
            self.download_path.setText(path)
    
    def save_settings(self):
        """保存设置"""
        self.config.set('download.path', self.download_path.text())
        self.config.set('download.auto_rename', self.auto_rename.isChecked())
        self.config.set('download.create_subfolders', self.create_subfolders.isChecked())
        self.config.set('download.download_original', self.download_original.isChecked())
        self.config.set('download.save_metadata', self.save_metadata.isChecked())
        self.config.set('download.max_file_size', self.max_file_size.value())

class SettingsDialog(QDialog):
    """设置对话框"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        try:
            lang = self.config.get('appearance.language', 'zh_CN')
        except Exception:
            lang = 'zh_CN'
        self.i18n = I18n(lang)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("")
        from PyQt6.QtWidgets import QApplication
        try:
            parent_w = self.parent().width() if self.parent() else None
        except Exception:
            parent_w = None
        screen_w = QApplication.primaryScreen().availableGeometry().width()
        max_w = int((parent_w or int(screen_w * 0.6)) * 1.0)
        self.setMinimumWidth(520)
        try:
            self.setMaximumWidth(max_w)
        except Exception:
            pass
        self.resize(min(max_w, 600), 520)
        self.setModal(True)
        
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(12, 10, 12, 12)
        self._main_layout.setSpacing(10)
        
        
        
        # 内容滚动容器
        from PyQt6.QtWidgets import QScrollArea, QFrame
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)

        lang_group = QGroupBox(self.i18n.t("语言"))
        lang_form = QFormLayout(lang_group)
        lang_form.setContentsMargins(12, 10, 12, 10)
        lang_form.setVerticalSpacing(10)
        lang_form.setHorizontalSpacing(12)
        self.language_box = QComboBox()
        langs = I18n.supported_languages()
        for code, name in langs.items():
            self.language_box.addItem(self.i18n.t(name), code)
        current_lang = self.config.get('appearance.language', 'zh_CN')
        idx = max(0, self.language_box.findData(current_lang))
        self.language_box.setCurrentIndex(idx)
        lang_form.addRow(self.i18n.t("语言"), self.language_box)
        self._content_layout.addWidget(lang_group)

        ui_group = QGroupBox(self.i18n.t("界面设置"))
        ui_form = QFormLayout(ui_group)
        ui_form.setContentsMargins(12, 10, 12, 10)
        ui_form.setVerticalSpacing(10)
        ui_form.setHorizontalSpacing(12)
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(60, 150)
        try:
            self.scale_spin.setValue(int(self.config.get('appearance.scale_base', 70) or 70))
        except Exception:
            self.scale_spin.setValue(70)
        self.scale_spin.setSuffix(" %")
        ui_form.addRow(self.i18n.t("默认缩放"), self.scale_spin)
        self._content_layout.addWidget(ui_group)
        cf_group = QGroupBox(self.i18n.t("内容过滤"))
        cf_form = QFormLayout(cf_group)
        cf_form.setContentsMargins(12, 10, 12, 10)
        cf_form.setVerticalSpacing(10)
        cf_form.setHorizontalSpacing(12)
        self.cf_btn_group = QButtonGroup()
        self.cf_off = QRadioButton(self.i18n.t("关闭"))
        self.cf_hide = QRadioButton(self.i18n.t("隐藏E评级图片"))
        self.cf_blur = QRadioButton(self.i18n.t("模糊E评级缩略图"))
        self.cf_btn_group.addButton(self.cf_off, 0)
        self.cf_btn_group.addButton(self.cf_hide, 1)
        self.cf_btn_group.addButton(self.cf_blur, 2)
        mode = str(self.config.get('appearance.e_rating_filter', 'off') or 'off')
        if mode == 'hide':
            self.cf_hide.setChecked(True)
        elif mode == 'blur':
            self.cf_blur.setChecked(True)
        else:
            self.cf_off.setChecked(True)
        cf_form.addRow(self.cf_off)
        cf_form.addRow(self.cf_hide)
        cf_form.addRow(self.cf_blur)
        self._content_layout.addWidget(cf_group)
        try:
            self._cf_warn_ready = False
            def _on_off():
                if getattr(self, '_cf_warn_ready', False) and self.cf_off.isChecked():
                    QMessageBox.warning(self, self.i18n.t("成人内容警告"), self.i18n.t("关闭过滤将显示成人内容（E评级图片），可能不适合公开环境。"))
            def _on_blur():
                if getattr(self, '_cf_warn_ready', False) and self.cf_blur.isChecked():
                    QMessageBox.warning(self, self.i18n.t("成人内容警告"), self.i18n.t("将显示成人内容的缩略图（模糊处理）。注意：某些图片可能评级设置不正确导致无法使用模糊，请注意。"))
            self.cf_off.toggled.connect(lambda checked: (_on_off() if checked else None))
            self.cf_blur.toggled.connect(lambda checked: (_on_blur() if checked else None))
            self._cf_warn_ready = True
        except Exception:
            pass
        
        self.download_tab = DownloadTab(self.config, self.i18n)
        self._content_layout.addWidget(self.download_tab)

        self.update_tab = UpdateTab(self.config, self.i18n)
        self._content_layout.addWidget(self.update_tab)

        self.favorites_tab = FavoritesTab(self.config, self.i18n)
        self._content_layout.addWidget(self.favorites_tab)

        sd_group = QGroupBox(self.i18n.t("Stable Diffusion"))
        sd_form = QFormLayout(sd_group)
        sd_form.setContentsMargins(12, 10, 12, 10)
        sd_form.setVerticalSpacing(10)
        sd_form.setHorizontalSpacing(12)
        self.sd_url_edit = QLineEdit()
        try:
            self.sd_url_edit.setText(str(self.config.get('sd.url', 'http://127.0.0.1:7860') or 'http://127.0.0.1:7860'))
        except Exception:
            self.sd_url_edit.setText('http://127.0.0.1:7860')
        self.sd_browser_box = QComboBox()
        self.sd_browser_box.addItem('Edge', 'edge')
        self.sd_browser_box.addItem('Chrome', 'chrome')
        try:
            b = str(self.config.get('sd.browser', 'edge') or 'edge')
            idx = max(0, self.sd_browser_box.findData(b))
            self.sd_browser_box.setCurrentIndex(idx)
        except Exception:
            pass
        self.sd_port_spin = QSpinBox()
        self.sd_port_spin.setRange(1024, 65535)
        try:
            self.sd_port_spin.setValue(int(self.config.get('sd.cdp_port', 9222)))
        except Exception:
            self.sd_port_spin.setValue(9222)
        self.sd_attach_only = QCheckBox(self.i18n.t("仅附加现有浏览器，不自动启动"))
        self.sd_attach_only.setChecked(bool(self.config.get('sd.attach_only', False)))
        sd_form.addRow(self.i18n.t("WebUI 地址"), self.sd_url_edit)
        sd_form.addRow(self.i18n.t("浏览器"), self.sd_browser_box)
        sd_form.addRow(self.i18n.t("CDP 端口"), self.sd_port_spin)
        sd_form.addRow(self.sd_attach_only)
        self._content_layout.addWidget(sd_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        try:
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        except Exception:
            pass
        try:
            scroll.setFrameShape(QFrame.NoFrame)
        except Exception:
            pass
        scroll.setWidget(self._content)
        self._main_layout.addWidget(scroll)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        self.reset_button = QPushButton(self.i18n.t("重置默认"))
        self.reset_button.clicked.connect(self.reset_to_defaults)

        self.restart_button = QPushButton(self.i18n.t("重启应用"))
        self.restart_button.clicked.connect(self.restart_application)
        
        self.cancel_button = QPushButton(self.i18n.t("取消"))
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton(self.i18n.t("确定"))
        self.ok_button.clicked.connect(self.accept_settings)
        self.ok_button.setDefault(True)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.restart_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        self._main_layout.addLayout(button_layout)
    
    def accept_settings(self):
        self.config.set('appearance.language', self.language_box.currentData())
        try:
            # 将用户设置的值定义为新的默认：更新 scale_base，并把 scale 归一为 100
            new_base = int(self.scale_spin.value())
            self.config.set('appearance.scale_base', new_base)
            self.config.set('appearance.scale', 100)
        except Exception:
            pass
        self.download_tab.save_settings()
        self.update_tab.save_settings()
        self.favorites_tab.save_settings()
        try:
            self.config.set('sd.url', str(self.sd_url_edit.text()).strip())
            self.config.set('sd.browser', self.sd_browser_box.currentData())
            self.config.set('sd.cdp_port', int(self.sd_port_spin.value()))
            self.config.set('sd.attach_only', bool(self.sd_attach_only.isChecked()))
        except Exception:
            pass
        try:
            m = 'off'
            if self.cf_hide.isChecked():
                m = 'hide'
            elif self.cf_blur.isChecked():
                m = 'blur'
            self.config.set('appearance.e_rating_filter', m)
        except Exception:
            pass
        self.config.save_config()
        self.settings_changed.emit()
        QMessageBox.information(self, self.i18n.t("设置"), self.i18n.t("设置已保存并已应用。部分设置需要重启应用程序后生效。"))

    def reset_to_defaults(self):
        reply = QMessageBox.question(
            self, self.i18n.t("重置设置"), 
            self.i18n.t("确定要重置所有设置为默认值吗？"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.config.reset_to_defaults()
        current_lang = self.config.get('appearance.language', 'zh_CN')
        idx = max(0, self.language_box.findData(current_lang))
        self.language_box.setCurrentIndex(idx)
        try:
            self.config.set('appearance.scale_base', 70)
            self.config.set('appearance.scale', 100)
            self.scale_spin.setValue(70)
        except Exception:
            self.scale_spin.setValue(70)
        try:
            self.config.set('appearance.e_rating_filter', 'hide')
        except Exception:
            pass
        parent = self.download_tab.parent()
        self._content_layout.removeWidget(self.download_tab)
        self.download_tab.deleteLater()
        self.download_tab = DownloadTab(self.config, self.i18n)
        self._content_layout.addWidget(self.download_tab)
        parent = self.update_tab.parent()
        self._content_layout.removeWidget(self.update_tab)
        self.update_tab.deleteLater()
        self.update_tab = UpdateTab(self.config, self.i18n)
        self._content_layout.addWidget(self.update_tab)
        parent = self.favorites_tab.parent()
        self._content_layout.removeWidget(self.favorites_tab)
        self.favorites_tab.deleteLater()
        self.favorites_tab = FavoritesTab(self.config, self.i18n)
        self._content_layout.addWidget(self.favorites_tab)
        QMessageBox.information(self, self.i18n.t("重置完成"), self.i18n.t("所有设置已重置为默认值。"))

    def restart_application(self):
        reply = QMessageBox.question(
            self, self.i18n.t("重启应用"), 
            self.i18n.t("确定要重启应用吗？"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.config.set('appearance.language', self.language_box.currentData())
            self.download_tab.save_settings()
            self.favorites_tab.save_settings()
            self.config.save_config()
        except Exception:
            pass
        try:
            import sys
            from pathlib import Path
            if getattr(sys, "frozen", False):
                exe = Path(sys.executable)
                work = exe.parent
                QProcess.startDetached(str(exe), sys.argv[1:], str(work))
            else:
                root = Path(__file__).resolve().parents[3]
                script = str(root / "main.py")
                QProcess.startDetached(sys.executable, [script] + sys.argv[1:], str(root))
            self.accept()
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t("重启失败"), self.i18n.t("无法启动新进程：") + str(e))

class UpdateTab(QWidget):
    def __init__(self, config, i18n: I18n | None = None):
        super().__init__()
        self.config = config
        self.i18n = i18n or I18n(config.get('appearance.language', 'zh_CN'))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        group = QGroupBox(self.i18n.t("更新设置"))
        form = QFormLayout(group)

        self.source_box = QComboBox()
        self.source_box.addItem('JSON', 'json')
        self.source_box.addItem('GitHub', 'github')
        src = (self.config.get('updates.source', 'json') or 'json')
        idx = max(0, self.source_box.findData(src))
        self.source_box.setCurrentIndex(idx)

        self.enabled_box = QCheckBox(self.i18n.t("启用自动检查"))
        self.enabled_box.setChecked(bool(self.config.get('updates.enabled', True)))

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 1440)
        self.interval_spin.setValue(int(self.config.get('updates.interval_minutes', 60)))
        self.interval_spin.setSuffix(" min")

        self.feed_edit = QLineEdit()
        self.feed_edit.setText(self.config.get('updates.feed_url', ''))

        self.channel_edit = QLineEdit()
        self.channel_edit.setText(self.config.get('updates.channel', 'stable'))

        self.repo_edit = QLineEdit()
        self.repo_edit.setPlaceholderText('owner/repo')
        self.repo_edit.setText(self.config.get('updates.github_repo', ''))

        form.addRow(self.i18n.t("更新源类型:"), self.source_box)
        form.addRow(self.enabled_box)
        form.addRow(self.i18n.t("检查间隔:"), self.interval_spin)
        form.addRow(self.i18n.t("版本源地址:"), self.feed_edit)
        form.addRow(self.i18n.t("GitHub 仓库:"), self.repo_edit)
        form.addRow(self.i18n.t("更新通道:"), self.channel_edit)

        layout.addWidget(group)
        layout.addStretch()

    def save_settings(self):
        self.config.set('updates.source', self.source_box.currentData())
        self.config.set('updates.enabled', self.enabled_box.isChecked())
        self.config.set('updates.interval_minutes', int(self.interval_spin.value()))
        self.config.set('updates.feed_url', self.feed_edit.text().strip())
        self.config.set('updates.github_repo', self.repo_edit.text().strip())
        self.config.set('updates.channel', self.channel_edit.text().strip())
