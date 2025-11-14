import json
import re
from typing import Dict, Optional
import requests
from .. import __version__

class UpdateManager:
    def __init__(self, config):
        self.config = config

    def _cmp(self, a: str, b: str) -> int:
        def parse(v: str):
            return [int(x) for x in re.findall(r"\d+", v)]
        va = parse(a)
        vb = parse(b)
        for i in range(max(len(va), len(vb))):
            ai = va[i] if i < len(va) else 0
            bi = vb[i] if i < len(vb) else 0
            if ai != bi:
                return 1 if ai > bi else -1
        return 0

    def check_now(self) -> Dict[str, Optional[str]]:
        enabled = bool(self.config.get('updates.enabled', True))
        if not enabled:
            return {"has_update": False, "latest_version": None, "download_url": None, "notes_url": None, "message": "更新检查已禁用"}
        feed_url = self.config.get('updates.feed_url', '')
        channel = self.config.get('updates.channel', 'stable')
        try:
            if not feed_url:
                return {"has_update": False, "latest_version": None, "download_url": None, "notes_url": None, "message": "未配置更新源"}
            resp = requests.get(feed_url, timeout=5)
            resp.raise_for_status()
            data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else json.loads(resp.text)
            entry = data.get(channel) if isinstance(data, dict) else None
            latest = entry.get('version') if isinstance(entry, dict) else None
            dl = entry.get('download_url') if isinstance(entry, dict) else None
            notes = entry.get('notes_url') if isinstance(entry, dict) else None
            cur = __version__
            if latest and self._cmp(latest, cur) > 0:
                return {"has_update": True, "latest_version": latest, "download_url": dl, "notes_url": notes, "message": None}
            return {"has_update": False, "latest_version": cur, "download_url": None, "notes_url": None, "message": "已是最新版本"}
        except Exception as e:
            return {"has_update": False, "latest_version": None, "download_url": None, "notes_url": None, "message": str(e)}