# -*- coding: utf-8 -*-
"""
基础API客户端
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from ..core.config import Config

class BaseAPIClient(ABC):
    """基础API客户端抽象类"""
    
    def __init__(self, base_url: str, session: Optional[aiohttp.ClientSession] = None):
        self.base_url = base_url.rstrip('/')
        self.session = session
        self._own_session = session is None
        self._dbg_counter = 0
        
    async def __aenter__(self):
        # 如果没有会话或会话已关闭，则创建新会话
        if self.session is None or getattr(self.session, 'closed', False):
            # 信任系统环境变量中的代理（如 HTTP_PROXY/HTTPS_PROXY）
            self.session = aiohttp.ClientSession(trust_env=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self.session:
            await self.session.close()
            # 关闭后清空引用，避免复用已关闭的会话
            self.session = None
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        # 会话不存在或已关闭时重新创建
        if (self.session is None) or getattr(self.session, 'closed', False):
            # 信任系统环境变量中的代理（如 HTTP_PROXY/HTTPS_PROXY）
            self.session = aiohttp.ClientSession(trust_env=True)
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        # 读取网络设置
        cfg = Config()
        timeout_seconds = int(cfg.get('network.timeout', 30) or 30)
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        proxy_url = None
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

        debug = bool(cfg.get('network.debug', False))
        sample_every = int(cfg.get('network.debug_sample_every', 10) or 10)
        slow_ms = float(cfg.get('network.debug_slow_ms', 800) or 800)
        d_pre = debug and (self._dbg_counter % max(1, sample_every) == 0)
        self._dbg_counter += 1
        if debug:
            try:
                params = kwargs.get('params')
                headers = kwargs.get('headers')
                if d_pre:
                    print(f"[DEBUG] 请求: {method} {url}")
                    if params:
                        print(f"[DEBUG] 参数: {params}")
                    if headers:
                        print(f"[DEBUG] 头部: {list(headers.keys())}")
                    print(f"[DEBUG] 代理: {'启用' if proxy_url else '未启用'} {proxy_url or ''}")
                    print(f"[DEBUG] 超时: {timeout_seconds}s")
            except Exception:
                # 打印调试信息失败不影响主流程
                pass
        
        import time
        retries = 0
        max_retries = int(cfg.get('network.max_retries', 0) or 0)
        last_exc = None
        while True:
            start_ts = time.perf_counter()
            try:
                async with self.session.request(method, url, timeout=timeout, proxy=proxy_url, **kwargs) as response:
                    response.raise_for_status()
                    elapsed = time.perf_counter() - start_ts
                    content_type = response.headers.get('content-type', '')
                    dbg_log = debug and ((elapsed * 1000.0) >= slow_ms or d_pre)
                    if dbg_log:
                        try:
                            print(f"[DEBUG] 响应: {response.status} {response.reason}, 内容类型: {content_type}, 耗时: {elapsed:.3f}s")
                        except Exception:
                            pass
                    if 'application/json' in content_type:
                        data = await response.json()
                        if dbg_log:
                            try:
                                length = len(json.dumps(data))
                                print(f"[DEBUG] JSON长度: {length}")
                            except Exception:
                                pass
                        return data
                    else:
                        text = await response.text()
                        if dbg_log:
                            try:
                                print(f"[DEBUG] 文本长度: {len(text)}")
                            except Exception:
                                pass
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return {'content': text}
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exc = e
                if retries >= max_retries:
                    break
                retries += 1
                backoff = min(1.5 ** retries * 0.2, 3.0)
                if debug:
                    try:
                        print(f"[DEBUG] 重试 {retries}/{max_retries}, 等待 {backoff:.2f}s: {type(e).__name__} - {e}")
                    except Exception:
                        pass
                await asyncio.sleep(backoff)
            except Exception as e:
                last_exc = e
                break
        if isinstance(last_exc, aiohttp.ClientError):
            if debug:
                try:
                    print(f"[DEBUG] ClientError: {type(last_exc).__name__} - {last_exc} | URL: {url}")
                except Exception:
                    pass
            raise APIException(f"请求失败: {last_exc}")
        raise APIException(f"未知错误: {last_exc}")
    
    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """GET请求"""
        return await self._request('GET', endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """POST请求"""
        return await self._request('POST', endpoint, json=data, **kwargs)

    async def post_form(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """POST表单请求"""
        return await self._request('POST', endpoint, data=data, **kwargs)

    async def delete(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """DELETE请求"""
        return await self._request('DELETE', endpoint, params=params, **kwargs)
    
    @abstractmethod
    async def search(self, tags: str, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索图片"""
        pass
    
    @abstractmethod
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """获取单个帖子详情"""
        pass
    
    @abstractmethod
    def format_image_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化图片数据为统一格式"""
        pass

    async def count(self, tags: str) -> int:
        """获取匹配标签的总帖子数（默认不支持，返回 -1 表示未知）。"""
        return -1

class APIException(Exception):
    """API异常类"""
    pass
