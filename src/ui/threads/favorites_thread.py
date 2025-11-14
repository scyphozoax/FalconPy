# -*- coding: utf-8 -*-
"""
在线收藏获取线程：在后台线程中运行异步获取，避免阻塞 UI。
仅实现 Danbooru 站点的 favorites 获取。
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

class FavoritesFetchThread(QThread):
    """使用 asyncio 运行 APIManager.get_favorites 的线程"""

    favorites_ready = pyqtSignal(list)  # 统一格式的图片数据列表
    error = pyqtSignal(str)

    def __init__(self, api_manager, site: str, page: int = 1, limit: int = 40):
        super().__init__()
        self.api_manager = api_manager
        self.site = site
        self.page = page
        self.limit = limit
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
            f_fetch = asyncio.run_coroutine_threadsafe(
                self.api_manager.get_favorites(self.site, page=self.page, limit=self.limit), loop
            )
            self._futures = [f_fetch]
            try:
                results = f_fetch.result()
            except concurrent.futures.CancelledError:
                return
            except Exception as e:
                raise e
            if self.isInterruptionRequested() or self._cancelled:
                return
            self.favorites_ready.emit(results)
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
