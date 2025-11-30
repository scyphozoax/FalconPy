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

class TagsQueryThread(QThread):
    tags_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api_manager, site: str, query: str, limit: int = 100):
        super().__init__()
        self.api_manager = api_manager
        self.site = site
        self.query = query
        self.limit = limit
        self._futures = []
        self._cancelled = False

    def cancel(self):
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
                self.api_manager.search_tags(self.site, self.query, limit=self.limit), loop
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
            self.tags_ready.emit(results)
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
