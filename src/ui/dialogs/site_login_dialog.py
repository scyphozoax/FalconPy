# -*- coding: utf-8 -*-
"""
站点登录对话框：仅针对一个网站展示登录输入窗口
复用 LoginDialog 内的 SiteLoginWidget 与 LoginThread
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QProgressBar, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from typing import Dict

from .login_dialog import SiteLoginWidget, LoginThread
from ...core.config import Config
from ...core.i18n import I18n


class SiteLoginDialog(QDialog):
    """单站点登录对话框"""

    login_success = pyqtSignal(str, dict)  # 网站名, 用户信息
    login_failed = pyqtSignal(str, str)    # 网站名, 错误信息

    def __init__(self, site_name: str, site_config: Dict, parent=None):
        super().__init__(parent)
        try:
            cfg = Config()
            lang = cfg.get('appearance.language', 'zh_CN')
        except Exception:
            lang = 'zh_CN'
        self.i18n = I18n(lang)
        self.site_name = site_name
        self.site_config = site_config
        self.login_thread = None
        self._init_ui()

    def _init_ui(self):
        from PyQt6.QtWidgets import QApplication
        self.setWindowTitle(self.i18n.t("登录到 {site}").format(site=self.site_name))
        try:
            parent_w = self.parent().width() if self.parent() else None
        except Exception:
            parent_w = None
        screen_w = QApplication.primaryScreen().availableGeometry().width()
        max_w = int((parent_w or int(screen_w * 0.5)) * 1.0)
        self.setMinimumWidth(360)
        try:
            self.setMaximumWidth(max_w)
        except Exception:
            pass
        self.resize(min(max_w, 420), 320)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        title = QLabel(self.i18n.t("{site} 账号登录").format(site=self.site_name))
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 单站点登录组件
        self.site_widget = SiteLoginWidget(self.site_name, self.site_config, self.i18n)
        self.site_widget.login_requested.connect(self._handle_login_request)
        layout.addWidget(self.site_widget)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.close_btn = QPushButton(self.i18n.t("关闭"))
        self.close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def _handle_login_request(self, site: str, credentials: Dict):
        # 停止已有线程
        if self.login_thread is not None and self.login_thread.isRunning():
            self.login_thread.quit()
            self.login_thread.wait()

        self.login_thread = LoginThread(site, credentials)
        self.login_thread.login_success.connect(self._on_login_success)
        self.login_thread.login_failed.connect(self._on_login_failed)
        self.login_thread.start()

        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

    def _on_login_success(self, site: str, user_info: Dict):
        self.progress.setVisible(False)
        # 通知子组件
        self.site_widget.on_login_success(user_info)
        # 发射信号
        self.login_success.emit(site, user_info)
        QMessageBox.information(self, self.i18n.t("登录成功"), self.i18n.t("已成功登录到 {site}").format(site=site))

    def _on_login_failed(self, site: str, error: str):
        self.progress.setVisible(False)
        self.site_widget.on_login_failed(self.i18n.t(error))
        self.login_failed.emit(site, error)

    def closeEvent(self, event):
        if self.login_thread is not None and self.login_thread.isRunning():
            self.login_thread.quit()
            self.login_thread.wait()
        event.accept()