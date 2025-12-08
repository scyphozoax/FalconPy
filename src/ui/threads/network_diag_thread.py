# -*- coding: utf-8 -*-
"""
网络诊断线程：用于检测各站点的连通性并给出详细信息。
"""

from PyQt6.QtCore import QThread, pyqtSignal
import asyncio
import aiohttp
import threading
import concurrent.futures
import socket
import time
from typing import Tuple, Optional
from ...core.config import Config


def _site_probe_target(site: str) -> Tuple[str, str]:
    """返回 (主机, 诊断URL)。均为无需登录的最小可用接口。
    """
    s = (site or '').strip().lower()
    if s == 'danbooru':
        return ('danbooru.donmai.us', 'https://danbooru.donmai.us/posts.json?limit=1')
    if s == 'aibooru':
        return ('aibooru.online', 'https://aibooru.online/posts.json?limit=1')
    if s == 'konachan':
        return ('konachan.net', 'https://konachan.net/post.json?limit=1')
    if s in ('yandere', 'yande.re', 'yande'):  # 兼容不同拼写
        return ('yande.re', 'https://yande.re/post.json?limit=1')
    # 默认回退到 Danbooru
    return ('danbooru.donmai.us', 'https://danbooru.donmai.us/posts.json?limit=1')


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

class NetworkDiagnosticsThread(QThread):
    """执行单站点网络诊断的线程。"""

    success = pyqtSignal(str)  # 诊断详情
    failed = pyqtSignal(str)   # 错误详情

    def __init__(self, site: str):
        super().__init__()
        self.site = site

    def run(self):
        cfg = Config()
        timeout_seconds = int(cfg.get('network.timeout', 30) or 30)
        proxy_url: Optional[str] = None
        if cfg.get('network.use_proxy', False):
            host = cfg.get('network.proxy_host', '')
            port = cfg.get('network.proxy_port', 0)
            username = cfg.get('network.proxy_username', '')
            password = cfg.get('network.proxy_password', '')
            if host and port:
                if username and password:
                    proxy_url = f"http://{username}:{password}@{host}:{port}"
                else:
                    proxy_url = f"http://{host}:{port}"

        host, url = _site_probe_target(self.site)
        details = []
        details.append(f"站点: {self.site}")
        details.append(f"目标: {url}")
        details.append(f"使用代理: {'是' if proxy_url else '否'}{(' ' + proxy_url) if proxy_url else ''}")
        details.append(f"超时: {timeout_seconds}s")

        # 步骤1：DNS解析
        try:
            info = socket.getaddrinfo(host, None)
            ip_list = sorted({i[4][0] for i in info if i and i[4]})
            ip_text = ', '.join(ip_list[:3]) + ("..." if len(ip_list) > 3 else "")
            details.append(f"DNS解析: 成功 -> {ip_text}")
        except Exception as e:
            details.append(f"DNS解析失败: {type(e).__name__} - {e}")
            self.failed.emit("\n".join(details))
            return

        # 步骤2：HTTP访问
        async def _http_probe():
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(trust_env=True) as session:
                t0 = time.perf_counter()
                async with session.get(url, timeout=timeout, proxy=proxy_url) as resp:
                    content_type = resp.headers.get('content-type', '')
                    # 尝试读取少量文本以验证响应（不强制JSON）
                    text = await resp.text()
                    elapsed = time.perf_counter() - t0
                    details.append(f"HTTP状态: {resp.status} {resp.reason}")
                    details.append(f"内容类型: {content_type}")
                    details.append(f"响应大小: {len(text)}")
                    details.append(f"耗时: {elapsed:.3f}s")

        loop = _ensure_shared_loop()
        try:
            fut = asyncio.run_coroutine_threadsafe(_http_probe(), loop)
            fut.result()
            self.success.emit("\n".join(details))
        except aiohttp.ClientConnectorCertificateError as e:
            details.append(f"TLS证书错误: {type(e).__name__} - {e}")
            self.failed.emit("\n".join(details))
        except aiohttp.ClientConnectorError as e:
            details.append(f"连接错误: {type(e).__name__} - {e}")
            self.failed.emit("\n".join(details))
        except aiohttp.ClientResponseError as e:
            details.append(f"响应错误: {type(e).__name__} - {e}")
            self.failed.emit("\n".join(details))
        except concurrent.futures.TimeoutError as e:
            details.append(f"请求超时: {type(e).__name__} - {e}")
            self.failed.emit("\n".join(details))
        except Exception as e:
            details.append(f"未知错误: {type(e).__name__} - {e}")
            self.failed.emit("\n".join(details))
