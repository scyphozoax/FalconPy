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
        self.font_size_spin.setValue(int(self.config.get('appearance.font', 'Segoe UI,10').split(',')[1]))
        self.font_index_to_family = {}
        selected_idx = -1
        current_font = self.config.get('appearance.font', 'Segoe UI,10')
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
            fam = self.font_index_to_family.get(idx, 'Segoe UI')
            size = int(self.font_size_spin.value())
            self.config.set('appearance.font', f"{fam},{size}")
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
        self.setWindowTitle(self.i18n.t("设置"))
        self.setFixedSize(600, 500)
        self.setModal(True)
        
        self._main_layout = QVBoxLayout(self)
        
        title_label = QLabel(self.i18n.t("应用程序设置"))
        title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_layout.addWidget(title_label)
        
        lang_group = QGroupBox(self.i18n.t("语言"))
        lang_form = QFormLayout(lang_group)
        self.language_box = QComboBox()
        langs = I18n.supported_languages()
        for code, name in langs.items():
            self.language_box.addItem(self.i18n.t(name), code)
        current_lang = self.config.get('appearance.language', 'zh_CN')
        idx = max(0, self.language_box.findData(current_lang))
        self.language_box.setCurrentIndex(idx)
        lang_form.addRow(self.i18n.t("语言"), self.language_box)
        self._main_layout.addWidget(lang_group)
        
        self.download_tab = DownloadTab(self.config, self.i18n)
        self._main_layout.addWidget(self.download_tab)
        
        self.favorites_tab = FavoritesTab(self.config, self.i18n)
        self._main_layout.addWidget(self.favorites_tab)
        
        button_layout = QHBoxLayout()
        
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
        self.download_tab.save_settings()
        self.favorites_tab.save_settings()
        self.config.save_config()
        self.settings_changed.emit()
        QMessageBox.information(self, self.i18n.t("设置"), self.i18n.t("设置已保存，部分设置需要重启应用程序后生效。"))
        self.accept()

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
        parent = self.download_tab.parent()
        self._main_layout.removeWidget(self.download_tab)
        self.download_tab.deleteLater()
        self.download_tab = DownloadTab(self.config, self.i18n)
        self._main_layout.insertWidget(self._main_layout.count()-1, self.download_tab)
        parent = self.favorites_tab.parent()
        self._main_layout.removeWidget(self.favorites_tab)
        self.favorites_tab.deleteLater()
        self.favorites_tab = FavoritesTab(self.config, self.i18n)
        self._main_layout.insertWidget(self._main_layout.count()-1, self.favorites_tab)
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
            root = Path(__file__).resolve().parents[3]
            script = str(root / "main.py")
            QProcess.startDetached(sys.executable, [script], str(root))
            self.accept()
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t("重启失败"), self.i18n.t("无法启动新进程：") + str(e))
