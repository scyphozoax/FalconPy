# -*- coding: utf-8 -*-
from PyQt6.QtCore import QThread, pyqtSignal
import os
import json
from pathlib import Path
import requests

class DownloadTask:
    def __init__(self, url: str, site: str, post_id: str, ext: str, save_dir: Path, headers: dict, proxies: dict | None,
                 timeout: int, max_file_size_mb: int, metadata: dict | None):
        self.url = url
        self.site = site
        self.post_id = post_id
        self.ext = ext
        self.save_dir = save_dir
        self.headers = headers
        self.proxies = proxies
        self.timeout = timeout
        self.max_file_size_mb = max_file_size_mb
        self.metadata = metadata or {}

class DownloadQueueThread(QThread):
    task_started = pyqtSignal(int, str)
    task_progress = pyqtSignal(int, int, int)
    task_finished = pyqtSignal(int, bool, str, str)
    overall_progress = pyqtSignal(int, int)
    queue_finished = pyqtSignal()
    canceled = pyqtSignal()

    def __init__(self, tasks: list[DownloadTask], auto_rename: bool, save_metadata: bool, max_retries: int):
        super().__init__()
        self.tasks = tasks
        self.auto_rename = auto_rename
        self.save_metadata = save_metadata
        self.max_retries = max_retries
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        total_size = 0
        for t in self.tasks:
            sz = int(t.metadata.get('file_size', 0) or 0)
            if sz > 0:
                total_size += sz
        total_written = 0

        session = requests.Session()
        try:
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        except Exception:
            pass
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            retry = Retry(total=self.max_retries, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
        except Exception:
            pass

        for idx, task in enumerate(self.tasks):
            if self._cancel:
                self.canceled.emit()
                break
            self.task_started.emit(idx, f"{task.site}_{task.post_id}.{task.ext}")
            task.save_dir.mkdir(parents=True, exist_ok=True)
            def build_filename(n: int = 0):
                sfx = f"_{n}" if n > 0 else ""
                return task.save_dir / f"{task.site}_{task.post_id}{sfx}.{task.ext}"
            target_path = build_filename(0)
            if target_path.exists() and self.auto_rename:
                n = 1
                while build_filename(n).exists():
                    n += 1
                target_path = build_filename(n)
            temp_path = target_path.with_suffix(target_path.suffix + '.part')

            headers = dict(task.headers)
            existing_size = temp_path.stat().st_size if temp_path.exists() else 0
            if existing_size > 0:
                headers['Range'] = f'bytes={existing_size}-'
            try:
                resp = session.get(task.url, headers=headers, stream=True, timeout=task.timeout, proxies=task.proxies)
            except Exception as e:
                self.task_finished.emit(idx, False, str(target_path), str(e))
                continue
            if resp.status_code == 403:
                self.task_finished.emit(idx, False, str(target_path), '403')
                continue
            try:
                resp.raise_for_status()
            except Exception as e:
                self.task_finished.emit(idx, False, str(target_path), str(e))
                continue

            total = None
            if resp.status_code == 206:
                cr = resp.headers.get('Content-Range')
                if cr and '/' in cr:
                    try:
                        total = int(cr.split('/')[-1])
                    except Exception:
                        total = None
            if total is None:
                try:
                    total = int(resp.headers.get('Content-Length', '0') or 0)
                except Exception:
                    total = 0

            if total and task.max_file_size_mb > 0:
                if total / (1024 * 1024) > task.max_file_size_mb:
                    self.task_finished.emit(idx, False, str(target_path), 'size_limit')
                    continue

            mode = 'ab' if existing_size > 0 and resp.status_code == 206 else 'wb'
            written = existing_size
            try:
                with open(temp_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if self._cancel:
                            self.canceled.emit()
                            break
                        if not chunk:
                            continue
                        f.write(chunk)
                        written += len(chunk)
                        self.task_progress.emit(idx, written, total or 0)
                        total_written += len(chunk)
                        self.overall_progress.emit(total_written, total_size)
            except Exception as e:
                self.task_finished.emit(idx, False, str(target_path), str(e))
                continue

            if self._cancel:
                self.task_finished.emit(idx, False, str(target_path), 'canceled')
                break

            try:
                temp_path.replace(target_path)
            except Exception:
                os.replace(str(temp_path), str(target_path))

            if self.save_metadata:
                meta_path = target_path.with_suffix(target_path.suffix + '.json')
                try:
                    with open(meta_path, 'w', encoding='utf-8') as mf:
                        json.dump(task.metadata, mf, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            self.task_finished.emit(idx, True, str(target_path), '')

        self.queue_finished.emit()