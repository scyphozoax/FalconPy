# -*- coding: utf-8 -*-
"""
登录对话框
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QLabel, QLineEdit, QPushButton, QComboBox, 
                            QCheckBox, QTextEdit, QTabWidget, QWidget,
                            QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap

import asyncio
import aiohttp
from typing import Dict, Optional
from ...core.i18n import I18n
from ...core.config import Config
from ..threads.network_diag_thread import NetworkDiagnosticsThread

class LoginThread(QThread):
    """登录线程"""
    
    login_success = pyqtSignal(str, dict)  # 网站名, 用户信息
    login_failed = pyqtSignal(str, str)    # 网站名, 错误信息
    
    def __init__(self, site: str, credentials: Dict[str, str]):
        super().__init__()
        self.site = site
        self.credentials = credentials
    
    def run(self):
        """执行登录"""
        try:
            # 这里应该调用相应的API客户端进行登录
            # 暂时模拟登录过程
            import time
            time.sleep(2)  # 模拟网络请求
            # 按站点判断凭据要求：
            site = self.site.strip()
            username = (self.credentials.get('username') or '').strip()
            password = (self.credentials.get('password') or '').strip()
            api_key = (self.credentials.get('api_key') or '').strip()

            ok = False
            # Danbooru 使用用户名+API码
            if site.lower() == 'danbooru':
                ok = bool(username and api_key)
            # Konachan / Yande.re 使用用户名 + （密码 或 API码）
            elif site.lower() in ('konachan', 'yande.re'):
                ok = bool(username and (password or api_key))

            if ok:
                # 模拟成功登录，包含用于后续保存的凭据字段
                user_info = {
                    'username': username,
                    'user_id': '12345',
                    'avatar_url': '',
                    'level': 'Member'
                }
                if api_key:
                    user_info['api_key'] = api_key
                if password:
                    user_info['password'] = password
                self.login_success.emit(self.site, user_info)
            else:
                # 统一提示文案（根据站点类型）
                if site.lower() == 'danbooru':
                    self.login_failed.emit(self.site, "请填写用户名与API码")
                elif site.lower() in ('konachan', 'yande.re'):
                    self.login_failed.emit(self.site, "请填写用户名，并提供密码或API码")
                else:
                    self.login_failed.emit(self.site, "请填写必需的登录信息")
                
        except Exception as e:
            self.login_failed.emit(self.site, str(e))

class SiteLoginWidget(QWidget):
    """单个网站登录组件"""
    
    login_requested = pyqtSignal(str, dict)  # 网站名, 凭据
    
    def __init__(self, site_name: str, site_config: Dict, i18n: I18n):
        super().__init__()
        self.site_name = site_name
        self.site_config = site_config
        self.i18n = i18n
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        # 顶部站点信息（图标、名称、描述）已移除，保留纯表单
        
        # 登录表单
        form_layout = QFormLayout()
        form_layout.setContentsMargins(12, 8, 12, 8)
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(12)
        
        # 用户名
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self.i18n.t("输入用户名"))
        form_layout.addRow(self.i18n.t("用户名:"), self.username_input)
        
        # 密码
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(self.i18n.t("输入密码"))
        form_layout.addRow(self.i18n.t("密码:"), self.password_input)
        
        # API码（所有网站均可选支持）
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText(self.i18n.t("输入API码"))
        form_layout.addRow(self.i18n.t("API码:"), self.api_key_input)
        
        layout.addLayout(form_layout)
        
        # 记住登录信息
        self.remember_checkbox = QCheckBox(self.i18n.t("记住登录信息"))
        layout.addWidget(self.remember_checkbox)
        
        # 登录按钮
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        self.login_button = QPushButton(self.i18n.t("登录"))
        self.login_button.clicked.connect(self.perform_login)
        
        self.test_button = QPushButton(self.i18n.t("测试连接"))
        self.test_button.clicked.connect(self.test_connection)
        
        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.login_button)
        
        layout.addLayout(button_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.status_label)

        layout.addStretch()
    
    def perform_login(self):
        """执行登录"""
        credentials = {
            'username': self.username_input.text().strip(),
            'password': self.password_input.text().strip(),
            'api_key': self.api_key_input.text().strip()
        }

        # 基本校验：至少需要用户名，其余由后台线程按站点规则判断
        if not credentials.get('username'):
            self.status_label.setText(self.i18n.t("请填写用户名"))
            self.status_label.setStyleSheet("color: #d13438;")
            return
        
        self.login_button.setEnabled(False)
        self.status_label.setText(self.i18n.t("正在登录..."))
        self.status_label.setStyleSheet("color: #0078d4;")
        
        self.login_requested.emit(self.site_name, credentials)
    
    def test_connection(self):
        """测试连接：调用网络诊断线程并展示结果提示。"""
        self.status_label.setText(self.i18n.t("正在测试连接..."))
        self.status_label.setStyleSheet("color: #0078d4;")

        # 启动诊断线程
        self._diag_thread = NetworkDiagnosticsThread(self.site_name)

        def on_success(details: str):
            self.status_label.setText(self.i18n.t("连接正常"))
            self.status_label.setStyleSheet("color: #107c10;")
            # 详细信息放到提示中，便于查看
            self.status_label.setToolTip(details)

        def on_failed(details: str):
            self.status_label.setText(self.i18n.t("连接失败"))
            self.status_label.setStyleSheet("color: #d13438;")
            self.status_label.setToolTip(details)

        self._diag_thread.success.connect(on_success)
        self._diag_thread.failed.connect(on_failed)
        self._diag_thread.start()
    
    def on_login_success(self, user_info: Dict):
        """登录成功"""
        self.login_button.setEnabled(True)
        self.status_label.setText(self.i18n.t("登录成功 - 欢迎 {username}").format(username=user_info.get('username', '')))
        self.status_label.setStyleSheet("color: #107c10;")
    
    def on_login_failed(self, error: str):
        """登录失败"""
        self.login_button.setEnabled(True)
        self.status_label.setText(self.i18n.t("登录失败: {error}").format(error=self.i18n.t(error)))
        self.status_label.setStyleSheet("color: #d13438;")

class LoginDialog(QDialog):
    """登录对话框"""
    
    login_success = pyqtSignal(str, dict)  # 网站名, 用户信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            cfg = Config()
            lang = cfg.get('appearance.language', 'zh_CN')
        except Exception:
            lang = 'zh_CN'
        self.i18n = I18n(lang)
        self.login_threads = {}
        self.init_ui()
        self.setup_sites()
    
    def init_ui(self):
        """初始化界面"""
        from PyQt6.QtWidgets import QApplication
        self.setWindowTitle("")
        try:
            parent_w = self.parent().width() if self.parent() else None
        except Exception:
            parent_w = None
        screen_w = QApplication.primaryScreen().availableGeometry().width()
        max_w = int((parent_w or int(screen_w * 0.5)) * 1.0)
        self.setMinimumWidth(460)
        try:
            self.setMaximumWidth(max_w)
        except Exception:
            pass
        self.resize(min(max_w, 480), 560)
        self.setModal(True)
        
        from PyQt6.QtWidgets import QScrollArea, QFrame
        layout = QVBoxLayout(self)
        
        # 标题
        
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        desc_label = QLabel(self.i18n.t("登录后可以访问您的在线收藏夹和个人设置"))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px;")
        content_layout.addWidget(desc_label)
        
        self.tab_widget = QTabWidget()
        content_layout.addWidget(self.tab_widget)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)

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
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.close_button = QPushButton(self.i18n.t("关闭"))
        self.close_button.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        # 取消对话框的局部硬编码样式，改为使用全局主题管理器
    
    def setup_sites(self):
        """设置支持的网站"""
        sites_config = {
            'Danbooru': {
                'description': '高质量动漫图片社区',
                'requires_api_key': True
            },
            'Konachan': {
                'description': '高分辨率壁纸网站',
                'requires_api_key': False
            },
            'Yande.re': {
                'description': '精选动漫壁纸',
                'requires_api_key': False
            }
        }
        
        for site_name, config in sites_config.items():
            site_widget = SiteLoginWidget(site_name, config, self.i18n)
            site_widget.login_requested.connect(self.handle_login_request)
            self.tab_widget.addTab(site_widget, site_name)
    
    def handle_login_request(self, site: str, credentials: Dict):
        """处理登录请求"""
        # 停止之前的登录线程
        if site in self.login_threads:
            self.login_threads[site].quit()
            self.login_threads[site].wait()
        
        # 创建新的登录线程
        login_thread = LoginThread(site, credentials)
        login_thread.login_success.connect(self.on_login_success)
        login_thread.login_failed.connect(self.on_login_failed)
        
        self.login_threads[site] = login_thread
        login_thread.start()
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
    
    def on_login_success(self, site: str, user_info: Dict):
        """登录成功处理"""
        self.progress_bar.setVisible(False)
        
        # 通知对应的网站组件
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, SiteLoginWidget) and widget.site_name == site:
                widget.on_login_success(user_info)
                break
        
        # 发送成功信号
        self.login_success.emit(site, user_info)
        
        # 显示成功消息
        QMessageBox.information(self, self.i18n.t("登录成功"), self.i18n.t("已成功登录到 {site}").format(site=site))
    
    def on_login_failed(self, site: str, error: str):
        """登录失败处理"""
        self.progress_bar.setVisible(False)
        
        # 通知对应的网站组件
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, SiteLoginWidget) and widget.site_name == site:
                widget.on_login_failed(self.i18n.t(error))
                break
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止所有登录线程
        for thread in self.login_threads.values():
            if thread.isRunning():
                thread.quit()
                thread.wait()
        
        event.accept()