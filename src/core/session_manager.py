# -*- coding: utf-8 -*-
"""
会话管理器
用于管理用户登录状态和会话信息
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib

class SessionManager:
    """会话管理器"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            from .config import Config
            config_dir = str(Config().app_dir)
        
        self.config_dir = config_dir
        self.sessions_file = os.path.join(config_dir, "sessions.json")
        self.sessions = {}
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载现有会话
        self.load_sessions()
    
    def load_sessions(self):
        """加载会话数据"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = data.get('sessions', {})
                    
                # 清理过期会话
                self.cleanup_expired_sessions()
        except Exception as e:
            print(f"加载会话失败: {e}")
            self.sessions = {}
    
    def save_sessions(self):
        """保存会话数据"""
        try:
            data = {
                'sessions': self.sessions,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存会话失败: {e}")
    
    def create_session(self, site: str, user_info: Dict, credentials: Dict = None, 
                      remember: bool = False):
        """创建新会话"""
        session_id = self._generate_session_id(site, user_info.get('username', ''))
        
        # 计算过期时间
        if remember:
            expires_at = datetime.now() + timedelta(days=30)  # 记住30天
        else:
            expires_at = datetime.now() + timedelta(hours=24)  # 默认24小时
        
        session_data = {
            'session_id': session_id,
            'site': site,
            'user_info': user_info,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'remember': remember,
            'last_accessed': datetime.now().isoformat()
        }
        
        # 如果选择记住登录信息，保存加密的凭据
        if remember and credentials:
            session_data['credentials'] = self._encrypt_credentials(credentials)
        
        self.sessions[f"{site}_{user_info.get('user_id', user_info.get('username', ''))}"] = session_data
        self.save_sessions()
        
        return session_id
    
    def get_session(self, site: str, user_id: str = None) -> Optional[Dict]:
        """获取会话信息"""
        if user_id:
            key = f"{site}_{user_id}"
        else:
            # 查找该网站的任何有效会话
            for key, session in self.sessions.items():
                if session['site'] == site and not self._is_session_expired(session):
                    return session
            return None
        
        session = self.sessions.get(key)
        if session and not self._is_session_expired(session):
            # 更新最后访问时间
            session['last_accessed'] = datetime.now().isoformat()
            self.save_sessions()
            return session
        
        return None
    
    def update_session(self, site: str, user_id: str, updates: Dict):
        """更新会话信息"""
        key = f"{site}_{user_id}"
        if key in self.sessions:
            self.sessions[key].update(updates)
            self.sessions[key]['last_accessed'] = datetime.now().isoformat()
            self.save_sessions()
    
    def delete_session(self, site: str, user_id: str = None):
        """删除会话"""
        if user_id:
            key = f"{site}_{user_id}"
            if key in self.sessions:
                del self.sessions[key]
                self.save_sessions()
        else:
            # 删除该网站的所有会话
            keys_to_delete = [key for key, session in self.sessions.items() 
                            if session['site'] == site]
            for key in keys_to_delete:
                del self.sessions[key]
            if keys_to_delete:
                self.save_sessions()
    
    def get_all_active_sessions(self) -> Dict[str, Dict]:
        """获取所有活跃会话"""
        active_sessions = {}
        for key, session in self.sessions.items():
            if not self._is_session_expired(session):
                active_sessions[key] = session
        return active_sessions
    
    def get_sites_with_sessions(self) -> list:
        """获取有活跃会话的网站列表"""
        sites = set()
        for session in self.sessions.values():
            if not self._is_session_expired(session):
                sites.add(session['site'])
        return list(sites)
    
    def is_logged_in(self, site: str) -> bool:
        """检查是否已登录到指定网站"""
        return self.get_session(site) is not None
    
    def get_user_info(self, site: str) -> Optional[Dict]:
        """获取用户信息"""
        session = self.get_session(site)
        return session.get('user_info') if session else None
    
    def get_credentials(self, site: str, user_id: str) -> Optional[Dict]:
        """获取保存的凭据（如果用户选择了记住登录）"""
        session = self.get_session(site, user_id)
        if session and session.get('remember') and 'credentials' in session:
            return self._decrypt_credentials(session['credentials'])
        return None
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        expired_keys = []
        for key, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.sessions[key]
        
        if expired_keys:
            self.save_sessions()
    
    def _is_session_expired(self, session: Dict) -> bool:
        """检查会话是否过期"""
        try:
            expires_at = datetime.fromisoformat(session['expires_at'])
            return datetime.now() > expires_at
        except:
            return True
    
    def _generate_session_id(self, site: str, username: str) -> str:
        """生成会话ID"""
        data = f"{site}_{username}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _encrypt_credentials(self, credentials: Dict) -> str:
        """加密凭据（简单的base64编码，实际应用中应使用更安全的加密）"""
        import base64
        data = json.dumps(credentials)
        return base64.b64encode(data.encode()).decode()
    
    def _decrypt_credentials(self, encrypted_data: str) -> Dict:
        """解密凭据"""
        import base64
        try:
            data = base64.b64decode(encrypted_data.encode()).decode()
            return json.loads(data)
        except:
            return {}
    
    def logout_all(self):
        """登出所有会话"""
        self.sessions.clear()
        self.save_sessions()
    
    def extend_session(self, site: str, user_id: str, hours: int = 24):
        """延长会话时间"""
        session = self.get_session(site, user_id)
        if session:
            new_expires = datetime.now() + timedelta(hours=hours)
            self.update_session(site, user_id, {
                'expires_at': new_expires.isoformat()
            })