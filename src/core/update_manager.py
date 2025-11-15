import json
import re
from typing import Dict, Optional, Any, List
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
        source = (self.config.get('updates.source', 'json') or 'json').strip().lower()
        channel = self.config.get('updates.channel', 'stable')
        try:
            if source == 'github':
                repo = self.config.get('updates.github_repo', '').strip()
                if not repo:
                    return {"has_update": False, "latest_version": None, "download_url": None, "notes_url": None, "message": "未配置GitHub仓库"}
                info = self._github_fetch(repo, channel)
                latest = info.get('version')
                dl = info.get('download_url')
                notes = info.get('notes_url')
            else:
                feed_url = self.config.get('updates.feed_url', '').strip()
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

    def _github_fetch(self, repo: str, channel: str) -> Dict[str, Optional[str]]:
        headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'FalconPy-Updater'
        }
        if channel == 'stable':
            url = f'https://api.github.com/repos/{repo}/releases/latest'
            r = requests.get(url, headers=headers, timeout=8)
            r.raise_for_status()
            rel = r.json()
            tag = rel.get('tag_name') or ''
            ver = tag.lstrip('vV') if tag else None
            assets = rel.get('assets') or []
            dl = self._pick_asset(assets) or rel.get('html_url')
            notes = rel.get('html_url')
            return {"version": ver, "download_url": dl, "notes_url": notes}
        else:
            url = f'https://api.github.com/repos/{repo}/releases'
            r = requests.get(url, headers=headers, timeout=8)
            r.raise_for_status()
            items = r.json() if isinstance(r.json(), list) else []
            beta = next((x for x in items if bool(x.get('prerelease'))), None)
            if not beta:
                return {"version": None, "download_url": None, "notes_url": None}
            tag = beta.get('tag_name') or ''
            ver = tag.lstrip('vV') if tag else None
            assets = beta.get('assets') or []
            dl = self._pick_asset(assets) or beta.get('html_url')
            notes = beta.get('html_url')
            return {"version": ver, "download_url": dl, "notes_url": notes}

    def _pick_asset(self, assets: List[Dict[str, Any]]) -> Optional[str]:
        names = [a.get('name','') for a in assets]
        for a in assets:
            n = (a.get('name') or '').lower()
            if n.endswith('.msi') or n.endswith('.exe'):
                return a.get('browser_download_url')
        if assets:
            return assets[0].get('browser_download_url')
        return None