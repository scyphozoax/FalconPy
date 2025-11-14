# -*- coding: utf-8 -*-
"""
在线收藏操作线程：在后台执行添加/移除收藏，避免阻塞 UI。
目前支持 Danbooru。
"""

from PyQt6.QtCore import QThread, pyqtSignal


class OnlineFavoriteOpThread(QThread):
    finished_ok = pyqtSignal(bool)  # True 表示成功
    error = pyqtSignal(str)

    def __init__(self, api_manager, site: str, op: str, post_id: str):
        super().__init__()
        self.api_manager = api_manager
        self.site = site
        self.op = op  # 'add' | 'remove'
        self.post_id = post_id
        self._loop = None

    def run(self):
        import asyncio
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def _do():
                if self.op == 'add':
                    return await self.api_manager.add_favorite(self.site, self.post_id)
                elif self.op == 'remove':
                    return await self.api_manager.remove_favorite(self.site, self.post_id)
                return False

            ok = self._loop.run_until_complete(_do())
            self.finished_ok.emit(bool(ok))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            try:
                if self._loop:
                    self._loop.run_until_complete(asyncio.sleep(0))
                    self._loop.close()
            except Exception:
                pass
            self._loop = None