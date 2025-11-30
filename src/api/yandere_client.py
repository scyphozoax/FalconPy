# -*- coding: utf-8 -*-
"""
Yande.re API客户端
"""

from typing import Dict, List, Any
from .base_client import BaseAPIClient
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class YandereClient(BaseAPIClient):
    """Yande.re API客户端"""
    
    def __init__(self, username: str = "", password: str = "", api_key: str = ""):
        super().__init__("https://yande.re")
        self.username = username
        self.password = password
        self.api_key = api_key
    
    async def search(self, tags: str, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            json_resp = await self.get('/post.json', params={'tags': tags or '', 'page': page, 'limit': limit})
            if isinstance(json_resp, list) and json_resp:
                return [self.format_image_data(item) for item in json_resp]
        except Exception:
            pass
        try:
            response = await self.get('/post', params={'page': page, 'tags': tags or ''})
            if isinstance(response, dict) and 'content' in response:
                html = response['content']
                return self._parse_list_html(html, limit)
            return []
        except Exception as e:
            print(f"Yande.re搜索失败: {e}")
            return []
    
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """获取单个帖子详情"""
        params = {
            'tags': f'id:{post_id}'
        }
        
        try:
            response = await self.get('/post.json', params=params)
            
            if isinstance(response, list) and response:
                return self.format_image_data(response[0])
            else:
                return {}
                
        except Exception as e:
            print(f"获取Yande.re帖子失败: {e}")
            return {}
    
    def format_image_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化图片数据为统一格式"""
        if not raw_data:
            return {}
        
        # Yande.re的字段映射（与Konachan类似）
        file_url = raw_data.get('file_url', '')
        sample_url = raw_data.get('sample_url', file_url)
        preview_url = raw_data.get('preview_url', '')
        
        return {
            'id': str(raw_data.get('id', '')),
            'title': f"Yande.re #{raw_data.get('id', '')}",
            'tags': raw_data.get('tags', '').split(),
            'rating': raw_data.get('rating', 's'),
            'score': raw_data.get('score', 0),
            'file_url': file_url,
            'preview_url': sample_url,
            'thumbnail_url': preview_url,
            'width': raw_data.get('width', 0),
            'height': raw_data.get('height', 0),
            'file_size': raw_data.get('file_size', 0),
            'file_ext': file_url.split('.')[-1] if file_url else '',
            'source': raw_data.get('source', ''),
            'created_at': str(raw_data.get('created_at', '')),
            'uploader': raw_data.get('author', ''),
            'site': 'yandere',
            'post_url': f"https://yande.re/post/show/{raw_data.get('id', '')}"
        }

    def _parse_list_html(self, html: str, limit: int = 20) -> List[Dict[str, Any]]:
        """解析 Yande.re 列表页 HTML，提取基本图片信息（缩略图与帖子链接）。"""
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')

        results: List[Dict[str, Any]] = []
        try:
            anchors = soup.select('ul#post-list-posts a.thumb, a[href*="/post/show/"]')
        except Exception:
            anchors = soup.find_all('a')

        base = 'https://yande.re/'

        for a in anchors:
            href = a.get('href') or ''
            if '/post/show/' not in href:
                continue
            post_id = ''
            try:
                path = urlparse(href).path
                post_id = path.strip('/').split('/')[-1]
            except Exception:
                post_id = ''
            if not post_id:
                continue

            img = a.find('img') if hasattr(a, 'find') else None
            thumb = ''
            if img:
                thumb = (
                    img.get('data-preview-url') or img.get('data-src') or img.get('data-original') or img.get('src') or ''
                )
            if thumb.startswith('//'):
                thumb = 'https:' + thumb
            elif thumb.startswith('/'):
                thumb = urljoin(base, thumb)

            tags = []
            rating = 'q'
            score = 0
            data_tags = a.get('data-tags') or ''
            if isinstance(data_tags, str) and data_tags:
                tags = data_tags.split()
            if img and not tags:
                alt_tags = img.get('alt') or ''
                if isinstance(alt_tags, str) and alt_tags:
                    tags = alt_tags.split()
            r = a.get('data-rating') or ''
            if isinstance(r, str) and r:
                rating = r
            li = getattr(a, 'parent', None)
            try:
                classes = li.get('class') if li else []
                if isinstance(classes, list):
                    if 'rating-s' in classes:
                        rating = 's'
                    elif 'rating-q' in classes:
                        rating = 'q'
                    elif 'rating-e' in classes:
                        rating = 'e'
            except Exception:
                pass
            try:
                ds = a.get('data-score')
                if ds is not None:
                    score = int(ds)
            except Exception:
                score = 0

            post_url = urljoin(base, href)

            item = {
                'id': str(post_id),
                'title': f"Yande.re #{post_id}",
                'tags': tags,
                'rating': rating,
                'score': score,
                'file_url': '',
                'preview_url': thumb or '',
                'thumbnail_url': thumb or '',
                'width': 0,
                'height': 0,
                'file_size': 0,
                'file_ext': '',
                'source': '',
                'created_at': '',
                'uploader': '',
                'site': 'yandere',
                'post_url': post_url,
            }
            results.append(item)
            if len(results) >= limit:
                break

        return results

    async def count(self, tags: str) -> int:
        try:
            resp = await self.get('/post', params={'page': 1, 'tags': tags or ''})
            if not isinstance(resp, dict) or 'content' not in resp:
                return -1
            html = resp['content']
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception:
                soup = BeautifulSoup(html, 'html.parser')
            try:
                anchors = soup.select('ul#post-list-posts a.thumb, a[href*="/post/show/"]')
            except Exception:
                anchors = soup.find_all('a')
            cnt = 0
            for a in anchors:
                href = a.get('href') or ''
                if '/post/show/' in href:
                    cnt += 1
            per_page = cnt
            max_page = 1
            pages = []
            for p in soup.select('div.pagination a'):
                href = p.get('href') or ''
                if 'page=' in href:
                    try:
                        q = href.split('page=')[-1]
                        num = int(''.join([c for c in q if c.isdigit()]))
                        pages.append(num)
                    except Exception:
                        pass
            if pages:
                max_page = max(pages)
            if per_page > 0 and max_page > 0:
                return per_page * max_page
            return -1
        except Exception:
            return -1

    async def get_tags(self, limit: int = 1000) -> List[Dict[str, Any]]:
        try:
            resp = await self.get('/tag.json', params={'order': 'count', 'limit': min(max(1, limit), 1000)})
            if isinstance(resp, list):
                out = []
                for t in resp:
                    name = t.get('name') or ''
                    cnt = t.get('count') or 0
                    typ = t.get('type') if 'type' in t else None
                    out.append({'name': name, 'count': int(cnt or 0), 'type': typ})
                return out
        except Exception:
            pass
        return []

    async def search_tags(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        q = (query or '').strip()
        if not q:
            return []
        try:
            resp = await self.get('/tag.json', params={'name': f'{q}*', 'order': 'name', 'limit': min(max(1, limit), 1000)})
            if isinstance(resp, list):
                out = []
                for t in resp:
                    name = t.get('name') or ''
                    cnt = t.get('count') or 0
                    typ = t.get('type') if 'type' in t else None
                    out.append({'name': name, 'count': int(cnt or 0), 'type': typ})
                return out
        except Exception:
            pass
        return []
