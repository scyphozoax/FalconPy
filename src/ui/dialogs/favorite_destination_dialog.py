# -*- coding: utf-8 -*-
"""
收藏目标选择对话框：允许用户选择收藏到本地收藏夹或在线收藏夹，
并可记住选择为当前站点默认。
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QRadioButton, QComboBox, QPushButton, QCheckBox)
from PyQt6.QtCore import Qt
from ...core.config import Config

from ...core.database import DatabaseManager


class FavoriteDestinationDialog(QDialog):
    def __init__(self, site_key: str, parent=None):
        super().__init__(parent)
        self.site_key = site_key
        self.db = DatabaseManager()
        self.cfg = Config()
        self.setWindowTitle("选择收藏目标")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        site_label = QLabel(f"站点：{site_key.capitalize()}")
        layout.addWidget(site_label)

        # 目标选项
        self.radio_local = QRadioButton("本地收藏夹")
        self.radio_online = QRadioButton("在线收藏夹")
        self.radio_local.setChecked(True)
        layout.addWidget(self.radio_local)

        # 本地收藏夹选择
        local_row = QHBoxLayout()
        self.folder_box = QComboBox()
        self._reload_folders()
        self.new_btn = QPushButton("新建收藏夹")
        self.new_btn.clicked.connect(self._create_folder)
        local_row.addWidget(QLabel("本地收藏夹："))
        local_row.addWidget(self.folder_box)
        local_row.addWidget(self.new_btn)
        layout.addLayout(local_row)

        layout.addWidget(self.radio_online)
        layout.addWidget(QLabel("说明：在线收藏将添加到网站账号的收藏列表"))

        # 根据站点与凭据决定是否允许在线收藏
        self._apply_online_capability()

        # 记住选择
        self.remember_box = QCheckBox("记住本次选择（设为该网站默认）")
        layout.addWidget(self.remember_box)

        # 操作按钮
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _reload_folders(self):
        self.folder_box.clear()
        folders = self.db.get_favorites()  # 使用新的 favorites 表
        for f in folders:
            self.folder_box.addItem(f.get('name', f"收藏夹{f.get('id')}") , f.get('id'))
        if not folders:
            # 若无则自动创建默认收藏夹
            default_id = self.db.create_favorite('默认收藏夹', '默认收藏夹')
            self.folder_box.addItem('默认收藏夹', default_id)

    def _create_folder(self):
        try:
            new_id = self.db.create_favorite('新收藏夹', '用户创建')
            self._reload_folders()
            # 选中新建项
            idx = max(0, self.folder_box.findData(new_id))
            self.folder_box.setCurrentIndex(idx)
        except Exception:
            pass

    def _apply_online_capability(self):
        site = (self.site_key or '').lower()
        # 仅 Danbooru 目前支持在线收藏操作
        if site != 'danbooru':
            self.radio_online.setEnabled(False)
            self.radio_online.setToolTip("当前版本尚未支持该站点的在线收藏")
            return
        # Danbooru 需要用户名与 API码
        username = self.cfg.get('sites.danbooru.username', '')
        api_key = self.cfg.get('sites.danbooru.api_key', '')
        if not (username and api_key):
            self.radio_online.setEnabled(False)
            self.radio_online.setToolTip("需登录并提供API码后才能使用在线收藏")
        else:
            self.radio_online.setEnabled(True)
            self.radio_online.setToolTip("")

    def get_selection(self) -> dict:
        return {
            'destination': 'local' if self.radio_local.isChecked() else 'online',
            'folder_id': self.folder_box.currentData(),
            'remember': self.remember_box.isChecked()
        }