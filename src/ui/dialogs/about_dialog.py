# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...core.config import Config
from ...core.i18n import I18n
from ... import __version__, __author__


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            cfg = Config()
            lang = cfg.get('appearance.language', 'zh_CN')
        except Exception:
            lang = 'zh_CN'
        self.i18n = I18n(lang)

        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(self.i18n.t("关于 FalconPy"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("FalconPy")
        f = QFont()
        try:
            f.setPointSize(18)
            f.setWeight(QFont.Weight.Bold)
        except Exception:
            pass
        title.setFont(f)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(self.i18n.t("版本: {version}").format(version=__version__))
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        author = QLabel(self.i18n.t("作者: {author}").format(author=__author__))
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)

        desc1 = QLabel(self.i18n.t("FalconPy 是一个跨站图片浏览与收藏工具。"))
        desc1.setWordWrap(True)
        desc1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc1)

        desc2 = QLabel(self.i18n.t("专注可读性与简洁设计。"))
        desc2.setWordWrap(True)
        desc2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc2)

        try:
            repo = Config().get('updates.github_repo', '').strip()
        except Exception:
            repo = ''
        if repo:
            link = QLabel(f"<a href='https://github.com/{repo}'>{self.i18n.t('项目主页')}</a>")
            try:
                link.setTextFormat(Qt.TextFormat.RichText)
                link.setOpenExternalLinks(True)
            except Exception:
                pass
            link.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(link)

        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        close_btn = QPushButton(self.i18n.t("关闭"))
        close_btn.clicked.connect(self.close)
        btn_bar.addWidget(close_btn)
        layout.addLayout(btn_bar)

