# -*- coding: utf-8 -*-
"""
网站选择器组件
"""

from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt

class SiteSelectorWidget(QWidget):
    """网站选择器"""
    
    site_changed = pyqtSignal(str)  # 网站改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签
        label = QLabel("网站:")
        layout.addWidget(label)
        
        # 下拉框
        self.combo_box = QComboBox()
        self.combo_box.addItems([
            "Danbooru",
            "Konachan",
            "Yande.re"
        ])
        
        # 连接信号
        self.combo_box.currentTextChanged.connect(self.on_site_changed)
        
        layout.addWidget(self.combo_box)
    
    def on_site_changed(self, site_name):
        """网站改变事件"""
        self.site_changed.emit(site_name.lower())
    
    def get_current_site(self):
        """获取当前选择的网站"""
        return self.combo_box.currentText().lower()
    
    def set_current_site(self, site_name):
        """设置当前网站"""
        index = self.combo_box.findText(site_name, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.combo_box.setCurrentIndex(index)