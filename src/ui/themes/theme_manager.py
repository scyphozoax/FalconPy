# -*- coding: utf-8 -*-
"""
主题管理器
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QFontMetrics

class ThemeManager(QObject):
    """主题管理器"""
    
    theme_changed = pyqtSignal(str)  # 主题改变信号
    
    def __init__(self):
        super().__init__()
        self.current_theme = "win11"
        
        # 定义主题样式
        self.themes = {
            "light": self._get_light_theme(),
            "dark": self._get_dark_theme(),
            "blue": self._get_blue_theme(),
            "win11": self._get_win11_theme(),
            "win11_dark": self._get_win11_dark_theme()
        }
    
    def _get_light_theme(self):
        """浅色主题样式"""
        return """
            QMainWindow {
                background-color: #ffffff;
                color: #333333;
            }
            
            QMenuBar {
                background-color: #f8f9fa;
                color: #333333;
                border-bottom: 1px solid #dee2e6;
                padding: 2px;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 4px;
            }
            
            QMenuBar::item:selected {
                background-color: #e9ecef;
            }
            
            QMenu {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 4px;
            }
            
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background-color: #007bff;
                color: #ffffff;
            }
            
            QToolBar {
                background-color: #f8f9fa;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px;
                margin: 2px;
            }
            
            QToolButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            
            QToolButton:pressed {
                background-color: #dee2e6;
            }
            
            QStatusBar {
                background-color: #f8f9fa;
                color: #333333;
                border-top: 1px solid #dee2e6;
                padding: 4px;
            }
            
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QPushButton {
                background-color: #007bff;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #0056b3;
            }
            
            QPushButton:pressed {
                background-color: #004085;
            }
            
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
            
            QComboBox {
                background-color: #ffffff;
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 120px;
            }
            
            QComboBox:focus {
                border-color: #007bff;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzMzMzMzMyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            }
            
            /* Scrollbar - Light Theme (modern, rounded) */
            QScrollBar {
                background: transparent;
            }
            QScrollBar:vertical {
                width: 12px;
                margin: 2px;
            }
            QScrollBar:horizontal {
                height: 12px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #ced4da;
                border-radius: 6px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #adb5bd;
            }
            QScrollBar::handle:horizontal {
                background-color: #ced4da;
                border-radius: 6px;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #adb5bd;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical { background: transparent; }
            QScrollBar::sub-page:vertical { background: transparent; }
            QScrollBar::add-page:horizontal { background: transparent; }
            QScrollBar::sub-page:horizontal { background: transparent; }
            
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
            }
            
            QTabBar::tab {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
                color: #6c757d; /* 未选中更淡的文字颜色 */
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 2px solid #007bff; /* 选中下划线强调 */
                color: #212529; /* 更深文字，提升对比度 */
                font-weight: 600; /* 选中加粗 */
            }
            
            QTabBar::tab:hover {
                background-color: #e9ecef;
                color: #495057;
            }
            
            QDialog {
                background-color: #ffffff;
                color: #333333;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
                color: #333333;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #ffffff;
                color: #333333;
            }
        """
    
    def _get_dark_theme(self):
        """深色主题样式"""
        return """
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QMenuBar {
                background-color: #2d2d30;
                color: #ffffff;
                border-bottom: 1px solid #3e3e42;
                padding: 2px;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 4px;
            }
            
            QMenuBar::item:selected {
                background-color: #3e3e42;
            }
            
            QMenu {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                padding: 4px;
                color: #ffffff;
            }
            
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            
            QToolBar {
                background-color: #2d2d30;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px;
                margin: 2px;
                color: #ffffff;
            }
            
            QToolButton:hover {
                background-color: #3e3e42;
                border-color: #5a5a5e;
            }
            
            QToolButton:pressed {
                background-color: #4a4a4e;
            }
            
            QStatusBar {
                background-color: #2d2d30;
                color: #ffffff;
                border-top: 1px solid #3e3e42;
                padding: 4px;
            }
            
            QLineEdit {
                background-color: #3c3c3c;
                border: 2px solid #5a5a5e;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #ffffff;
            }
            
            QLineEdit:focus {
                border-color: #007acc;
                outline: none;
            }
            
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #005a9e;
            }
            
            QPushButton:pressed {
                background-color: #004578;
            }
            
            QPushButton:disabled {
                background-color: #5a5a5e;
                color: #8a8a8e;
            }
            
            QComboBox {
                background-color: #3c3c3c;
                border: 2px solid #5a5a5e;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 120px;
                color: #ffffff;
            }
            
            QComboBox:focus {
                border-color: #007acc;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            }
            
            /* Scrollbar - Dark Theme (modern, rounded) */
            QScrollBar {
                background: transparent;
            }
            QScrollBar:vertical {
                width: 12px;
                margin: 2px;
            }
            QScrollBar:horizontal {
                height: 12px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5e;
                border-radius: 6px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6a6a6e;
            }
            QScrollBar::handle:horizontal {
                background-color: #5a5a5e;
                border-radius: 6px;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #6a6a6e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical { background: transparent; }
            QScrollBar::sub-page:vertical { background: transparent; }
            QScrollBar::add-page:horizontal { background: transparent; }
            QScrollBar::sub-page:horizontal { background: transparent; }
            
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                border-radius: 6px;
                background-color: #1e1e1e;
            }
            
            QTabBar::tab {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
                color: #cfd2d6; /* 未选中更淡的文字颜色 */
            }
            
            QTabBar::tab:selected {
                background-color: #007acc; /* 选中使用强调色 */
                border-color: #005a9e;
                border-bottom: 2px solid #005a9e; /* 强化边框与下划线 */
                color: #ffffff;
                font-weight: 600;
            }
            
            QTabBar::tab:hover {
                background-color: #3e3e42;
                color: #e6e6e6;
            }
            
            QLabel {
                color: #ffffff;
            }
            
            QTreeWidget {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                color: #ffffff;
            }
            
            QTreeWidget::item {
                padding: 4px;
                border-radius: 4px;
            }
            
            QTreeWidget::item:selected {
                background-color: #007acc;
            }
            
            QTreeWidget::item:hover {
                background-color: #3e3e42;
            }
            
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e42;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #5a5a5e;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            
            QCheckBox::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }
            
            QRadioButton {
                color: #ffffff;
                spacing: 8px;
            }
            
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #5a5a5e;
                border-radius: 8px;
                background-color: #3c3c3c;
            }
            
            QRadioButton::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }
            
            QSpinBox {
                background-color: #3c3c3c;
                border: 2px solid #5a5a5e;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
            }
            
            QSpinBox:focus {
                border-color: #007acc;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #5a5a5e;
                height: 6px;
                background-color: #3c3c3c;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background-color: #007acc;
                border: 1px solid #005a9e;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            
            QSlider::handle:horizontal:hover {
                background-color: #0084d4;
            }
        """
    
    def _get_blue_theme(self):
        """蓝色主题样式"""
        return """
            QMainWindow {
                background-color: #f0f4f8;
                color: #2d3748;
            }
            
            QMenuBar {
                background-color: #4299e1;
                color: #ffffff;
                border-bottom: 1px solid #3182ce;
                padding: 2px;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 4px;
            }
            
            QMenuBar::item:selected {
                background-color: #3182ce;
            }
            
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 4px;
            }
            
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background-color: #4299e1;
                color: #ffffff;
            }
            
            QToolBar {
                background-color: #4299e1;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px;
                margin: 2px;
                color: #ffffff;
            }
            
            QToolButton:hover {
                background-color: #3182ce;
                border-color: #2c5aa0;
            }
            
            QToolButton:pressed {
                background-color: #2c5aa0;
            }
            
            QStatusBar {
                background-color: #edf2f7;
                color: #2d3748;
                border-top: 1px solid #e2e8f0;
                padding: 4px;
            }
            
            QPushButton {
                background-color: #4299e1;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #3182ce;
            }
            
            QPushButton:pressed {
                background-color: #2c5aa0;
            }
            
            /* Scrollbar - Blue Theme (modern, rounded) */
            QScrollBar {
                background: transparent;
            }
            QScrollBar:vertical {
                width: 12px;
                margin: 2px;
            }
            QScrollBar:horizontal {
                height: 12px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #8ec3f6;
                border-radius: 6px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #74b4ed;
            }
            QScrollBar::handle:horizontal {
                background-color: #8ec3f6;
                border-radius: 6px;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #74b4ed;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical { background: transparent; }
            QScrollBar::sub-page:vertical { background: transparent; }
            QScrollBar::add-page:horizontal { background: transparent; }
            QScrollBar::sub-page:horizontal { background: transparent; }
        """
    
    def _get_win11_theme(self):
        """Windows 11浅色主题样式"""
        return """
            /* Windows 11 风格 - 浅色主题 */
            QMainWindow {
                background-color: #f3f3f3;
                color: #202020;
            }
            
            /* 菜单栏 - 毛玻璃效果 */
            QMenuBar {
                background-color: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(20px);
                color: #202020;
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                padding: 4px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px;
            }
            
            QMenuBar::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
            }
            
            QMenuBar::item:pressed {
                background-color: rgba(0, 120, 212, 0.2);
            }
            
            /* 下拉菜单 */
            QMenu {
                background-color: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                padding: 8px;
                margin: 4px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            
            QMenu::item {
                padding: 10px 16px;
                border-radius: 6px;
                margin: 2px 0;
                min-width: 200px;
            }
            
            QMenu::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
            }
            
            QMenu::separator {
                height: 1px;
                background-color: rgba(0, 0, 0, 0.08);
                margin: 8px 0;
            }
            
            /* 工具栏 */
            QToolBar {
                background-color: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(20px);
                border: none;
                spacing: 8px;
                padding: 8px 12px;
                border-radius: 0;
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            }
            
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-color: rgba(0, 0, 0, 0.1);
            }
            
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.1);
                border-color: rgba(0, 0, 0, 0.15);
            }
            
            QToolButton:checked {
                background-color: rgba(0, 120, 212, 0.1);
                border-color: #0078d4;
                color: #0078d4;
            }
            
            /* 状态栏 */
            QStatusBar {
                background-color: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(20px);
                color: #202020;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                padding: 8px 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
            
            /* 输入框 - 圆角设计 */
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                color: #202020;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
            
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: #ffffff;
                outline: none;
            }
            
            QLineEdit:hover {
                border-color: rgba(0, 0, 0, 0.2);
            }
            
            /* 按钮 - 圆角设计 */
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                min-height: 36px;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #106ebe;
                transform: translateY(-1px);
            }
            
            QPushButton:pressed {
                background-color: #005a9e;
                transform: translateY(0);
            }
            
            QPushButton:disabled {
                background-color: rgba(0, 0, 0, 0.1);
                color: rgba(0, 0, 0, 0.3);
            }
            
            /* 次要按钮 */
            QPushButton[button-type="secondary"] {
                background-color: rgba(0, 0, 0, 0.05);
                color: #202020;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
            
            QPushButton[button-type="secondary"]:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            QPushButton[button-type="secondary"]:pressed {
                background-color: rgba(0, 0, 0, 0.15);
            }
            
            /* 下拉框 */
            QComboBox {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                min-width: 140px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                color: #202020;
            }
            
            QComboBox:focus {
                border-color: #0078d4;
                background-color: #ffffff;
            }
            
            QComboBox:hover {
                border-color: rgba(0, 0, 0, 0.2);
            }
            
            QComboBox::drop-down {
                border: none;
                width: 32px;
                border-radius: 0 6px 6px 0;
            }
            
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzY2NjY2NiIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
                width: 12px;
                height: 8px;
            }
            
            /* 滚动条 - Windows 11风格 */
            QScrollBar {
                background: transparent;
            }
            
            QScrollBar:vertical {
                width: 8px;
                margin: 4px 0;
                border-radius: 4px;
            }
            
            QScrollBar:horizontal {
                height: 8px;
                margin: 0 4px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
                min-height: 40px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
            
            QScrollBar::handle:horizontal {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
                min-width: 40px;
                margin: 2px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            
            /* 标签页 */
            QTabWidget::pane {
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
                margin: 0;
            }
            
            QTabBar::tab {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                margin: 4px 2px;
                color: #666666;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            
            QTabBar::tab:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
                font-weight: 600;
            }
            
            QTabBar::tab:hover {
                background-color: rgba(0, 0, 0, 0.05);
                color: #202020;
            }
            
            /* 对话框 */
            QDialog {
                background-color: #f3f3f3;
                color: #202020;
                border-radius: 12px;
            }
            
            /* 分组框 */
            QGroupBox {
                font-weight: 600;
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 16px;
                background-color: rgba(255, 255, 255, 0.5);
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 12px 0 12px;
                background-color: transparent;
                color: #202020;
                font-weight: 600;
            }
            
            /* 复选框 */
            QCheckBox {
                color: #202020;
                spacing: 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid rgba(0, 0, 0, 0.3);
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 0.9);
                margin-right: 8px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDRMNC41IDcuNUwxMSAxIiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            
            /* 单选框 */
            QRadioButton {
                color: #202020;
                spacing: 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid rgba(0, 0, 0, 0.3);
                border-radius: 7px;
                background-color: rgba(255, 255, 255, 0.9);
                margin-right: 8px;
            }
            
            QRadioButton::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            
            /* 数字输入框 */
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QSpinBox:focus {
                border-color: #0078d4;
                background-color: #ffffff;
            }
            
            /* 滑块 */
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 2px;
            }
            
            QSlider::handle:horizontal {
                background-color: #0078d4;
                border: none;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            
            QSlider::handle:horizontal:hover {
                background-color: #106ebe;
                transform: scale(1.1);
            }
            
            QSlider::handle:horizontal:pressed {
                background-color: #005a9e;
                transform: scale(0.95);
            }
            
            /* 标签 */
            QLabel {
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            /* 树形控件 */
            QTreeWidget {
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            QTreeWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px 0;
            }
            
            QTreeWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
            }
            
            QTreeWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            /* 列表控件 */
            QListWidget {
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            QListWidget::item {
                padding: 12px 16px;
                border-radius: 6px;
                margin: 2px 0;
            }
            
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
                border: 1px solid rgba(0, 120, 212, 0.3);
            }
            
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            /* 表格 */
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                gridline-color: rgba(0, 0, 0, 0.05);
                outline: none;
            }
            
            QTableWidget::item {
                padding: 8px 12px;
                border-radius: 4px;
            }
            
            QTableWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
            }
            
            QHeaderView::section {
                background-color: rgba(0, 0, 0, 0.05);
                color: #202020;
                padding: 12px 16px;
                border: none;
                border-right: 1px solid rgba(0, 0, 0, 0.1);
                font-weight: 600;
            }
            
            QHeaderView::section:last {
                border-right: none;
            }
            
            /* 文本编辑框 */
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
            
            QTextEdit:focus {
                border-color: #0078d4;
                background-color: #ffffff;
                outline: none;
            }
            
            QTextEdit:hover {
                border-color: rgba(0, 0, 0, 0.2);
            }
            
            /* 进度条 */
            QProgressBar {
                background-color: rgba(0, 0, 0, 0.05);
                border: none;
                border-radius: 8px;
                height: 8px;
                text-align: center;
                color: #202020;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12px;
            }
            
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 8px;
            }
            
            /* 分割条 */
            QSplitter::handle {
                background-color: rgba(0, 0, 0, 0.1);
                border: none;
                border-radius: 2px;
            }
            
            QSplitter::handle:horizontal {
                width: 4px;
                margin: 0 2px;
            }
            
            QSplitter::handle:vertical {
                height: 4px;
                margin: 2px 0;
            }
            
            QSplitter::handle:hover {
                background-color: rgba(0, 120, 212, 0.5);
            }
        """
    
    def _get_win11_dark_theme(self):
        """Windows 11深色主题样式"""
        return """
            /* Windows 11 风格 - 深色主题 */
            QMainWindow {
                background-color: #202020;
                color: #ffffff;
            }
            
            /* 菜单栏 - 深色毛玻璃效果 */
            QMenuBar {
                background-color: rgba(32, 32, 32, 0.8);
                backdrop-filter: blur(20px);
                color: #ffffff;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                padding: 4px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px;
            }
            
            QMenuBar::item:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #4cc2ff;
            }
            
            QMenuBar::item:pressed {
                background-color: rgba(0, 120, 212, 0.3);
            }
            
            /* 下拉菜单 */
            QMenu {
                background-color: rgba(32, 32, 32, 0.95);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
                margin: 4px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            
            QMenu::item {
                padding: 10px 16px;
                border-radius: 6px;
                margin: 2px 0;
                min-width: 200px;
                color: #ffffff;
            }
            
            QMenu::item:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #4cc2ff;
            }
            
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.1);
                margin: 8px 0;
            }
            
            /* 工具栏 */
            QToolBar {
                background-color: rgba(32, 32, 32, 0.8);
                backdrop-filter: blur(20px);
                border: none;
                spacing: 8px;
                padding: 8px 12px;
                border-radius: 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
            
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
            }
            
            QToolButton:checked {
                background-color: rgba(0, 120, 212, 0.2);
                border-color: #4cc2ff;
                color: #4cc2ff;
            }
            
            /* 状态栏 */
            QStatusBar {
                background-color: rgba(32, 32, 32, 0.8);
                backdrop-filter: blur(20px);
                color: #ffffff;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                padding: 8px 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
            
            /* 输入框 - 深色圆角设计 */
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                color: #ffffff;
                selection-background-color: #4cc2ff;
                selection-color: #202020;
            }
            
            QLineEdit:focus {
                border-color: #4cc2ff;
                background-color: rgba(255, 255, 255, 0.15);
                outline: none;
            }
            
            QLineEdit:hover {
                border-color: rgba(255, 255, 255, 0.2);
            }
            
            /* 按钮 - 深色圆角设计 */
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                min-height: 36px;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #106ebe;
                transform: translateY(-1px);
            }
            
            QPushButton:pressed {
                background-color: #005a9e;
                transform: translateY(0);
            }
            
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.3);
            }
            
            /* 次要按钮 */
            QPushButton[button-type="secondary"] {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            QPushButton[button-type="secondary"]:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            
            QPushButton[button-type="secondary"]:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
            
            /* 下拉框 */
            QComboBox {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                min-width: 140px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                color: #ffffff;
            }
            
            QComboBox:focus {
                border-color: #4cc2ff;
                background-color: rgba(255, 255, 255, 0.15);
            }
            
            QComboBox:hover {
                border-color: rgba(255, 255, 255, 0.2);
            }
            
            QComboBox::drop-down {
                border: none;
                width: 32px;
                border-radius: 0 6px 6px 0;
            }
            
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iI2NjY2NjYyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
                width: 12px;
                height: 8px;
            }
            
            /* 滚动条 - 深色Windows 11风格 */
            QScrollBar {
                background: transparent;
            }
            
            QScrollBar:vertical {
                width: 8px;
                margin: 4px 0;
                border-radius: 4px;
            }
            
            QScrollBar:horizontal {
                height: 8px;
                margin: 0 4px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 40px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            
            QScrollBar::handle:horizontal {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-width: 40px;
                margin: 2px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            
            /* 标签页 */
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                background-color: rgba(32, 32, 32, 0.9);
                margin: 0;
            }
            
            QTabBar::tab {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                margin: 4px 2px;
                color: #999999;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            
            QTabBar::tab:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #4cc2ff;
                font-weight: 600;
            }
            
            QTabBar::tab:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #cccccc;
            }
            
            /* 对话框 */
            QDialog {
                background-color: #202020;
                color: #ffffff;
                border-radius: 12px;
            }
            
            /* 分组框 */
            QGroupBox {
                font-weight: 600;
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 16px;
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 12px 0 12px;
                background-color: transparent;
                color: #ffffff;
                font-weight: 600;
            }
            
            /* 复选框 */
            QCheckBox {
                color: #ffffff;
                spacing: 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 0.1);
                margin-right: 8px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDRMNC41IDcuNUwxMSAxIiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            
            /* 单选框 */
            QRadioButton {
                color: #ffffff;
                spacing: 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 7px;
                background-color: rgba(255, 255, 255, 0.1);
                margin-right: 8px;
            }
            
            QRadioButton::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            
            /* 数字输入框 */
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            QSpinBox:focus {
                border-color: #4cc2ff;
                background-color: rgba(255, 255, 255, 0.15);
            }
            
            /* 滑块 */
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
            
            QSlider::handle:horizontal {
                background-color: #0078d4;
                border: none;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
            
            QSlider::handle:horizontal:hover {
                background-color: #106ebe;
                transform: scale(1.1);
            }
            
            QSlider::handle:horizontal:pressed {
                background-color: #005a9e;
                transform: scale(0.95);
            }
            
            /* 标签 */
            QLabel {
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            /* 树形控件 */
            QTreeWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            QTreeWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px 0;
            }
            
            QTreeWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #4cc2ff;
            }
            
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            /* 列表控件 */
            QListWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            QListWidget::item {
                padding: 12px 16px;
                border-radius: 6px;
                margin: 2px 0;
            }
            
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #4cc2ff;
                border: 1px solid rgba(0, 120, 212, 0.3);
            }
            
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            /* 表格 */
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                gridline-color: rgba(255, 255, 255, 0.05);
                outline: none;
            }
            
            QTableWidget::item {
                padding: 8px 12px;
                border-radius: 4px;
            }
            
            QTableWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #4cc2ff;
            }
            
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                padding: 12px 16px;
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
            }
            
            QHeaderView::section:last {
                border-right: none;
            }
            
            /* 文本编辑框 */
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px 16px;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                selection-background-color: #4cc2ff;
                selection-color: #202020;
            }
            
            QTextEdit:focus {
                border-color: #4cc2ff;
                background-color: rgba(255, 255, 255, 0.1);
                outline: none;
            }
            
            QTextEdit:hover {
                border-color: rgba(255, 255, 255, 0.2);
            }
            
            /* 进度条 */
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 8px;
                height: 8px;
                text-align: center;
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12px;
            }
            
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 8px;
            }
            
            /* 分割条 */
            QSplitter::handle {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            
            QSplitter::handle:horizontal {
                width: 4px;
                margin: 0 2px;
            }
            
            QSplitter::handle:vertical {
                height: 4px;
                margin: 2px 0;
            }
            
            QSplitter::handle:hover {
                background-color: rgba(76, 194, 255, 0.5);
            }
        """
    
    def apply_theme(self, theme_name: str, widget=None):
        """应用主题"""
        if theme_name not in self.themes:
            theme_name = "light"
        self.current_theme = theme_name
        style = self.themes[theme_name]
        try:
            fm = QFontMetrics(QApplication.instance().font())
            sz = max(10, min(16, int(round(fm.height() * 0.65))))
        except Exception:
            sz = 12
        override = f"""
            QCheckBox::indicator {{
                width: {sz}px;
                height: {sz}px;
                border-radius: 3px;
                margin-right: 6px;
            }}
            QRadioButton::indicator {{
                width: {sz}px;
                height: {sz}px;
                border-radius: {max(5, sz//2)}px;
                margin-right: 6px;
            }}
        """
        style = style + "\n" + override
        if widget:
            widget.setStyleSheet(style)
        else:
            QApplication.instance().setStyleSheet(style)
        self.theme_changed.emit(theme_name)
    
    def get_current_theme(self):
        """获取当前主题"""
        return self.current_theme
    
    def get_available_themes(self):
        """获取可用主题列表"""
        return list(self.themes.keys())