# -*- coding: utf-8 -*-
"""
账号管理对话框：统一管理各网站的登录状态，提供登录/登出入口
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QGridLayout,
    QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from typing import Dict

from ...core.config import Config
from ...core.i18n import I18n
from ...core.session_manager import SessionManager
from .site_login_dialog import SiteLoginDialog


class AccountManagementDialog(QDialog):
    """账号管理页面"""

    login_success = pyqtSignal(str, dict)   # 网站, 用户信息
    logout_requested = pyqtSignal(str)      # 请求登出的网站

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            cfg = Config()
            lang = cfg.get('appearance.language', 'zh_CN')
        except Exception:
            lang = 'zh_CN'
        self.i18n = I18n(lang)
        self.session_manager = SessionManager()

        # 站点配置（与登录页保持一致）
        self.sites_config: Dict[str, Dict] = {
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

        self.row_widgets: Dict[str, Dict[str, QWidget]] = {}
        self._init_ui()
        self._refresh_rows()

    def _init_ui(self):
        from PyQt6.QtWidgets import QApplication
        self.setWindowTitle("")
        try:
            parent_w = self.parent().width() if self.parent() else None
        except Exception:
            parent_w = None
        screen_w = QApplication.primaryScreen().availableGeometry().width()
        max_w = int((parent_w or int(screen_w * 0.6)) * 1.0)
        self.setMinimumWidth(480)
        try:
            self.setMaximumWidth(max_w)
        except Exception:
            pass
        self.resize(min(max_w, 520), 360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        

        desc = QLabel(self.i18n.t("在此管理各网站的登录状态与凭据"))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)
        layout.addLayout(grid)
        self.grid = grid

        # 表头
        header_site = QLabel(self.i18n.t("网站"))
        header_status = QLabel(self.i18n.t("状态"))
        header_actions = QLabel(self.i18n.t("操作"))
        header_site.setStyleSheet("font-weight: bold;")
        header_status.setStyleSheet("font-weight: bold;")
        header_actions.setStyleSheet("font-weight: bold;")
        grid.addWidget(header_site, 0, 0)
        grid.addWidget(header_status, 0, 1)
        grid.addWidget(header_actions, 0, 2)

        # 各站点行将由 _refresh_rows 填充

    def _refresh_rows(self):
        # 清理旧行（除表头）
        # 简洁处理：不移除控件，仅更新文本与按钮状态
        row_index = 1
        for site, cfg in self.sites_config.items():
            if site not in self.row_widgets:
                # 新建行
                site_label = QLabel(site)
                status_label = QLabel("")
                actions = QWidget()
                h = QHBoxLayout(actions)
                h.setContentsMargins(0, 0, 0, 0)
                h.setSpacing(6)
                login_btn = QPushButton(self.i18n.t("登录"))
                logout_btn = QPushButton(self.i18n.t("登出"))
                h.addWidget(login_btn)
                h.addWidget(logout_btn)

                self.grid.addWidget(site_label, row_index, 0)
                self.grid.addWidget(status_label, row_index, 1)
                self.grid.addWidget(actions, row_index, 2)

                self.row_widgets[site] = {
                    'status': status_label,
                    'login': login_btn,
                    'logout': logout_btn
                }

                login_btn.clicked.connect(lambda checked=False, s=site: self._open_login_for_site(s))
                logout_btn.clicked.connect(lambda checked=False, s=site: self._request_logout(s))

                row_index += 1
            # 更新状态
            status = self._site_status_text(site)
            self.row_widgets[site]['status'].setText(status)
            is_logged_in = self.session_manager.is_logged_in(site)
            self.row_widgets[site]['logout'].setEnabled(is_logged_in)
            self.row_widgets[site]['login'].setEnabled(True)

    def _site_status_text(self, site: str) -> str:
        info = self.session_manager.get_user_info(site)
        if info:
            username = info.get('username', '')
            return self.i18n.t("已登录: {username}").format(username=username)
        return self.i18n.t("未登录")

    def _open_login_for_site(self, site: str):
        cfg = self.sites_config.get(site, {'requires_api_key': False})
        dlg = SiteLoginDialog(site, cfg, self)
        # 主题应用在外部主窗口中进行，这里只处理逻辑
        dlg.login_success.connect(self._on_login_success)
        dlg.login_failed.connect(self._on_login_failed)
        dlg.exec()

    def _on_login_success(self, site: str, user_info: Dict):
        # 透传给外部（主窗口）统一处理会话与UI
        self.login_success.emit(site, user_info)
        # 刷新本页状态
        self._refresh_rows()

    def _on_login_failed(self, site: str, error: str):
        QMessageBox.warning(self, self.i18n.t("登录失败"), self.i18n.t(error))

    def _request_logout(self, site: str):
        self.logout_requested.emit(site)
        # 外部处理后刷新
        self._refresh_rows()