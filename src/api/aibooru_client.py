# -*- coding: utf-8 -*-
"""
Aibooru API客户端（与 Danbooru 完全一致的接口）
"""

from typing import Dict, List, Any, Optional
from .base_client import BaseAPIClient


class AibooruClient(BaseAPIClient):
    """Aibooru API客户端"""

    def __init__(self, username: str = "", api_key: str = ""):
        super().__init__("https://aibooru.online")
        self.username = username
        self.api_key = api_key

    def _get_auth_params(self) -> Dict[str, str]:
        if self.username and self.api_key:
            return {"login": self.username, "api_key": self.api_key}
        return {}

    def _get_auth_headers(self) -> Dict[str, str]:
        if self.username and self.api_key:
            import base64
            credentials = f"{self.username}:{self.api_key}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            return {"Authorization": f"Basic {encoded_credentials}"}
        return {}

    async def count(self, tags: str) -> int:
        params = {"tags": tags, **self._get_auth_params()}
        try:
            resp = await self.get("/counts/posts.json", params=params, headers=self._get_auth_headers())
            if isinstance(resp, dict):
                counts = resp.get("counts") or resp
                value = counts.get("posts") if isinstance(counts, dict) else None
                if isinstance(value, int) and value >= 0:
                    return value
        except Exception:
            pass
        try:
            resp2 = await self.get("/posts/count.json", params=params, headers=self._get_auth_headers())
            if isinstance(resp2, dict):
                value = resp2.get("count")
                if isinstance(value, int) and value >= 0:
                    return value
            elif isinstance(resp2, int) and resp2 >= 0:
                return resp2
        except Exception:
            pass
        return -1

    async def search(self, tags: str, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        params = {"tags": tags, "page": page, "limit": min(limit, 200), **self._get_auth_params()}
        try:
            response = await self.get("/posts.json", params=params, headers=self._get_auth_headers())
            if isinstance(response, list):
                return [self.format_image_data(item) for item in response]
            return []
        except Exception as e:
            print(f"Aibooru搜索失败: {e}")
            return []

    async def get_post(self, post_id: str) -> Dict[str, Any]:
        params = self._get_auth_params()
        try:
            response = await self.get(f"/posts/{post_id}.json", params=params, headers=self._get_auth_headers())
            return self.format_image_data(response)
        except Exception as e:
            print(f"获取Aibooru帖子失败: {e}")
            return {}

    async def get_favorites(self, user_id: Optional[str] = None, page: int = 1, limit: int = 40) -> List[Dict[str, Any]]:
        if not self.username:
            return []
        target_user = user_id or self.username
        params = {"search[user_name]": target_user, "page": page, "limit": limit, **self._get_auth_params()}
        try:
            response = await self.get("/favorites.json", params=params)
            if isinstance(response, list):
                post_ids = [str(item.get("post_id")) for item in response if "post_id" in item]
                if not post_ids:
                    return []
                import asyncio
                sem = asyncio.Semaphore(max(1, min(8, limit)))
                async def fetch_one(pid: str):
                    async with sem:
                        try:
                            return await self.get_post(pid)
                        except Exception:
                            return {}
                tasks = [fetch_one(pid) for pid in post_ids]
                results = await asyncio.gather(*tasks, return_exceptions=False)
                return [r for r in results if isinstance(r, dict) and r]
            return []
        except Exception as e:
            print(f"获取Aibooru收藏夹失败: {e}")
            return []

    async def add_favorite(self, post_id: str) -> bool:
        auth_headers = self._get_auth_headers()
        if not auth_headers:
            return False
        try:
            payload = {"post_id": post_id}
            resp = await self.post_form("/favorites.json", data=payload, headers=auth_headers)
            if isinstance(resp, dict):
                return True
            return bool(resp)
        except Exception:
            return False

    async def remove_favorite(self, post_id: str) -> bool:
        auth_headers = self._get_auth_headers()
        if not auth_headers:
            return False
        try:
            await self.delete(f"/favorites/{post_id}.json", headers=auth_headers)
            return True
        except Exception:
            return False

    def format_image_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_data:
            return {}
        file_url = raw_data.get("file_url", "")
        if not file_url and "large_file_url" in raw_data:
            file_url = raw_data["large_file_url"]
        preview_url = raw_data.get("preview_file_url", "")
        if not preview_url and "large_file_url" in raw_data:
            preview_url = raw_data["large_file_url"]

        def _abs(u: str) -> str:
            if isinstance(u, str) and u.startswith("/"):
                return f"https://aibooru.online{u}"
            return u

        file_url = _abs(file_url)
        preview_url = _abs(preview_url)

        tag_details = {
            "general": raw_data.get("tag_string_general", "").split(),
            "artist": raw_data.get("tag_string_artist", "").split(),
            "character": raw_data.get("tag_string_character", "").split(),
            "copyright": raw_data.get("tag_string_copyright", "").split(),
            "meta": raw_data.get("tag_string_meta", "").split(),
        }
        all_tags = raw_data.get("tag_string", "").split()

        return {
            "id": str(raw_data.get("id", "")),
            "title": f"Aibooru #{raw_data.get('id', '')}",
            "tags": all_tags,
            "tag_details": tag_details,
            "rating": raw_data.get("rating", "q"),
            "score": raw_data.get("score", 0),
            "file_url": file_url,
            "preview_url": preview_url,
            "thumbnail_url": _abs(raw_data.get("preview_file_url", "")),
            "width": raw_data.get("image_width", 0),
            "height": raw_data.get("image_height", 0),
            "file_size": raw_data.get("file_size", 0),
            "file_ext": raw_data.get("file_ext", ""),
            "source": raw_data.get("source", ""),
            "created_at": raw_data.get("created_at", ""),
            "uploader": raw_data.get("uploader_name", ""),
            "artist": raw_data.get("tag_string_artist", ""),
            "site": "aibooru",
            "post_url": f"https://aibooru.online/posts/{raw_data.get('id', '')}"
        }

