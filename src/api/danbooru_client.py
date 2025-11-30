# -*- coding: utf-8 -*-
"""
Danbooru API客户端
"""

from typing import Dict, List, Any, Optional
from .base_client import BaseAPIClient

class DanbooruClient(BaseAPIClient):
    """Danbooru API客户端"""
    
    def __init__(self, username: str = "", api_key: str = ""):
        super().__init__("https://danbooru.donmai.us")
        self.username = username
        self.api_key = api_key
    
    def _get_auth_params(self) -> Dict[str, str]:
        """获取认证参数（用于查询参数）"""
        if self.username and self.api_key:
            return {
                'login': self.username,
                'api_key': self.api_key
            }
        return {}
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取HTTP Basic Authentication头"""
        if self.username and self.api_key:
            import base64
            credentials = f"{self.username}:{self.api_key}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            return {
                'Authorization': f'Basic {encoded_credentials}'
            }
        return {}

    async def count(self, tags: str) -> int:
        """获取符合条件的总帖子数（用于准确分页）。
        优先使用 /counts/posts.json，失败时回退尝试 /posts/count.json。
        返回 -1 表示未知或接口不可用。
        """
        params = {
            'tags': tags,
            **self._get_auth_params()
        }
        try:
            # 首选 counts 接口
            resp = await self.get('/counts/posts.json', params=params, headers=self._get_auth_headers())
            # 期望结构: {"counts": {"posts": <int>}}
            if isinstance(resp, dict):
                counts = resp.get('counts') or resp
                value = counts.get('posts') if isinstance(counts, dict) else None
                if isinstance(value, int) and value >= 0:
                    return value
        except Exception:
            pass
        # 回退：/posts/count.json?tags=...
        try:
            resp2 = await self.get('/posts/count.json', params=params, headers=self._get_auth_headers())
            # 期望结构: {"count": <int>} 或直接是整数
            if isinstance(resp2, dict):
                value = resp2.get('count')
                if isinstance(value, int) and value >= 0:
                    return value
            elif isinstance(resp2, int) and resp2 >= 0:
                return resp2
        except Exception:
            pass
        return -1
    
    async def search(self, tags: str, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索图片"""
        params = {
            'tags': tags,
            'page': page,
            'limit': min(limit, 200),  # Danbooru限制最大200
            **self._get_auth_params()
        }
        
        try:
            response = await self.get('/posts.json', params=params, headers=self._get_auth_headers())
            
            if isinstance(response, list):
                return [self.format_image_data(item) for item in response]
            else:
                return []
                
        except Exception as e:
            print(f"Danbooru搜索失败: {e}")
            return []
    
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """获取单个帖子详情"""
        params = self._get_auth_params()
        
        try:
            response = await self.get(f'/posts/{post_id}.json', params=params, headers=self._get_auth_headers())
            return self.format_image_data(response)
        except Exception as e:
            print(f"获取Danbooru帖子失败: {e}")
            return {}
    
    async def get_favorites(self, user_id: Optional[str] = None, page: int = 1, limit: int = 40) -> List[Dict[str, Any]]:
        """获取收藏夹"""
        if not self.username:
            return []
        
        target_user = user_id or self.username
        params = {
            'search[user_name]': target_user,
            'page': page,
            'limit': limit,
            **self._get_auth_params()
        }
        
        try:
            response = await self.get('/favorites.json', params=params)
            
            if isinstance(response, list):
                post_ids = [str(item['post_id']) for item in response if 'post_id' in item]
                if not post_ids:
                    return []
                import asyncio
                cfg_limit = max(1, min(8, limit))
                sem = asyncio.Semaphore(cfg_limit)
                async def fetch_one(pid: str):
                    async with sem:
                        try:
                            return await self.get_post(pid)
                        except Exception:
                            return {}
                tasks = [fetch_one(pid) for pid in post_ids]
                results = await asyncio.gather(*tasks, return_exceptions=False)
                return [r for r in results if isinstance(r, dict) and r]
            else:
                return []
                
        except Exception as e:
            print(f"获取Danbooru收藏夹失败: {e}")
            return []

    async def add_favorite(self, post_id: str) -> bool:
        """添加收藏：POST /favorites.json {post_id} 需要认证"""
        auth_headers = self._get_auth_headers()
        if not auth_headers:
            return False
        try:
            payload = {'post_id': post_id}
            resp = await self.post_form('/favorites.json', data=payload, headers=auth_headers)
            # 成功通常返回收藏记录，简单判断有 post_id 即认为成功
            if isinstance(resp, dict):
                return True
            return bool(resp)
        except Exception as e:
            return False

    async def remove_favorite(self, post_id: str) -> bool:
        """移除收藏：DELETE /favorites/{post_id}.json 需要认证"""
        auth_headers = self._get_auth_headers()
        if not auth_headers:
            return False

    async def get_tags(self, limit: int = 1000) -> List[Dict[str, Any]]:
        params = {
            'search[order]': 'count',
            'limit': min(max(1, limit), 1000),
            **self._get_auth_params()
        }
        try:
            resp = await self.get('/tags.json', params=params, headers=self._get_auth_headers())
            if isinstance(resp, list):
                out = []
                for t in resp:
                    name = t.get('name') or ''
                    cnt = t.get('post_count') or 0
                    cat = t.get('category') if 'category' in t else None
                    out.append({'name': name, 'count': int(cnt or 0), 'type': cat})
                return out
        except Exception:
            pass
        return []

    async def search_tags(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        q = (query or '').strip()
        if not q:
            return []
        # 先试 /tag_autocomplete.json
        try:
            ac1 = await self.get('/tag_autocomplete.json', params={'query': q, 'limit': min(max(1, limit), 1000)}, headers=self._get_auth_headers())
            if isinstance(ac1, list) and ac1:
                out = []
                for t in ac1:
                    name = t.get('name') or t.get('value') or ''
                    cnt = t.get('post_count') or t.get('category_count') or 0
                    cat = None
                    if name:
                        out.append({'name': name, 'count': int(cnt or 0), 'type': cat})
                if out:
                    return out
        except Exception:
            pass
        # 再试 /autocomplete.json （新版接口）
        try:
            ac2 = await self.get('/autocomplete.json', params={'search[query]': q, 'search[type]': 'tag', 'limit': min(max(1, limit), 1000)}, headers=self._get_auth_headers())
            if isinstance(ac2, list) and ac2:
                out = []
                for t in ac2:
                    name = t.get('value') or t.get('label') or ''
                    cnt = t.get('post_count') or t.get('category_count') or 0
                    cat = None
                    if name:
                        out.append({'name': name, 'count': int(cnt or 0), 'type': cat})
                if out:
                    return out
        except Exception:
            pass
        # 回退到 tags.json 的模糊匹配（不按分类，统一合并）
        out_all = []
        try:
            params = {
                'search[name_or_alias_matches]': f'*{q}*',
                'search[hide_empty]': 'true',
                'search[order]': 'count',
                'limit': min(max(1, limit), 1000),
                **self._get_auth_params()
            }
            resp = await self.get('/tags.json', params=params, headers=self._get_auth_headers())
            if isinstance(resp, list):
                for t in resp:
                    name = t.get('name') or ''
                    cnt = t.get('post_count') or 0
                    if name:
                        out_all.append({'name': name, 'count': int(cnt or 0), 'type': None})
            # 去重并返回
            seen = set()
            uniq = []
            for t in out_all:
                n = t['name']
                if n not in seen:
                    uniq.append(t)
                    seen.add(n)
            return uniq[:limit]
        except Exception:
            pass
        return []
        try:
            # Danbooru使用 DELETE /favorites/{post_id}.json 端点
            resp = await self.delete(f'/favorites/{post_id}.json', headers=auth_headers)
            return True
        except Exception as e:
            # 回退：某些实现返回错误时仍删除成功，尝试查询判断，这里简单返回False
            return False
    
    def format_image_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化图片数据为统一格式"""
        if not raw_data:
            return {}
        
        # 获取图片URL
        file_url = raw_data.get('file_url', '')
        if not file_url and 'large_file_url' in raw_data:
            file_url = raw_data['large_file_url']
        
        # 获取预览图URL
        preview_url = raw_data.get('preview_file_url', '')
        if not preview_url and 'large_file_url' in raw_data:
            preview_url = raw_data['large_file_url']

        # Danbooru部分URL可能为相对路径，补全为绝对路径
        def _abs(u: str) -> str:
            if isinstance(u, str) and u.startswith('/'):
                return f"https://danbooru.donmai.us{u}"
            return u
        file_url = _abs(file_url)
        preview_url = _abs(preview_url)

        # 组装分组标签详情（便于查看器展示）
        tag_details = {
            'general': raw_data.get('tag_string_general', '').split(),
            'artist': raw_data.get('tag_string_artist', '').split(),
            'character': raw_data.get('tag_string_character', '').split(),
            'copyright': raw_data.get('tag_string_copyright', '').split(),
            'meta': raw_data.get('tag_string_meta', '').split(),
        }
        # 合并所有标签形成简单列表（用于数据库和网格显示）
        all_tags = raw_data.get('tag_string', '').split()
        
        return {
            'id': str(raw_data.get('id', '')),
            'title': f"Danbooru #{raw_data.get('id', '')}",
            'tags': all_tags,
            'tag_details': tag_details,
            'rating': raw_data.get('rating', 'q'),
            'score': raw_data.get('score', 0),
            'file_url': file_url,
            'preview_url': preview_url,
            'thumbnail_url': _abs(raw_data.get('preview_file_url', '')),
            'width': raw_data.get('image_width', 0),
            'height': raw_data.get('image_height', 0),
            'file_size': raw_data.get('file_size', 0),
            'file_ext': raw_data.get('file_ext', ''),
            'source': raw_data.get('source', ''),
            'created_at': raw_data.get('created_at', ''),
            'uploader': raw_data.get('uploader_name', ''),
            'artist': raw_data.get('tag_string_artist', ''),
            'site': 'danbooru',
            'post_url': f"https://danbooru.donmai.us/posts/{raw_data.get('id', '')}"
        }
