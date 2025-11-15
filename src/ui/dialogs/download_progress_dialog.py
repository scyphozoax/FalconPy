# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import pyqtSignal

class DownloadProgressDialog(QDialog):
    canceled = pyqtSignal()

    def __init__(self, parent=None, i18n=None):
        super().__init__(parent)
        self._i18n = i18n
        self._canceled = False
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        self.title_label = QLabel("")
        self.info_label = QLabel("")
        self.progress_bar = QProgressBar()
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton(self._i18n.t("取消") if self._i18n else "取消")
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        layout.addWidget(self.title_label)
        layout.addWidget(self.info_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(btn_row)
        self.cancel_btn.clicked.connect(self._on_cancel)

    def setup(self, total: int, initial: int, title: str, filename: str):
        self.setWindowTitle(title)
        self.title_label.setText(title)
        self.info_label.setText(filename)
        if total and total > 0:
            self.progress_bar.setRange(0, int(total))
            self.progress_bar.setValue(int(initial))
        else:
            self.progress_bar.setRange(0, 0)

    def set_value(self, v: int):
        self.progress_bar.setValue(int(v))

    def set_text(self, text: str):
        self.info_label.setText(text)

    def was_canceled(self) -> bool:
        return self._canceled

    def _on_cancel(self):
        self._canceled = True
        try:
            self.canceled.emit()
        except Exception:
            pass