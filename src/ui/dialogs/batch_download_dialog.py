# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt
from ..threads.download_queue_thread import DownloadQueueThread, DownloadTask
from ...core.config import Config
from pathlib import Path

class BatchDownloadDialog(QDialog):
    def __init__(self, parent, images: list, i18n=None, config: Config | None = None):
        super().__init__(parent)
        self._parent = parent
        self._i18n = i18n
        self._images = images or []
        self._config = config or getattr(parent, 'config', Config())
        self.setWindowTitle(self._i18n.t('批量下载') if self._i18n else '批量下载')
        self.resize(720, 420)

        layout = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title_label = QLabel(self._i18n.t('下载队列') if self._i18n else '下载队列')
        head.addWidget(self.title_label)
        head.addStretch(1)
        layout.addLayout(head)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            self._i18n.t('文件') if self._i18n else '文件',
            self._i18n.t('大小') if self._i18n else '大小',
            self._i18n.t('进度') if self._i18n else '进度',
            self._i18n.t('状态') if self._i18n else '状态',
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        total_row = QHBoxLayout()
        self.total_label = QLabel(self._i18n.t('总体进度') if self._i18n else '总体进度')
        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 0)
        total_row.addWidget(self.total_label)
        total_row.addWidget(self.total_progress)
        layout.addLayout(total_row)

        btns = QHBoxLayout()
        self.btn_cancel = QPushButton(self._i18n.t('取消') if self._i18n else '取消')
        self.btn_close = QPushButton(self._i18n.t('关闭') if self._i18n else '关闭')
        btns.addStretch(1)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)

        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_close.clicked.connect(self.close)

        self._rows = []
        self._build_tasks()
        self._start()

    def _build_tasks(self):
        base_path = self._config.get('download.path', './downloads')
        auto_rename = self._config.get('download.auto_rename', True)
        create_subfolders = self._config.get('download.create_subfolders', True)
        save_metadata = self._config.get('download.save_metadata', False)
        download_original = self._config.get('download.download_original', True)
        max_file_size_mb = int(self._config.get('download.max_file_size', 50) or 50)
        timeout = int(self._config.get('network.timeout', 30) or 30)
        max_retries = int(self._config.get('network.max_retries', 3) or 3)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        tasks = []
        base_dir = Path(base_path).expanduser()
        if not base_dir.is_absolute():
            base_dir = Path(self._config.app_dir) / base_dir

        proxies = None
        if self._config.get('network.use_proxy', False):
            host = self._config.get('network.proxy_host', '')
            port = self._config.get('network.proxy_port', 0)
            if host and port:
                proxy_url = f"http://{host}:{port}"
                proxies = {"http": proxy_url, "https": proxy_url}

        for img in self._images:
            site = (img.get('site') or 'unknown').lower()
            post_id = str(img.get('id', 'unknown'))
            url = img.get('file_url') if download_original else None
            if not url:
                url = img.get('file_url') or img.get('preview_url') or img.get('thumbnail_url')
            if not url:
                continue
            ext = (img.get('file_ext') or Path(url).suffix.lstrip('.').lower() or 'jpg')
            ext = ''.join(c for c in ext if c.isalnum()) or 'jpg'
            h = dict(headers)
            referer = None
            pu = img.get('post_url') or ''
            if pu:
                referer = pu
            else:
                if site == 'danbooru' and post_id and post_id.isdigit():
                    referer = f'https://danbooru.donmai.us/posts/{post_id}'
                elif site == 'konachan' and post_id and post_id.isdigit():
                    referer = f'https://konachan.net/post/show/{post_id}'
                elif site == 'yandere' and post_id and post_id.isdigit():
                    referer = f'https://yande.re/post/show/{post_id}'
            if not referer:
                if site == 'danbooru':
                    referer = 'https://danbooru.donmai.us'
                elif site == 'konachan':
                    referer = 'https://konachan.net'
                elif site == 'yandere':
                    referer = 'https://yande.re'
            if referer:
                h['Referer'] = referer

            save_dir = base_dir / site if create_subfolders else base_dir

            t = DownloadTask(url, site, post_id, ext, save_dir, h, proxies, timeout, max_file_size_mb, img)
            tasks.append(t)

        self._tasks = tasks
        self._auto_rename = auto_rename
        self._save_metadata = save_metadata
        self._max_retries = max_retries

        for i, img in enumerate(self._images):
            name = f"{(img.get('site') or 'unknown').lower()}_{str(img.get('id', 'unknown'))}.{(img.get('file_ext') or '').lower()}"
            size_mb = 0.0
            try:
                size_mb = float(img.get('file_size', 0) or 0) / (1024 * 1024)
            except Exception:
                size_mb = 0.0
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{size_mb:.2f} MB" if size_mb > 0 else "-"))
            pb = QProgressBar()
            pb.setRange(0, 0)
            self.table.setCellWidget(row, 2, pb)
            self.table.setItem(row, 3, QTableWidgetItem(""))
            self._rows.append({'pb': pb})

    def _start(self):
        self._thread = DownloadQueueThread(self._tasks, self._auto_rename, self._save_metadata, self._max_retries)
        self._thread.task_started.connect(self._on_task_started)
        self._thread.task_progress.connect(self._on_task_progress)
        self._thread.task_finished.connect(self._on_task_finished)
        self._thread.overall_progress.connect(self._on_overall)
        self._thread.queue_finished.connect(self._on_queue_finished)
        self._thread.canceled.connect(self._on_canceled)
        self._thread.start()

    def _on_task_started(self, idx: int, name: str):
        try:
            self.table.item(idx, 3).setText(self._i18n.t('下载中') if self._i18n else '下载中')
            self._rows[idx]['pb'].setRange(0, 0)
        except Exception:
            pass

    def _on_task_progress(self, idx: int, cur: int, total: int):
        try:
            if total > 0:
                self._rows[idx]['pb'].setRange(0, total)
                self._rows[idx]['pb'].setValue(cur)
            else:
                self._rows[idx]['pb'].setRange(0, 0)
        except Exception:
            pass

    def _on_task_finished(self, idx: int, ok: bool, path: str, err: str):
        try:
            self._rows[idx]['pb'].setRange(0, 1)
            self._rows[idx]['pb'].setValue(1 if ok else 0)
            self.table.item(idx, 3).setText(self._i18n.t('完成') if ok else (self._i18n.t('失败') if self._i18n else ('完成' if ok else '失败')))
        except Exception:
            pass

    def _on_overall(self, cur: int, total: int):
        try:
            if total > 0:
                self.total_progress.setRange(0, total)
                self.total_progress.setValue(cur)
            else:
                self.total_progress.setRange(0, 0)
        except Exception:
            pass

    def _on_queue_finished(self):
        try:
            self.total_progress.setRange(0, 1)
            self.total_progress.setValue(1)
            self.title_label.setText(self._i18n.t('下载完成') if self._i18n else '下载完成')
        except Exception:
            pass

    def _on_canceled(self):
        try:
            self.title_label.setText(self._i18n.t('已取消') if self._i18n else '已取消')
        except Exception:
            pass

    def _on_cancel(self):
        try:
            if hasattr(self, '_thread') and self._thread:
                self._thread.cancel()
        except Exception:
            pass