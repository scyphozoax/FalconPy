# -*- coding: utf-8 -*-
"""
API管理器
"""

import asyncio
from typing import Dict, List, Any, Optional
from ..core.config import Config
from .base_client import BaseAPIClient
from .danbooru_client import DanbooruClient
from .konachan_client import KonachanClient
from .yandere_client import YandereClient

class APIManager:
    """API管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化所有API客户端"""
        # Danbooru
        danbooru_config = self.config.get('sites.danbooru', {})
        if danbooru_config.get('enabled', True):
            self.clients['danbooru'] = DanbooruClient(
                username=danbooru_config.get('username', ''),
                api_key=danbooru_config.get('api_key', '')
            )
        
        # Konachan
        konachan_config = self.config.get('sites.konachan', {})
        if konachan_config.get('enabled', True):
            self.clients['konachan'] = KonachanClient(
                username=konachan_config.get('username', ''),
                password=konachan_config.get('password', ''),
                api_key=konachan_config.get('api_key', '')
            )
        
        # Yande.re
        yandere_config = self.config.get('sites.yandere', {})
        if yandere_config.get('enabled', True):
            self.clients['yandere'] = YandereClient(
                username=yandere_config.get('username', ''),
                password=yandere_config.get('password', ''),
                api_key=yandere_config.get('api_key', '')
            )
        
    
    def get_client(self, site_name: str):
        """获取指定网站的API客户端"""
        s = (site_name or '').strip().lower()
        if s in ('yande.re', 'yande', 'yandere'):
            s = 'yandere'
        return self.clients.get(s)
    
    def get_available_sites(self) -> List[str]:
        """获取可用的网站列表"""
        return list(self.clients.keys())

    async def search(self, site_name: str, tags: str, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """在指定网站搜索"""
        client = self.get_client(site_name)
        if not client:
            return []
        
        try:
            return await client.search(tags, page, limit)
        except Exception as e:
            print(f"搜索失败 ({site_name}): {e}")
            return []

    async def count(self, site_name: str, tags: str) -> int:
        """获取指定网站匹配标签的总帖子数，返回 -1 表示未知。"""
        client = self.get_client(site_name)
        if not client:
            return -1
        try:
            if hasattr(client, 'count'):
                return await client.count(tags)
            return -1
        except Exception as e:
            print(f"获取总数失败 ({site_name}): {e}")
            return -1
    
    async def search_all_sites(self, tags: str, page: int = 1, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """在所有网站搜索"""
        tasks = []
        site_names = []
        
        for site_name in self.clients.keys():
            tasks.append(self.search(site_name, tags, page, limit))
            site_names.append(site_name)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            combined_results = {}
            for site_name, result in zip(site_names, results):
                if isinstance(result, Exception):
                    print(f"网站 {site_name} 搜索出错: {result}")
                    combined_results[site_name] = []
                else:
                    combined_results[site_name] = result
            
            return combined_results
            
        except Exception as e:
            print(f"批量搜索失败: {e}")
            return {site: [] for site in site_names}
    
    async def get_post(self, site_name: str, post_id: str) -> Dict[str, Any]:
        """获取指定网站的帖子详情"""
        client = self.get_client(site_name)
        if not client:
            return {}
        
        try:
            return await client.get_post(post_id)
        except Exception as e:
            print(f"获取帖子失败 ({site_name}): {e}")
            return {}

    async def get_tags(self, site_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        client = self.get_client(site_name)
        if not client or not hasattr(client, 'get_tags'):
            return []
        try:
            return await client.get_tags(limit=limit)
        except Exception as e:
            print(f"获取标签失败 ({site_name}): {e}")
            return []

    async def search_tags(self, site_name: str, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        client = self.get_client(site_name)
        if not client or not hasattr(client, 'search_tags'):
            return []
        try:
            return await client.search_tags(query=query, limit=limit)
        except Exception as e:
            print(f"搜索标签失败 ({site_name}): {e}")
            return []
    
    async def get_favorites(self, site_name: str, user_id: Optional[str] = None, page: int = 1, limit: int = 40) -> List[Dict[str, Any]]:
        """获取指定网站的收藏夹"""
        client = self.get_client(site_name)
        if not client or not hasattr(client, 'get_favorites'):
            return []
        
        try:
            return await client.get_favorites(user_id, page=page, limit=limit)
        except Exception as e:
            print(f"获取收藏夹失败 ({site_name}): {e}")
            return []

    async def add_favorite(self, site_name: str, post_id: str) -> bool:
        """添加在线收藏（当前支持 Danbooru）"""
        client = self.get_client(site_name)
        if not client or not hasattr(client, 'add_favorite'):
            return False
        try:
            return await client.add_favorite(post_id)
        except Exception as e:
            print(f"添加在线收藏失败 ({site_name}): {e}")
            return False

    async def remove_favorite(self, site_name: str, post_id: str) -> bool:
        """移除在线收藏（当前支持 Danbooru）"""
        client = self.get_client(site_name)
        if not client or not hasattr(client, 'remove_favorite'):
            return False
        try:
            return await client.remove_favorite(post_id)
        except Exception as e:
            print(f"移除在线收藏失败 ({site_name}): {e}")
            return False
    
    def update_credentials(self, site_name: str, credentials: Dict[str, str]):
        """更新网站认证信息"""
        site_name = site_name.lower()
        if site_name in ('yande.re', 'yande', 'yandere'):
            site_name = 'yandere'
        
        # 更新配置
        for key, value in credentials.items():
            self.config.set(f'sites.{site_name}.{key}', value)
        
        # 重新初始化对应的客户端
        if site_name == 'danbooru':
            self.clients[site_name] = DanbooruClient(
                username=credentials.get('username', ''),
                api_key=credentials.get('api_key', '')
            )
        elif site_name == 'konachan':
            self.clients[site_name] = KonachanClient(
                username=credentials.get('username', ''),
                password=credentials.get('password', ''),
                api_key=credentials.get('api_key', '')
            )
        elif site_name == 'yandere':
            self.clients[site_name] = YandereClient(
                username=credentials.get('username', ''),
                password=credentials.get('password', ''),
                api_key=credentials.get('api_key', '')
            )
        # 移除 Sankaku 的凭据更新逻辑
        
        # 保存配置
        self.config.save_config()

    def shutdown(self):
        try:
            for client in self.clients.values():
                try:
                    sess = getattr(client, 'session', None)
                    if sess and not getattr(sess, 'closed', False):
                        # 安全关闭可能存在的持久会话
                        import asyncio
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(sess.close())
                            loop.close()
                        except Exception:
                            # 回退：直接调度关闭
                            try:
                                asyncio.get_event_loop().run_until_complete(sess.close())
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
        # 关闭共享会话（连接池）
        try:
            BaseAPIClient.close_shared_sessions()
        except Exception:
            pass
