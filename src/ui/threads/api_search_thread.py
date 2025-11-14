# -*- coding: utf-8 -*-
"""
API 搜索线程：在后台线程中运行异步搜索，避免阻塞 UI。
重构为线程内独立事件循环，并支持协作式取消。
"""

from PyQt6.QtCore import QThread, pyqtSignal
import threading
import asyncio
import concurrent.futures


_SHARED_LOOP = None
_SHARED_THREAD = None

def _ensure_shared_loop():
    global _SHARED_LOOP, _SHARED_THREAD
    if _SHARED_LOOP and _SHARED_THREAD and _SHARED_THREAD.is_alive():
        return _SHARED_LOOP
    loop = asyncio.new_event_loop()
    def _runner():
        asyncio.set_event_loop(loop)
        loop.run_forever()
    t = threading.Thread(target=_runner, name="FalconPyAsyncLoop", daemon=True)
    t.start()
    _SHARED_LOOP = loop
    _SHARED_THREAD = t
    return loop

class APISearchThread(QThread):
    """使用 asyncio 运行 APIManager.search 的线程"""

    results_ready = pyqtSignal(list, int, int)  # results, page, total_pages
    error = pyqtSignal(str)

    def __init__(self, api_manager, site: str, query: str, page: int = 1, limit: int = 20):
        super().__init__()
        self.api_manager = api_manager
        self.site = site
        self.query = query
        self.page = page
        self.limit = limit
        # 事件循环与任务引用，用于跨线程取消
        self._futures = []
        self._cancelled = False

    def cancel(self):
        """请求中断并取消正在运行的异步任务。"""
        try:
            self._cancelled = True
            self.requestInterruption()
            for f in list(self._futures):
                try:
                    f.cancel()
                except Exception:
                    pass
        except Exception:
            pass

    def run(self):
        try:
            loop = _ensure_shared_loop()
            if self.isInterruptionRequested() or self._cancelled:
                return
            f_search = asyncio.run_coroutine_threadsafe(
                self.api_manager.search(self.site, self.query, self.page, self.limit), loop
            )
            self._futures = [f_search]
            try:
                results = f_search.result()
            except concurrent.futures.CancelledError:
                return
            except Exception as e:
                raise e
            if self.isInterruptionRequested() or self._cancelled:
                return
            total_pages = None
            try:
                f_count = asyncio.run_coroutine_threadsafe(
                    self.api_manager.count(self.site, self.query), loop
                )
                self._futures.append(f_count)
                total_count = f_count.result(timeout=8.0)
                if isinstance(total_count, int) and total_count >= 0:
                    total_pages = max(1, (total_count + self.limit - 1) // self.limit)
            except concurrent.futures.TimeoutError:
                total_pages = None
            except concurrent.futures.CancelledError:
                return
            except Exception:
                total_pages = None
            if total_pages is None:
                results_len = len(results) if isinstance(results, list) else 0
                if results_len == 0:
                    total_pages = max(1, self.page - 1)
                elif results_len < self.limit:
                    total_pages = max(1, self.page)
                else:
                    total_pages = max(1, self.page + 1)
            self.results_ready.emit(results, self.page, total_pages)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
        finally:
            try:
                for f in list(self._futures):
                    try:
                        if not f.done():
                            f.cancel()
                    except Exception:
                        pass
                self._futures.clear()
            except Exception:
                pass
