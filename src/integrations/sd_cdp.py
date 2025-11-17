# -*- coding: utf-8 -*-
import os
import time
import json
import subprocess
from typing import Optional, Tuple

import requests


def is_sd_running(sd_url: str, timeout: float = 1.5) -> bool:
    try:
        r = requests.get(sd_url.rstrip('/') + '/sdapi/v1/options', timeout=timeout)
        return r.status_code == 200
    except Exception:
        try:
            r = requests.get(sd_url.rstrip('/'), timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False


def _get_cdp_targets(port: int) -> list:
    for path in ('/json/list', '/json'):
        try:
            r = requests.get(f'http://127.0.0.1:{port}{path}', timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return []


def _find_sd_target(sd_url: str, targets: list) -> Optional[dict]:
    url = sd_url.rstrip('/')
    for t in targets:
        try:
            u = str(t.get('url', '') or '')
            title = str(t.get('title', '') or '')
            if u.startswith(url) or 'Stable Diffusion' in title:
                if t.get('type') == 'page' and t.get('webSocketDebuggerUrl'):
                    return t
        except Exception:
            pass
    return None


def _open_sd_tab(port: int, sd_url: str) -> Optional[dict]:
    for path in (f'/json/new?{sd_url}', '/json/new'):
        try:
            r = requests.get(f'http://127.0.0.1:{port}{path}', timeout=2.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def _browser_path(browser: str) -> Optional[str]:
    browser = (browser or 'edge').lower()
    candidates = []
    if browser == 'edge':
        candidates = [
            os.path.expandvars(r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe'),
            os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
        ]
    else:
        candidates = [
            os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _ensure_browser(browser: str, port: int, sd_url: Optional[str] = None) -> bool:
    targets = _get_cdp_targets(port)
    if targets:
        return True
    exe = _browser_path(browser)
    if not exe:
        return False
    user_dir = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), f'{browser}_sd_user')
    try:
        os.makedirs(user_dir, exist_ok=True)
    except Exception:
        pass
    try:
        args = [
            exe,
            f'--remote-debugging-port={port}',
            f'--user-data-dir={user_dir}',
            '--remote-allow-origins=*'
        ]
        if sd_url:
            args.append(sd_url)
        subprocess.Popen(args)
    except Exception:
        return False
    for _ in range(20):
        time.sleep(0.2)
        if _get_cdp_targets(port):
            return True
    return False


def _cdp_eval(ws_url: str, expression: str, origin_hint: Optional[str] = None, await_promise: bool = False) -> Tuple[bool, str]:
    try:
        from websocket import create_connection
    except Exception:
        return False, '缺少依赖：请安装 websocket-client'
    for attempt in range(5):
        try:
            kwargs = {'timeout': 3.0}
            if origin_hint:
                kwargs['origin'] = origin_hint
            ws = create_connection(ws_url, **kwargs)
            msg_id = 1
            def send(method: str, params: dict):
                nonlocal msg_id
                payload = json.dumps({'id': msg_id, 'method': method, 'params': params})
                ws.send(payload)
                msg_id += 1
                return json.loads(ws.recv())
            send('Page.bringToFront', {})
            res = send('Runtime.evaluate', {
                'expression': expression,
                'returnByValue': True,
                'awaitPromise': bool(await_promise),
            })
            ws.close()
            if res.get('error'):
                err = str(res.get('error'))
                if 'Execution context was destroyed' in err or 'Cannot find context with specified id' in err:
                    import time as _t
                    _t.sleep(0.6)
                    continue
                return False, err
            return True, 'ok'
        except Exception as e:
            msg = str(e)
            if '403' in msg or 'Rejected an incoming WebSocket connection' in msg:
                return False, 'CDP连接失败：请以 --remote-allow-origins=* 启动浏览器（Edge/Chrome），或允许 http://127.0.0.1:9222'
            import time as _t
            _t.sleep(0.4)
            continue
    return False, '执行环境尚未就绪，请稍后重试'


def send_prompt_via_cdp(prompt: str, sd_url: str, browser: str = 'edge', port: int = 9222, attach_only: bool = False) -> Tuple[bool, str]:
    targets = _get_cdp_targets(port)
    t = _find_sd_target(sd_url, targets)
    if not t:
        if not targets:
            if attach_only:
                return False, '未检测到浏览器调试端口，请以 --remote-debugging-port=9222 启动浏览器'
            ok = _ensure_browser(browser, port, sd_url)
            if not ok:
                return False, '未找到可用浏览器，或无法开启调试端口'
        deadline = time.time() + 8.0
        while not t and time.time() < deadline:
            time.sleep(0.3)
            targets = _get_cdp_targets(port)
            t = _find_sd_target(sd_url, targets)
        if not t:
            new_t = _open_sd_tab(port, sd_url)
            time.sleep(0.6)
            targets = _get_cdp_targets(port)
            t = _find_sd_target(sd_url, targets)
            if not t and new_t and new_t.get('webSocketDebuggerUrl'):
                ws = new_t['webSocketDebuggerUrl']
                _cdp_bring_and_navigate(ws, sd_url, origin_hint=f'http://127.0.0.1:{port}')
                time.sleep(0.8)
                targets = _get_cdp_targets(port)
                t = _find_sd_target(sd_url, targets)
            if not t:
                return False, '无法打开 SD 标签页'
    ws_url = t.get('webSocketDebuggerUrl')
    if not ws_url:
        return False, '未发现调试WebSocket地址'
    jstext = (
        "(async function(){try{const app=(typeof gradioApp==='function'?gradioApp():document);"
        "function find(){return app.querySelector('#txt2img_prompt textarea')||app.querySelector('#txt2img_prompt > label > textarea');}"
        "let ta=find();const deadline=Date.now()+6000;while(!ta && Date.now()<deadline){await new Promise(r=>setTimeout(r,250));ta=find();}"
        "if(!ta){return 'not_found';} ta.value=" + json.dumps(prompt) + ";"
        "ta.dispatchEvent(new Event('input',{bubbles:true})); return 'ok';}catch(e){return 'err:'+e}})()"
    )
    origin = None
    try:
        from urllib.parse import urlparse
        p = urlparse(ws_url)
        origin = f'http://{p.hostname}:{p.port}' if p.hostname and p.port else None
    except Exception:
        origin = f'http://127.0.0.1:{port}'
    ok, msg = _cdp_eval(ws_url, jstext, origin, await_promise=True)
    if ok and msg == 'ok':
        return True, '已写入正向提示词'
    if ok and msg == 'not_found':
        return False, '未找到提示词输入框'
    return ok, msg


def send_to_sd(prompt: str, cfg) -> Tuple[bool, str]:
    try:
        sd_url = str(cfg.get('sd.url', 'http://127.0.0.1:7860'))
        browser = str(cfg.get('sd.browser', 'edge'))
        port = int(cfg.get('sd.cdp_port', 9222))
        attach_only = bool(cfg.get('sd.attach_only', False))
    except Exception:
        sd_url = 'http://127.0.0.1:7860'
        browser = 'edge'
        port = 9222
        attach_only = False
    if not is_sd_running(sd_url):
        return False, 'Stable Diffusion未启动'
    return send_prompt_via_cdp(prompt, sd_url, browser, port, attach_only)

def _cdp_bring_and_navigate(ws_url: str, url: str, origin_hint: Optional[str] = None) -> Tuple[bool, str]:
    try:
        from websocket import create_connection
    except Exception:
        return False, '缺少依赖：请安装 websocket-client'
    try:
        kwargs = {'timeout': 3.0}
        if origin_hint:
            kwargs['origin'] = origin_hint
        ws = create_connection(ws_url, **kwargs)
        msg_id = 1
        def send(method: str, params: dict):
            nonlocal msg_id
            payload = json.dumps({'id': msg_id, 'method': method, 'params': params})
            ws.send(payload)
            msg_id += 1
            return json.loads(ws.recv())
        send('Page.bringToFront', {})
        res = send('Page.navigate', {'url': url})
        ws.close()
        if res.get('error'):
            return False, str(res.get('error'))
        return True, 'ok'
    except Exception as e:
        return False, f'导航失败: {e}'