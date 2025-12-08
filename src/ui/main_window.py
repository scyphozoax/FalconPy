# -*- coding: utf-8 -*-
"""
主窗口界面
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QToolBar, QStatusBar, QSplitter, QTabWidget,
                            QComboBox, QLineEdit, QPushButton, QScrollArea,
                            QGridLayout, QLabel, QFrame, QMenuBar, QMenu, QMessageBox, QDialog, QApplication, QProgressDialog, QFileDialog)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QPalette, QColor
import os
import json
from pathlib import Path
import requests

from .widgets.image_grid import ImageGridWidget
from .widgets.thumbnail import ImageThumbnail
from .widgets.site_selector import SiteSelectorWidget
from .dialogs.account_management_dialog import AccountManagementDialog
from .dialogs.about_dialog import AboutDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.download_progress_dialog import DownloadProgressDialog
from .dialogs.batch_download_dialog import BatchDownloadDialog
from .threads.download_queue_thread import DownloadQueueThread, DownloadTask
from .themes.theme_manager import ThemeManager
from .threads.favorites_thread import FavoritesFetchThread
from .threads.tags_fetch_thread import TagsFetchThread
from .threads.tags_query_thread import TagsQueryThread
from .threads.online_favorite_thread import OnlineFavoriteOpThread
from .widgets.tag_suggest import TagSuggest
from .dialogs.favorite_destination_dialog import FavoriteDestinationDialog
from ..core.config import Config
from ..core.database import DatabaseManager
from ..core.session_manager import SessionManager
from ..core.cache_manager import CacheManager
from ..core.i18n import I18n
from ..core.update_manager import UpdateManager
from .threads.update_check_thread import UpdateCheckThread

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化配置和数据库
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager()
        self.theme_manager = ThemeManager()
        
        # 初始化缓存管理器
        cache_dir = self.config.cache_dir
        self.cache_manager = CacheManager(str(cache_dir))
        # 初始化 i18n
        try:
            lang = self.config.get('appearance.language', 'zh_CN')
        except Exception:
            lang = 'zh_CN'
        self.i18n = I18n(lang)
        
        self.api_manager = None
        self.current_search_thread = None
        self.current_fav_thread = None
        self.fav_source = 'local'  # local | online | merge
        self.update_manager = UpdateManager(self.config)
        self.update_timer = None
        self._get_post_threads = []
        self._last_query = ''
        self._last_site = ''
        self._last_page = 1
        self._bg_threads = []
        self._tag_cache = {}
        self._tag_retry = {}
        self._tag_thread = None
        
        # 设置API管理器
        self.setup_api_manager()
        
        # 初始化界面
        self.init_ui()
        self.restore_geometry()
        
        # 应用保存的设置
        self.apply_settings()
        
        # 检查现有会话
        self.check_existing_sessions()
        # 启动时自动加载默认内容（允许空查询）
        try:
            self.perform_search()
        except Exception:
            # 若初始化阶段出现异常，不阻塞窗口显示
            pass
    
    def setup_api_manager(self):
        """设置API管理器"""
        from ..api.api_manager import APIManager
        self.api_manager = APIManager(self.config)
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("FalconPy")
        self.setMinimumSize(800, 600)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建中央部件
        self.create_central_widget()
        # 为中央区域启用右键菜单
        try:
            cw = self.centralWidget()
            if cw:
                from PyQt6.QtCore import QPoint
                cw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                cw.customContextMenuRequested.connect(self.show_context_menu)
        except Exception:
            pass
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 设置快捷键
        self.setup_shortcuts()
        self._setup_update_checks()
        try:
            self._init_tag_suggest()
        except Exception:
            pass
        try:
            s0 = self.site_selector.get_current_site()
            self._fetch_tags_for_site(s0)
        except Exception:
            pass
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu(self.i18n.t('文件(&F)'))
        
        # 导入收藏夹
        import_action = QAction(self.i18n.t('导入收藏夹...'), self)
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.import_favorites)
        file_menu.addAction(import_action)
        
        # 导出收藏夹
        export_action = QAction(self.i18n.t('导出收藏夹...'), self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_favorites)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction(self.i18n.t('退出'), self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu(self.i18n.t('视图(&V)'))
        
        # 全屏
        fullscreen_action = QAction(self.i18n.t('全屏'), self)
        fullscreen_action.setShortcut('F11')
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(lambda checked=False: (self.showNormal() if self.isFullScreen() else self.showFullScreen()))
        view_menu.addAction(fullscreen_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu(self.i18n.t('工具(&T)'))
        
        # 账号管理
        account_action = QAction(self.i18n.t('账号管理...'), self)
        account_action.setShortcut('Ctrl+L')
        account_action.triggered.connect(self.show_account_management_dialog)
        tools_menu.addAction(account_action)
        
        tools_menu.addSeparator()
        
        # 设置
        settings_action = QAction(self.i18n.t('设置...'), self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings_dialog)
        tools_menu.addAction(settings_action)
        edit_cfg_action = QAction(self.i18n.t('编辑配置...'), self)
        edit_cfg_action.triggered.connect(self.open_config_file)
        tools_menu.addAction(edit_cfg_action)
        perf_action = QAction(self.i18n.t('性能面板'), self)
        perf_action.triggered.connect(self.show_perf_panel)
        tools_menu.addAction(perf_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu(self.i18n.t('帮助(&H)'))
        
        # 关于
        about_action = QAction(self.i18n.t('关于 FalconPy'), self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        check_update_action = QAction(self.i18n.t('检查更新...'), self)
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)
    
    def show_account_management_dialog(self):
        dialog = AccountManagementDialog(self)
        try:
            current_theme = self.theme_manager.get_current_theme()
            self.theme_manager.apply_theme(current_theme, dialog)
        except Exception:
            pass
        dialog.login_success.connect(self.on_login_success)
        dialog.logout_requested.connect(self.logout_from_site)
        dialog.exec()

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        try:
            current_theme = self.theme_manager.get_current_theme()
            self.theme_manager.apply_theme(current_theme, dialog)
        except Exception:
            pass
        dialog.exec()
    
    def open_config_file(self):
        try:
            path = Path(self.config.config_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                self.config.save_config()
            if os.name == 'nt':
                os.startfile(str(path))
            else:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            self.status_bar.showMessage(self.i18n.t("已打开配置文件: {file}").format(file=str(path)), 3000)
        except Exception as e:
            try:
                self.status_bar.showMessage(self.i18n.t("打开配置文件失败: {msg}").format(msg=str(e)), 3000)
            except Exception:
                pass

    def show_settings_dialog(self):
        dialog = SettingsDialog(self.config, self)
        current_theme = self.theme_manager.get_current_theme()
        self.theme_manager.apply_theme(current_theme, dialog)
        try:
            dialog.settings_changed.connect(self.apply_settings)
        except Exception:
            pass
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self.apply_settings()
    
    def on_login_success(self, site: str, user_info: dict):
        session_id = self.session_manager.create_session(
            site=site,
            user_info=user_info,
            remember=True
        )
        try:
            site_key = (site or '').lower()
            creds = {'username': user_info.get('username', '')}
            if site_key == 'danbooru':
                api_key = user_info.get('api_key', '')
                if api_key:
                    creds['api_key'] = api_key
            elif site_key in ('konachan', 'yande.re'):
                password = user_info.get('password', '')
                api_key = user_info.get('api_key', '')
                if password:
                    creds['password'] = password
                if api_key:
                    creds['api_key'] = api_key
            if any(k in creds and creds[k] for k in ('api_key', 'password')) or creds.get('username'):
                self.api_manager.update_credentials(site, creds)
        except Exception:
            pass
        self.update_ui_for_login_state(site, user_info)
        try:
            self.site_selector.set_current_site(site)
        except Exception:
            pass
        self.search_input.setText("")
        self.perform_search()
    
    def update_ui_for_login_state(self, site: str, user_info: dict):
        username = user_info.get('username', '')
        self.status_bar.showMessage(self.i18n.t("已登录到 {site} - 欢迎 {username}").format(site=site, username=username))
    
    def logout_from_site(self, site: str):
        user_info = self.session_manager.get_user_info(site)
        if user_info:
            user_id = user_info.get('user_id', user_info.get('username', ''))
            self.session_manager.delete_session(site, user_id)
        self.status_bar.showMessage(self.i18n.t("已从 {site} 登出").format(site=site))
    
    def check_existing_sessions(self):
        active_sessions = self.session_manager.get_all_active_sessions()
        if active_sessions:
            session = list(active_sessions.values())[0]
            site = session['site']
            user_info = session['user_info']
            self.update_ui_for_login_state(site, user_info)
    
    def apply_settings(self):
        theme = self.config.get('appearance.theme', 'win11')
        self.apply_theme(theme)
        try:
            lang = self.config.get('appearance.language', 'zh_CN')
            self.i18n.set_language(lang)
            self.menuBar().clear()
            self.create_menu_bar()
        except Exception:
            pass
        self.update()
        try:
            self.status_bar.showMessage(self.i18n.t("设置已应用"))
        except Exception:
            self.status_bar.showMessage("设置已应用")
        try:
            if hasattr(self, 'image_grid') and self.image_grid:
                self.image_grid.update_grid()
            if hasattr(self, 'fav_grids') and isinstance(self.fav_grids, dict):
                for _k, _g in self.fav_grids.items():
                    try:
                        _g.update_grid()
                    except Exception:
                        pass
        except Exception:
            pass
    
    def apply_theme(self, theme: str):
        self.theme_manager.apply_theme(theme, self)
    
    
    
    

    def export_favorites(self):
        try:
            data = self.db_manager.export_favorites_data()
            default_dir = Path(self.config.favorites_dir)
            default_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f'favorites_export_{ts}.json'
            default_path = str(default_dir / default_name)
            path, _ = QFileDialog.getSaveFileName(self, self.i18n.t('导出收藏夹'), default_path, 'JSON (*.json)')
            if not path:
                return
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_bar.showMessage(self.i18n.t('收藏夹已导出: {file}').format(file=path), 4000)
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t('错误'), self.i18n.t('导出失败: {msg}').format(msg=str(e)))

    def import_favorites(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, self.i18n.t('导入收藏夹'), str(self.config.favorites_dir), 'JSON (*.json)')
            if not path:
                return
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            favs = []
            if isinstance(data, dict) and 'favorites' in data and isinstance(data['favorites'], list):
                favs = data['favorites']
            elif isinstance(data, list):
                favs = data
            progress = QProgressDialog(self.i18n.t('正在导入收藏...'), self.i18n.t('取消'), 0, max(1, len(favs)), self)
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.show()
            stats = self.db_manager.import_favorites_data(data)
            progress.setValue(progress.maximum())
            self.status_bar.showMessage(self.i18n.t('导入完成: 收藏夹 {fav}, 新建 {new}, 图片 {img}, 跳过 {skip}').format(
                fav=stats.get('total_favorites', 0),
                new=stats.get('created_favorites', 0),
                img=stats.get('imported_images', 0),
                skip=stats.get('skipped_duplicates', 0)
            ), 5000)
            self._refresh_favorites_if_active()
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t('错误'), self.i18n.t('导入失败: {msg}').format(msg=str(e)))

    

    def _on_fav_source_changed(self, idx: int):
        try:
            text = self.fav_source_box.currentText().strip()
            if text.startswith('本地'):
                self.fav_source = 'local'
            elif text.startswith('在线'):
                self.fav_source = 'online'
            else:
                self.fav_source = 'merge'
            self._cancel_online_fav_thread()
            self._load_favorites_into_tabs()
        except Exception:
            pass

    def _on_tab_changed(self, index: int):
        try:
            tab_text = self.tab_widget.tabText(index)
            if tab_text == '收藏夹' or tab_text == self.i18n.t('收藏夹'):
                self._load_favorites_into_tabs()
        except Exception:
            pass

    def _refresh_favorites_if_active(self):
        try:
            current_index = self.tab_widget.currentIndex()
            if self.tab_widget.tabText(current_index) == '收藏夹' or self.tab_widget.tabText(current_index) == self.i18n.t('收藏夹'):
                self._load_favorites_into_tabs()
        except Exception:
            pass

    

    

    

    

    

    def _start_online_fav_fetch(self):
        try:
            username = self.config.get('sites.danbooru.username', '')
            api_key = self.config.get('sites.danbooru.api_key', '')
            if not username or not api_key:
                self.status_bar.showMessage("Danbooru 在线收藏：请登录并配置用户名与API Key", 4000)
                return
        except Exception:
            pass
        self._cancel_online_fav_thread()
        try:
            thread = FavoritesFetchThread(self.api_manager, 'danbooru', page=1, limit=40)
            thread.favorites_ready.connect(self._on_online_fav_ready)
            thread.error.connect(self._on_online_fav_error)
            self.current_fav_thread = thread
            self.fav_source_box.setEnabled(False)
            self.status_bar.showMessage("正在获取 Danbooru 在线收藏...", 2000)
            thread.start()
        except Exception as e:
            self.status_bar.showMessage(f"启动在线收藏线程失败：{e}", 4000)

    def _on_online_fav_ready(self, results: list):
        try:
            local_images = []
            grid = self.fav_grids.get('danbooru')
            if grid:
                try:
                    local_images = list(grid.current_images)
                except Exception:
                    local_images = []
            final_images = results or []
            if self.fav_source == 'merge':
                seen = set()
                merged = []
                for it in (local_images + final_images):
                    iid = str(it.get('id')) + '@' + (it.get('site') or 'danbooru')
                    if iid not in seen:
                        seen.add(iid)
                        merged.append(it)
                final_images = merged
            if grid:
                grid.set_images(final_images, 1, 1)
            self.status_bar.showMessage("Danbooru 在线收藏已更新", 2000)
        except Exception as e:
            self.status_bar.showMessage(f"更新在线收藏失败：{e}", 4000)
        finally:
            self.fav_source_box.setEnabled(True)
            self._cancel_online_fav_thread()

    def _on_online_fav_error(self, msg: str):
        try:
            self.status_bar.showMessage(f"获取在线收藏失败：{msg}", 4000)
        except Exception:
            pass
        finally:
            self.fav_source_box.setEnabled(True)
            self._cancel_online_fav_thread()

    def _cancel_online_fav_thread(self):
        try:
            th = getattr(self, 'current_fav_thread', None)
            if th:
                try:
                    th.cancel()
                except Exception:
                    pass
                try:
                    if th.isRunning():
                        th.wait(500)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.current_fav_thread = None

    def _get_site_default_fav_id(self, site: str):
        try:
            data = self.config.data
            fav_def = (data.get('sites', {}).get(site, {}) or {}).get('favorite_default', {})
            return fav_def.get('folder_id')
        except Exception:
            return None

    def _get_site_dest_default(self, site: str) -> str:
        try:
            data = self.config.data
            fav_def = (data.get('sites', {}).get(site, {}) or {}).get('favorite_default', {})
            return fav_def.get('destination', 'local')
        except Exception:
            return 'local'

    def _set_site_fav_default(self, site: str, destination: str, folder_id):
        try:
            sites = self.config.data.setdefault('sites', {})
            site_cfg = sites.setdefault(site, {})
            fav_def = site_cfg.setdefault('favorite_default', {})
            fav_def['destination'] = destination
            fav_def['folder_id'] = folder_id
            self.config.save()
        except Exception:
            pass

    def _choose_favorite_destination(self, site: str):
        try:
            dest = self._get_site_dest_default(site)
            folder_id = self._get_site_default_fav_id(site)
            if dest == 'online' or (dest == 'local' and folder_id):
                return {'destination': dest, 'folder_id': folder_id, 'remember': False}
        except Exception:
            pass
        dlg = FavoriteDestinationDialog(site, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = dlg.get_selection()
            if sel.get('remember'):
                self._set_site_fav_default(site, sel.get('destination'), sel.get('folder_id'))
            return sel
        return None

    def _start_online_fav_op(self, site: str, op: str, post_id: str):
        try:
            th = getattr(self, '_online_fav_thread', None)
            if th and th.isRunning():
                try:
                    th.finished_ok.disconnect()
                    th.error.disconnect()
                except Exception:
                    pass
        except Exception:
            pass
        th = OnlineFavoriteOpThread(self.api_manager, site, op, post_id)
        th.finished_ok.connect(lambda ok: self.status_bar.showMessage('在线收藏已更新' if ok else '在线收藏更新失败', 3000))
        th.error.connect(lambda m: self.status_bar.showMessage(f'在线收藏操作错误：{m}', 5000))
        self._online_fav_thread = th
        th.start()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # 搜索快捷键 (Ctrl+F)
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.focus_search)
        
        # 收藏快捷键 (Ctrl+D) - 需要当前选中图片
        favorite_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        favorite_shortcut.activated.connect(self.toggle_current_favorite)
        
        # 下载快捷键 (Ctrl+S) - 需要当前选中图片
        download_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        download_shortcut.activated.connect(self.download_current_image)
        
        # 上一页快捷键 (Ctrl+Left)
        prev_page_shortcut = QShortcut(QKeySequence("Ctrl+Left"), self)
        prev_page_shortcut.activated.connect(self.go_prev_page)
        
        # 下一页快捷键 (Ctrl+Right)
        next_page_shortcut = QShortcut(QKeySequence("Ctrl+Right"), self)
        next_page_shortcut.activated.connect(self.go_next_page)
        
        # ESC键关闭全屏或对话框
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.handle_escape)

    def _setup_update_checks(self):
        enabled = bool(self.config.get('updates.enabled', True))
        if not enabled:
            return
        interval = int(self.config.get('updates.interval_minutes', 60))
        if interval <= 0:
            interval = 60
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update_timer)
        self.update_timer.start(interval * 60 * 1000)
        self._on_update_timer()
    
    def _on_update_timer(self):
        try:
            t = UpdateCheckThread(self.update_manager)
            try:
                t.setParent(self)
            except Exception:
                pass
            self._bg_threads.append(t)
            def _handle(info: dict):
                try:
                    if info.get('has_update'):
                        ver = info.get('最新版本') or info.get('latest_version') or ''
                        ignored = set(self.config.get('updates.ignore_versions', []) or [])
                        last = self.config.get('updates.last_notified', None)
                        if ver in ignored or ver == last:
                            return
                        self.status_bar.showMessage(self.i18n.t("发现新版本: {ver}").format(ver=ver), 8000)
                        msg = QMessageBox(self)
                        msg.setWindowTitle(self.i18n.t('更新可用'))
                        msg.setText(self.i18n.t('发现新版本 {ver}').format(ver=ver))
                        msg.setInformativeText(self.i18n.t('是否前往下载页面？'))
                        download_btn = msg.addButton(self.i18n.t('前往下载'), QMessageBox.ButtonRole.AcceptRole)
                        later_btn = msg.addButton(self.i18n.t('稍后提醒'), QMessageBox.ButtonRole.RejectRole)
                        ignore_btn = msg.addButton(self.i18n.t('忽略此版本'), QMessageBox.ButtonRole.DestructiveRole)
                        msg.exec()
                        clicked = msg.clickedButton()
                        if clicked == download_btn:
                            url = info.get('download_url') or info.get('notes_url')
                            if url:
                                import webbrowser
                                webbrowser.open(url)
                            self.config.set('updates.last_notified', ver)
                            self.config.save_config()
                        elif clicked == ignore_btn:
                            ignored.add(ver)
                            self.config.set('updates.ignore_versions', list(ignored))
                            self.config.save_config()
                        else:
                            self.config.set('updates.last_notified', ver)
                            self.config.save_config()
                except Exception:
                    pass
            try:
                t.done.connect(_handle)
                t.finished.connect(lambda: self._cleanup_bg_thread(t))
            except Exception:
                pass
            t.start()
        except Exception:
            pass
    
    def check_for_updates(self):
        try:
            self.status_bar.showMessage(self.i18n.t('正在检查更新...'), 2000)
            t = UpdateCheckThread(self.update_manager)
            try:
                t.setParent(self)
            except Exception:
                pass
            self._bg_threads.append(t)
            def _handle(info: dict):
                try:
                    if info.get('has_update'):
                        ver = info.get('latest_version') or ''
                        msg = QMessageBox(self)
                        msg.setWindowTitle(self.i18n.t('更新可用'))
                        msg.setText(self.i18n.t('发现新版本 {ver}').format(ver=ver))
                        msg.setInformativeText(self.i18n.t('是否前往下载页面？'))
                        download_btn = msg.addButton(self.i18n.t('前往下载'), QMessageBox.ButtonRole.AcceptRole)
                        later_btn = msg.addButton(self.i18n.t('稍后提醒'), QMessageBox.ButtonRole.RejectRole)
                        ignore_btn = msg.addButton(self.i18n.t('忽略此版本'), QMessageBox.ButtonRole.DestructiveRole)
                        msg.exec()
                        clicked = msg.clickedButton()
                        if clicked == download_btn:
                            url = info.get('download_url') or info.get('notes_url')
                            if url:
                                import webbrowser
                                webbrowser.open(url)
                            self.config.set('updates.last_notified', ver)
                            self.config.save_config()
                        elif clicked == ignore_btn:
                            ignored = set(self.config.get('updates.ignore_versions', []) or [])
                            ignored.add(ver)
                            self.config.set('updates.ignore_versions', list(ignored))
                            self.config.save_config()
                        else:
                            self.config.set('updates.last_notified', ver)
                            self.config.save_config()
                    else:
                        self.status_bar.showMessage(self.i18n.t('已是最新版本'), 4000)
                except Exception:
                    pass
            try:
                t.done.connect(_handle)
                t.finished.connect(lambda: self._cleanup_bg_thread(t))
            except Exception:
                pass
            t.start()
        except Exception:
            pass

    def _cleanup_bg_thread(self, thread):
        try:
            if thread in getattr(self, '_bg_threads', []):
                self._bg_threads.remove(thread)
            thread.deleteLater()
        except Exception:
            pass
    
    def focus_search(self):
        """聚焦到搜索框"""
        if hasattr(self, 'search_input'):
            self.search_input.setFocus()
            self.search_input.selectAll()
    
    def toggle_current_favorite(self):
        """切换当前图片的收藏状态"""
        # 获取当前选中的图片
        if hasattr(self, 'image_grid') and self.image_grid.current_images:
            current_image = self.image_grid.get_selected_image()
            if current_image:
                # 这里需要实现收藏逻辑
                self.toggle_favorite(current_image)
            else:
                self.statusBar().showMessage(self.i18n.t("请先选择一张图片"), 2000)
    
    def download_current_image(self):
        """下载当前选中的图片"""
        if hasattr(self, 'image_grid') and self.image_grid.current_images:
            current_image = self.image_grid.get_selected_image()
            if current_image:
                # 这里需要实现下载逻辑
                self.download_image(current_image)
            else:
                self.statusBar().showMessage(self.i18n.t("请先选择一张图片"), 2000)
    
    def go_prev_page(self):
        """转到上一页"""
        if hasattr(self, 'image_grid'):
            self.image_grid.prev_page()
    
    def go_next_page(self):
        """转到下一页"""
        if hasattr(self, 'image_grid'):
            self.image_grid.next_page()
    
    def handle_escape(self):
        """处理ESC键"""
        # 如果是全屏状态，退出全屏
        if self.isFullScreen():
            self.showNormal()
        # 如果有对话框打开，关闭对话框
        # 这里可以添加更多ESC处理逻辑
        
    

    

    

    

    

    

    

    

    

    

    

    def show_image_viewer(self, image_data: dict):
        from .widgets.image_viewer import ImageViewerDialog
        images = []
        try:
            images = list(self.image_grid.current_images)
        except Exception:
            images = []
        cur_idx = 0
        try:
            cur_id = image_data.get('id')
            cur_site = image_data.get('site')
            cur_idx = next((i for i, it in enumerate(images)
                            if it.get('id') == cur_id and it.get('site') == cur_site), 0)
        except Exception:
            cur_idx = 0
        viewer = ImageViewerDialog(image_data, None, images_list=images, current_index=cur_idx)
        viewer.favorite_toggled.connect(self.on_favorite_toggled)
        viewer.download_requested.connect(self.download_image)
        viewer.tag_clicked.connect(self.on_viewer_tag_clicked)
        viewer.show()
        if not hasattr(self, 'image_viewers'):
            self.image_viewers = []
        self.image_viewers.append(viewer)
        try:
            viewer.destroyed.connect(self._on_viewer_destroyed)
        except Exception:
            pass

    def on_favorite_toggled(self, image_data: dict, is_favorite: bool):
        site = (image_data.get('site') or 'unknown').lower()
        if site == 'unknown':
            site = 'danbooru'
        if is_favorite:
            sel = self._choose_favorite_destination(site)
            if not sel:
                return
            if sel.get('destination') == 'local':
                fav_id = sel.get('folder_id') or self._get_default_favorite_id()
                try:
                    img_id = str(image_data.get('id'))
                    self.db_manager.add_image_to_favorite(fav_id, img_id, site, image_data)
                    self.status_bar.showMessage("已添加到本地收藏夹", 2000)
                    self._refresh_favorites_if_active()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加到本地收藏夹失败：{str(e)}")
            else:
                post_id = str(image_data.get('id'))
                self._start_online_fav_op(site, 'add', post_id)
        else:
            dest = self._get_site_dest_default(site)
            if dest == 'local':
                fav_id = self._get_site_default_fav_id(site) or self._get_default_favorite_id()
                try:
                    img_id = str(image_data.get('id'))
                    self.db_manager.remove_image_from_favorite(fav_id, img_id, site)
                    self.status_bar.showMessage("已从本地收藏夹移除", 2000)
                    self._refresh_favorites_if_active()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"移除本地收藏失败：{str(e)}")
            else:
                post_id = str(image_data.get('id'))
                self._start_online_fav_op(site, 'remove', post_id)


    

    

    

    

    

    def _on_viewer_destroyed(self, obj=None):
        try:
            v = obj if obj is not None else getattr(self, 'sender', lambda: None)()
            if hasattr(self, 'image_viewers') and v in self.image_viewers:
                self.image_viewers.remove(v)
        except Exception:
            pass

    

    

    def toggle_favorite(self, image_data):
        """切换图片收藏状态"""
        self.statusBar().showMessage(self.i18n.t("收藏功能待实现"), 2000)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar(self.i18n.t("主工具栏"))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # 网站选择器
        self.site_selector = SiteSelectorWidget()
        toolbar.addWidget(self.site_selector)
        
        toolbar.addSeparator()
        
        # 搜索框
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.i18n.t("输入标签搜索..."))
        self.search_input.setMinimumWidth(300)
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.search_button = QPushButton(self.i18n.t("搜索"))
        self.search_button.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        
        toolbar.addWidget(search_widget)
        
        toolbar.addSeparator()
        
        # 刷新按钮
        refresh_action = QAction(self.i18n.t("刷新"), self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_content)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # 账号管理按钮（替代旧登录入口）
        self.account_button = QPushButton(self.i18n.t("账号管理"))
        self.account_button.clicked.connect(self.show_account_management_dialog)
        toolbar.addWidget(self.account_button)
        try:
            if hasattr(self, 'tag_suggest'):
                self.tag_suggest.attach(self.search_input)
        except Exception:
            pass
        
        # 连接信号
        self.site_selector.site_changed.connect(self.on_site_changed)
        self.search_button.clicked.connect(self.perform_search)
        self.search_input.returnPressed.connect(self.perform_search)
        
        # 连接图片网格信号
        self.image_grid.image_selected.connect(self.show_image_viewer)
        self.image_grid.favorite_added.connect(self.add_to_favorites)
        try:
            self.image_grid.favorite_removed.connect(self.remove_from_favorites)
        except Exception:
            pass
        self.image_grid.page_changed.connect(self.load_page)
        # 接入图片网格下载请求
        try:
            self.image_grid.download_requested.connect(self.download_image)
            self.image_grid.refresh_requested.connect(self.refresh_content)
        except Exception:
            pass
        
        # 移除侧栏后不再连接收藏夹面板信号
        
    def add_to_favorites(self, image_data: dict):
        try:
            favorite_id = self._get_default_favorite_id()
            img_id = str(image_data.get('id'))
            site = (image_data.get('site') or 'unknown').lower()
            success = self.db_manager.add_image_to_favorite(favorite_id, img_id, site, image_data)
            if success:
                self.status_bar.showMessage("已添加到收藏夹：默认收藏夹", 2000)
            else:
                self.status_bar.showMessage("该图片已在收藏夹中", 2000)
            self._refresh_favorites_if_active()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加到收藏夹失败：{str(e)}")

    def remove_from_favorites(self, image_data: dict):
        try:
            img_id = str(image_data.get('id'))
            site = (image_data.get('site') or 'unknown').lower()
            try:
                cnt = self.db_manager.remove_image_global(img_id, site)
                if cnt > 0:
                    self.status_bar.showMessage("已从收藏夹移除", 2000)
                else:
                    fav_id = self._get_site_default_fav_id(site) or self._get_default_favorite_id()
                    self.db_manager.remove_image_from_favorite(fav_id, img_id, site)
                    self.status_bar.showMessage("已从收藏夹移除", 2000)
            except Exception:
                fav_id = self._get_site_default_fav_id(site) or self._get_default_favorite_id()
                self.db_manager.remove_image_from_favorite(fav_id, img_id, site)
                self.status_bar.showMessage("已从收藏夹移除", 2000)
            self._refresh_favorites_if_active()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"移除收藏失败：{str(e)}")

    def refresh_content(self):
        try:
            s = self.site_selector.get_current_site()
            self._fetch_tags_for_site(s)
        except Exception:
            pass
        self.perform_search()

    def on_site_changed(self, site: str):
        self.status_bar.showMessage(f"已切换到: {site}")
        try:
            self._fetch_tags_for_site(site)
        except Exception:
            pass
        self.perform_search()

    def on_viewer_tag_clicked(self, tag: str):
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            modifiers = QApplication.keyboardModifiers()
        except Exception:
            modifiers = None
        if hasattr(self, 'search_input'):
            base = self.search_input.text().strip()
            if modifiers and (modifiers & Qt.KeyboardModifier.ControlModifier):
                query = (f"{base} {tag}" if base else tag).strip()
            else:
                query = tag
            self.search_input.setText(query)
            try:
                if self.windowState() & Qt.WindowState.WindowMinimized:
                    self.showNormal()
                self.activateWindow()
                self.raise_()
            except Exception:
                pass
            self.perform_search()

    def create_central_widget(self):
        """创建中央部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 移除左侧收藏夹面板
        
        # 右侧主内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        
        # 图片浏览标签页
        self.image_grid = ImageGridWidget(self.cache_manager, i18n=self.i18n)
        self.tab_widget.addTab(self.image_grid, self.i18n.t("图片浏览"))
        try:
            loader = getattr(self.image_grid, 'image_loader', None)
            if loader and hasattr(loader, 'cache_stats_updated'):
                loader.cache_stats_updated.connect(self._on_cache_stats)
            if loader and hasattr(loader, 'thumbnail_loaded'):
                loader.thumbnail_loaded.connect(self._on_first_thumbnail_loaded)
            elif loader and hasattr(loader, 'image_loaded'):
                loader.image_loaded.connect(self._on_first_thumbnail_loaded)
        except Exception:
            pass
        
        # 合并收藏夹标签页：按站点分组
        favorites_widget = QWidget()
        fav_layout = QVBoxLayout(favorites_widget)
        fav_layout.setContentsMargins(0, 0, 0, 0)

        # 收藏来源选择器
        source_bar = QWidget()
        source_layout = QHBoxLayout(source_bar)
        source_layout.setContentsMargins(6, 6, 6, 6)
        source_layout.setSpacing(8)
        source_label = QLabel(self.i18n.t("收藏来源："))
        self.fav_source_box = QComboBox()
        self.fav_source_box.addItems([
            self.i18n.t("本地"), 
            self.i18n.t("在线(Danbooru)"), 
            self.i18n.t("合并")
        ])
        self.fav_source_box.currentIndexChanged.connect(self._on_fav_source_changed)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.fav_source_box)
        source_layout.addStretch(1)
        fav_layout.addWidget(source_bar)
        
        self.fav_tab = QTabWidget()
        self.fav_tab.setTabPosition(QTabWidget.TabPosition.North)
        
        self.site_tabs = [
            ("Danbooru", "danbooru"),
            ("Konachan", "konachan"),
            ("Yande.re", "yandere")
        ]
        self.fav_grids = {}
        for title, key in self.site_tabs:
            grid = ImageGridWidget(self.cache_manager, i18n=self.i18n)
            self.fav_grids[key] = grid
            # 收藏页子网格：绑定图片选择到查看器
            try:
                grid.image_selected.connect(lambda data, g=grid: self.show_image_viewer_from_grid(g, data))
                grid.download_requested.connect(self.download_image)
                grid.refresh_requested.connect(self.refresh_content)
            except Exception:
                pass
            self.fav_tab.addTab(grid, title)
        fav_layout.addWidget(self.fav_tab)
        self.tab_widget.addTab(favorites_widget, self.i18n.t("收藏夹"))
        
        content_layout.addWidget(self.tab_widget)
        splitter.addWidget(content_widget)
        
        # 设置分割器比例
        splitter.setSizes([0, 1200])
        
        # 切换到收藏夹页时加载数据
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def show_context_menu(self, pos):
        """显示主界面右键菜单"""
        # 若点击在图片网格或缩略图区域，交由图片网格自身的右键菜单处理
        try:
            global_pos = self.centralWidget().mapToGlobal(pos)
            w = QApplication.widgetAt(global_pos)
            # 回溯父级，判断是否位于图片网格或缩略图
            p = w
            grid_widget = getattr(self.image_grid, 'grid_widget', None)
            while p:
                if p is grid_widget:
                    return
                if isinstance(p, ImageThumbnail):
                    return
                p = getattr(p, 'parentWidget', lambda: None)()
        except Exception:
            pass
        try:
            menu = QMenu(self)

            # 刷新与翻页
            act_refresh = menu.addAction(self.i18n.t("刷新"))
            act_prev = menu.addAction(self.i18n.t("上一页"))
            act_next = menu.addAction(self.i18n.t("下一页"))
            menu.addSeparator()

            # 当前图片操作
            act_copy_link = menu.addAction(self.i18n.t("复制当前图片链接"))
            act_download = menu.addAction(self.i18n.t("下载当前图片"))
            act_download_all = menu.addAction(self.i18n.t("批量下载当前页"))
            menu.addSeparator()

            # 目录与设置
            act_open_dl = menu.addAction(self.i18n.t("打开下载目录"))
            # 缓存相关
            act_open_cache = menu.addAction(self.i18n.t("打开图片缓存目录"))
            act_open_thumb = menu.addAction(self.i18n.t("打开缩略图目录"))
            act_clear_cache = menu.addAction(self.i18n.t("清理图片缓存"))
            act_clear_thumb = menu.addAction(self.i18n.t("清理缩略图缓存"))
            act_account = menu.addAction(self.i18n.t("账号管理..."))
            act_settings = menu.addAction(self.i18n.t("设置..."))
            # 全屏/退出全屏
            act_full = menu.addAction(self.i18n.t("退出全屏") if self.isFullScreen() else self.i18n.t("全屏"))

            menu.addSeparator()
            # 标签切换
            act_tab_browse = menu.addAction(self.i18n.t("切换到图片浏览"))
            act_tab_fav = menu.addAction(self.i18n.t("切换到收藏夹"))

            # 触发位置：将相对位置转换为全局
            global_pos = self.centralWidget().mapToGlobal(pos)
            action = menu.exec(global_pos)

            if not action:
                return

            # 分发动作
            if action == act_refresh:
                self.refresh_content()
            elif action == act_prev:
                self.go_prev_page()
            elif action == act_next:
                self.go_next_page()
            elif action == act_copy_link:
                self.copy_current_image_link()
            elif action == act_download:
                self.download_current_image()
            elif action == act_download_all:
                self.batch_download_current_page()
            elif action == act_open_dl:
                self.open_downloads_dir()
            elif action == act_open_cache:
                self.open_cache_dir()
            elif action == act_open_thumb:
                self.open_thumbnails_dir()
            elif action == act_clear_cache:
                self.clear_image_cache()
            elif action == act_clear_thumb:
                self.clear_thumbnail_cache()
            elif action == act_account:
                self.show_account_management_dialog()
            elif action == act_settings:
                self.show_settings_dialog()
            elif action == act_full:
                self.showNormal() if self.isFullScreen() else self.showFullScreen()
            elif action == act_tab_browse:
                self.switch_to_tab(self.i18n.t("图片浏览"))
            elif action == act_tab_fav:
                self.switch_to_tab(self.i18n.t("收藏夹"))
        except Exception as e:
            try:
                self.status_bar.showMessage(self.i18n.t("右键菜单错误: {msg}").format(msg=str(e)))
            except Exception:
                pass
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel(self.i18n.t("就绪"))
        self.status_bar.addWidget(self.status_label)
        

        
        # 进度信息
        self.progress_label = QLabel("")
        self.status_bar.addPermanentWidget(self.progress_label)
        self._perf_panel = None
        self._last_first_ms = None

    def _on_cache_stats(self, stats: dict):
        try:
            active = int(stats.get('active_loads', 0))
            maxc = int(stats.get('max_concurrent', 0))
            pending = int(stats.get('pending_loads', 0))
            qsize = int(stats.get('preload_queue_size', 0))
            hit_rate = float(stats.get('cache_hit_rate', 0.0))
            avg_ms = float(stats.get('avg_load_ms', 0.0))
            loaded = int(stats.get('loaded_count', 0))
            cancel = int(stats.get('cancel_count', 0))
            text = f"加载 {active}/{maxc} | 等待 {pending} | 预载 {qsize} | 命中 {hit_rate*100:.0f}% | 平均 {avg_ms:.0f}ms | 成功 {loaded} | 取消 {cancel}"
            self.progress_label.setText(text)
            if self._perf_panel:
                try:
                    self._perf_panel.update_stats(stats, self._last_first_ms)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_first_thumbnail_loaded(self, *args, **kwargs):
        try:
            import time
            if not hasattr(self, '_first_image_reported'):
                self._first_image_reported = False
            if not hasattr(self, '_search_start_ts'):
                self._search_start_ts = None
            if self._first_image_reported:
                return
            if self._search_start_ts:
                elapsed = time.perf_counter() - float(self._search_start_ts)
                self.status_bar.showMessage(f"首图耗时 {elapsed:.3f}s", 2000)
                self._last_first_ms = elapsed * 1000.0
                self._first_image_reported = True
                if self._perf_panel:
                    try:
                        self._perf_panel.update_stats({}, self._last_first_ms)
                    except Exception:
                        pass
        except Exception:
            pass

    def eventFilter(self, obj, event):
        try:
            from PyQt6.QtCore import QEvent
            if obj is getattr(self, 'search_input', None) and event.type() == QEvent.Type.KeyPress:
                ts = getattr(self, 'tag_suggest', None)
                if ts and ts.handle_key(event):
                    return True
            if obj is getattr(self, 'search_input', None) and event.type() == QEvent.Type.FocusOut:
                ts = getattr(self, 'tag_suggest', None)
                if ts:
                    try:
                        ts.hide()
                    except Exception:
                        pass
            # 点击窗体其他区域时，若建议框可见且点击不在建议框/搜索框上，则隐藏建议框
            if event.type() == QEvent.Type.MouseButtonPress:
                ts = getattr(self, 'tag_suggest', None)
                if ts and getattr(ts, 'popup', None) and ts.popup.isVisible():
                    try:
                        w = self.sender() if hasattr(self, 'sender') else None
                    except Exception:
                        w = None
                    # 直接根据点击点判断是否在弹框/输入框矩形区域
                    try:
                        pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                    except Exception:
                        pos = None
                    if pos is not None:
                        in_popup = ts.popup.frameGeometry().contains(pos)
                        in_input = self.search_input.frameGeometry().contains(pos)
                        if not in_popup and not in_input:
                            try:
                                ts.hide()
                            except Exception:
                                pass
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _init_tag_suggest(self):
        try:
            self.tag_suggest = TagSuggest(self, i18n=self.i18n)
            if hasattr(self, 'search_input') and self.search_input:
                try:
                    self.tag_suggest.attach(self.search_input)
                    self.tag_suggest.set_remote_fetcher(self._fetch_tags_remote)
                except Exception:
                    pass
        except Exception:
            self.tag_suggest = None

    def _ensure_tags_for_site(self, site: str):
        s = (site or '').lower()
        if s in ('yande.re', 'yande'):
            s = 'yandere'
        if s not in self._tag_cache or not self._tag_cache.get(s):
            self._fetch_tags_for_site(s)
        else:
            try:
                if self.tag_suggest:
                    self.tag_suggest.set_tags(self._tag_cache.get(s, []))
            except Exception:
                pass

    def _fetch_tags_for_site(self, site: str):
        try:
            s = (site or '').lower()
            if s in ('yande.re', 'yande'):
                s = 'yandere'
            if getattr(self, '_tag_thread', None) and self._tag_thread.isRunning():
                try:
                    self._tag_thread.cancel()
                except Exception:
                    pass
                try:
                    if not self._tag_thread.wait(1000):
                        self._tag_thread.terminate()
                        self._tag_thread.wait()
                except Exception:
                    pass
            t = TagsFetchThread(self.api_manager, s, limit=1000)
            t.tags_ready.connect(lambda tags, ss=s: self._on_tags_ready(ss, tags))
            t.error.connect(lambda msg, ss=s: self._on_tags_error(ss, msg))
            self._tag_thread = t
            t.start()
        except Exception:
            pass

    def _on_tags_ready(self, site: str, tags: list):
        try:
            self._tag_cache[site] = list(tags or [])
            self._tag_retry[site] = 0
            if self.tag_suggest:
                self.tag_suggest.set_tags(self._tag_cache.get(site, []))
            self.status_bar.showMessage(self.i18n.t("标签已更新"), 2000)
        except Exception:
            pass

    def _on_tags_error(self, site: str, msg: str):
        try:
            n = int(self._tag_retry.get(site, 0) or 0)
            if n < 2:
                self._tag_retry[site] = n + 1
                QTimer.singleShot(600 * (n + 1), lambda ss=site: self._fetch_tags_for_site(ss))
            else:
                self.status_bar.showMessage(self.i18n.t("标签获取失败"), 3000)
        except Exception:
            pass
    
    
    
    def restore_geometry(self):
        """恢复窗口几何信息"""
        width = self.config.get('window.width', 1200)
        height = self.config.get('window.height', 800)
        maximized = self.config.get('window.maximized', False)
        
        self.resize(width, height)
        if maximized:
            self.showMaximized()
    
    def save_geometry(self):
        """保存窗口几何信息"""
        if not self.isMaximized():
            self.config.set('window.width', self.width())
            self.config.set('window.height', self.height())
        self.config.set('window.maximized', self.isMaximized())
        self.config.save_config()
    
    
    
    def perform_search(self):
        """执行搜索"""
        try:
            import time
            self._search_start_ts = time.perf_counter()
            self._first_image_reported = False
            self._last_first_ms = None
        except Exception:
            pass
        query = self.search_input.text().strip()
        try:
            if self._try_open_url_in_viewer(query):
                return
        except Exception:
            pass
        # 允许空查询：各站点通常会返回默认最新/热门内容

        site = self.site_selector.get_current_site()
        if site == "yande.re":
            site = "yandere"
        try:
            self._ensure_tags_for_site(site)
        except Exception:
            pass

        display_query = query if query else self.i18n.t("默认内容")
        self.status_bar.showMessage(self.i18n.t("正在搜索: {query}").format(query=display_query))
        
        # 使用后台线程执行异步搜索，避免主线程没有事件循环导致任务不执行
        from .threads.api_search_thread import APISearchThread
        
        # 若已有搜索线程，优先协作式取消并等待完成
        if hasattr(self, 'current_search_thread') and self.current_search_thread:
            try:
                if self.current_search_thread.isRunning():
                    try:
                        if hasattr(self.current_search_thread, 'cancel'):
                            self.current_search_thread.cancel()
                    except Exception:
                        pass
                    if not self.current_search_thread.wait(1000):
                        self.current_search_thread.terminate()
                        self.current_search_thread.wait()
            except Exception:
                pass
        
        self._last_query = query
        self._last_site = site
        self._last_page = 1
        self.current_search_thread = APISearchThread(self.api_manager, site, query, 1, 20)
        self.current_search_thread.results_ready.connect(self._on_search_results)
        self.current_search_thread.error.connect(self._on_search_error)
        # 禁用搜索按钮，避免并发启动
        try:
            if hasattr(self, 'search_button'):
                self.search_button.setEnabled(False)
                self.search_button.setText(self.i18n.t("搜索中..."))
            # 输入框也可防止回车重复触发
            if hasattr(self, 'search_input'):
                self.search_input.setEnabled(False)
        except Exception:
            pass
        self.current_search_thread.start()

    def _extract_site_from_netloc(self, netloc: str):
        try:
            n = (netloc or '').lower()
            if 'danbooru.donmai.us' in n:
                return 'danbooru'
            if 'aibooru.online' in n:
                return 'aibooru'
            if 'konachan.net' in n:
                return 'konachan'
            if 'yande.re' in n:
                return 'yandere'
        except Exception:
            pass
        return None

    def _open_viewer_single(self, image_data: dict):
        from .widgets.image_viewer import ImageViewerDialog
        viewer = ImageViewerDialog(image_data, None, images_list=[image_data], current_index=0)
        viewer.favorite_toggled.connect(self.on_favorite_toggled)
        viewer.download_requested.connect(self.download_image)
        viewer.tag_clicked.connect(self.on_viewer_tag_clicked)
        viewer.show()
        if not hasattr(self, 'image_viewers'):
            self.image_viewers = []
        self.image_viewers.append(viewer)
        try:
            viewer.destroyed.connect(self._on_viewer_destroyed)
        except Exception:
            pass

    def _try_open_url_in_viewer(self, text: str) -> bool:
        try:
            from urllib.parse import urlparse
            u = urlparse(text)
            if not u.scheme or not u.netloc:
                return False
            if u.scheme not in ('http', 'https'):
                return False
            site = self._extract_site_from_netloc(u.netloc)
            if not site:
                return False
            url = text
            path = u.path or ''
            base = url.split('?')[0]
            ext = ''
            try:
                if '.' in base:
                    ext = base.rsplit('.', 1)[-1].lower()
            except Exception:
                ext = ''
            media_exts = {'jpg','jpeg','png','gif','webp','mp4','webm'}
            is_direct = (ext in media_exts) or any(seg in path for seg in ('/data/', '/image/', '/original/', '/jpeg/', '/png/'))
            if is_direct:
                data = {'site': site, 'file_url': url, 'preview_url': url}
                if ext:
                    data['file_ext'] = ext
                try:
                    self._open_viewer_single(data)
                except Exception:
                    pass
                return True
            if site in ('konachan', 'yandere'):
                data = {'site': site, 'post_url': url}
                try:
                    self._open_viewer_single(data)
                except Exception:
                    pass
                return True
            if site == 'danbooru' and path.startswith('/posts/'):
                parts = [p for p in path.split('/') if p]
                post_id = parts[1] if len(parts) >= 2 else ''
                if post_id.isdigit():
                    try:
                        from PyQt6.QtCore import QThread, pyqtSignal
                        class _GetPostThread(QThread):
                            ready = pyqtSignal(dict)
                            error = pyqtSignal(str)
                            def __init__(self, api_manager, site, pid):
                                super().__init__()
                                self.api_manager = api_manager
                                self.site = site
                                self.pid = pid
                            def run(self):
                                try:
                                    from .threads.api_search_thread import _ensure_shared_loop
                                    loop = _ensure_shared_loop()
                                    import asyncio, concurrent.futures
                                    f = asyncio.run_coroutine_threadsafe(
                                        self.api_manager.get_post(self.site, self.pid), loop
                                    )
                                    try:
                                        data = f.result()
                                    except concurrent.futures.CancelledError:
                                        return
                                    except Exception as e:
                                        self.error.emit(str(e))
                                        return
                                    if isinstance(data, dict) and data:
                                        self.ready.emit(data)
                                    else:
                                        self.error.emit('empty')
                                except Exception as e:
                                    try:
                                        self.error.emit(str(e))
                                    except Exception:
                                        pass
                        t = _GetPostThread(self.api_manager, 'danbooru', post_id)
                        t.ready.connect(self._on_get_post_ready)
                        t.error.connect(self._on_get_post_error)
                        try:
                            t.finished.connect(lambda: self._cleanup_get_post_thread(t))
                        except Exception:
                            pass
                        self._get_post_threads.append(t)
                        try:
                            self.status_bar.showMessage(self.i18n.t("正在获取帖子详情..."), 2000)
                        except Exception:
                            pass
                        t.start()
                        return True
                    except Exception:
                        pass
            return False
        except Exception:
            return False

    def _on_get_post_ready(self, image_data: dict):
        try:
            self._open_viewer_single(image_data)
        except Exception:
            pass

    def _on_get_post_error(self, msg: str):
        try:
            self.status_bar.showMessage(self.i18n.t("获取帖子失败: {msg}").format(msg=msg), 3000)
        except Exception:
            pass

    def _cleanup_get_post_thread(self, thread):
        try:
            if thread in getattr(self, '_get_post_threads', []):
                self._get_post_threads.remove(thread)
        except Exception:
            pass

    def _on_search_results(self, results: list, page: int, total_pages: int):
        """搜索结果回调（来自线程）"""
        if results:
            # 使用线程传递的准确总页数，避免越界翻页
            self.image_grid.set_images(results, page, max(1, total_pages))
            self.status_bar.showMessage(self.i18n.t("找到 {count} 张图片").format(count=len(results)))
        else:
            self.image_grid.set_images([], 1, 1)
            self.status_bar.showMessage(self.i18n.t("未找到相关图片或默认流为空"))
        # 恢复按钮与输入框状态
        try:
            if hasattr(self, 'search_button'):
                self.search_button.setEnabled(True)
                self.search_button.setText(self.i18n.t("搜索"))
            if hasattr(self, 'search_input'):
                self.search_input.setEnabled(True)
        except Exception:
            pass

    def _on_search_error(self, error: str):
        """搜索错误回调（来自线程）"""
        self.image_grid.set_images([], 1, 1)
        self.status_bar.showMessage(self.i18n.t("搜索失败: {error}").format(error=error))
        print(f"搜索错误: {error}")
        # 恢复按钮与输入框状态
        try:
            if hasattr(self, 'search_button'):
                self.search_button.setEnabled(True)
                self.search_button.setText("搜索")
            if hasattr(self, 'search_input'):
                self.search_input.setEnabled(True)
        except Exception:
            pass
    
    def load_page(self, page: int):
        """加载指定页面"""
        try:
            import time
            self._search_start_ts = time.perf_counter()
            self._first_image_reported = False
            self._last_first_ms = None
        except Exception:
            pass
        try:
            from .threads.api_search_thread import APISearchThread
            query = self.search_input.text().strip()
            site = self.site_selector.get_current_site()
            if site == "yande.re":
                site = "yandere"
            if hasattr(self, 'current_search_thread') and self.current_search_thread:
                try:
                    if self.current_search_thread.isRunning():
                        try:
                            if hasattr(self.current_search_thread, 'cancel'):
                                self.current_search_thread.cancel()
                        except Exception:
                            pass
                        if not self.current_search_thread.wait(1000):
                            self.current_search_thread.terminate()
                            self.current_search_thread.wait()
                except Exception:
                    pass
            self._last_query = query
            self._last_site = site
            self._last_page = int(page)
            self.current_search_thread = APISearchThread(self.api_manager, site, query, int(page), 20)
            self.current_search_thread.results_ready.connect(self._on_search_results)
            self.current_search_thread.error.connect(self._on_search_error)
            try:
                if hasattr(self, 'search_button'):
                    self.search_button.setEnabled(False)
                    self.search_button.setText(self.i18n.t("搜索中..."))
                if hasattr(self, 'search_input'):
                    self.search_input.setEnabled(False)
                self.status_bar.showMessage(self.i18n.t("正在加载第 {page} 页").format(page=int(page)))
            except Exception:
                pass
            self.current_search_thread.start()
        except Exception:
            pass

    def show_perf_panel(self):
        if not getattr(self, '_perf_panel', None):
            self._perf_panel = PerformancePanel(self)
            loader = getattr(self.image_grid, 'image_loader', None)
            if loader and hasattr(loader, 'cache_stats_updated'):
                loader.cache_stats_updated.connect(lambda s: self._perf_panel.update_stats(s, self._last_first_ms))
            # 初始化时立即填充统计数据，避免首次打开为空白
            try:
                stats = {}
                if loader and hasattr(loader, 'get_cache_stats'):
                    stats = dict(loader.get_cache_stats() or {})
                elif loader and hasattr(loader, 'image_loader') and hasattr(loader.image_loader, 'get_load_stats'):
                    stats = dict(loader.image_loader.get_load_stats() or {})
                elif loader and hasattr(loader, 'get_load_stats'):
                    stats = dict(loader.get_load_stats() or {})
                try:
                    self._perf_panel.update_stats(stats, self._last_first_ms)
                except Exception:
                    pass
            except Exception:
                pass
        self._perf_panel.show()
        self._perf_panel.raise_()
        self._perf_panel.activateWindow()

    def download_image(self, image_data: dict):
        try:
            ext0 = (image_data.get('file_ext') or '').lower()
            if ext0 in ['mp4', 'webm']:
                url0 = image_data.get('file_url') or image_data.get('large_file_url') or image_data.get('preview_url')
                if url0:
                    import webbrowser
                    webbrowser.open(url0)
                    return
                QMessageBox.warning(self, self.i18n.t("下载失败"), self.i18n.t("无法获取视频URL"))
                return
            base_path = self.config.get('download.path', './downloads')
            auto_rename = self.config.get('download.auto_rename', True)
            create_subfolders = self.config.get('download.create_subfolders', True)
            download_original = self.config.get('download.download_original', True)
            save_metadata = self.config.get('download.save_metadata', False)
            max_file_size_mb = int(self.config.get('download.max_file_size', 50) or 50)
            timeout = int(self.config.get('network.timeout', 30) or 30)
            max_retries = int(self.config.get('network.max_retries', 3) or 3)

            def _build_task(url: str) -> DownloadTask | None:
                if not url:
                    return None
                site = (image_data.get('site') or 'unknown').lower()
                post_id = str(image_data.get('id', 'unknown'))
                ext = (image_data.get('file_ext') or Path(url).suffix.lstrip('.').lower() or 'jpg')
                ext = ''.join(c for c in ext if c.isalnum()) or 'jpg'
                base_dir = Path(base_path).expanduser()
                if not base_dir.is_absolute():
                    base_dir = Path(self.config.app_dir) / base_dir
                save_dir = base_dir / site if create_subfolders else base_dir
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                referer = None
                pu = image_data.get('post_url') or ''
                if pu:
                    referer = pu
                else:
                    if site == 'danbooru' and post_id and post_id.isdigit():
                        referer = f'https://danbooru.donmai.us/posts/{post_id}'
                    elif site == 'konachan' and post_id and post_id.isdigit():
                        referer = f'https://konachan.net/post/show/{post_id}'
                    elif site == 'yandere' and post_id and post_id.isdigit():
                        referer = f'https://yande.re/post/show/{post_id}'
                if not referer:
                    if site == 'danbooru':
                        referer = 'https://danbooru.donmai.us'
                    elif site == 'konachan':
                        referer = 'https://konachan.net'
                    elif site == 'yandere':
                        referer = 'https://yande.re'
                if referer:
                    headers['Referer'] = referer
                proxies = None
                if self.config.get('network.use_proxy', False):
                    host = self.config.get('network.proxy_host', '')
                    port = self.config.get('network.proxy_port', 0)
                    if host and port:
                        proxy_url = f"http://{host}:{port}"
                        proxies = {"http": proxy_url, "https": proxy_url}
                return DownloadTask(url, site, post_id, ext, save_dir, headers, proxies, timeout, max_file_size_mb, image_data)

            url_primary = image_data.get('file_url') if download_original else None
            url_fallback = image_data.get('large_file_url') or image_data.get('preview_url') or image_data.get('thumbnail_url')
            url = url_primary or url_fallback
            if not url:
                QMessageBox.warning(self, "错误", "无法获取可下载的文件URL")
                return

            task = _build_task(url)
            if not task:
                QMessageBox.warning(self, "错误", "无法创建下载任务")
                return

            progress = DownloadProgressDialog(self, i18n=self.i18n)
            ttl = self.i18n.t("下载进度") if hasattr(self, 'i18n') else "下载进度"
            filename = f"{task.site}_{task.post_id}.{task.ext}"
            progress.setup(int(image_data.get('file_size', 0) or 0), 0, ttl, filename)
            progress.show()

            dl = DownloadQueueThread([task], auto_rename, save_metadata, max_retries)
            self._single_dl_thread = dl
            progress.canceled.connect(dl.cancel)

            def _on_progress(idx, cur, total):
                if total > 0:
                    try:
                        progress.set_value(cur)
                    except Exception:
                        pass
                    try:
                        pct = (cur / total) * 100.0
                        mb_cur = cur / (1024 * 1024)
                        mb_tot = total / (1024 * 1024)
                        self.status_bar.showMessage(f"下载中 {mb_cur:.2f}/{mb_tot:.2f} MB ({pct:.0f}%)")
                    except Exception:
                        pass
                else:
                    try:
                        progress.set_text(f"已下载 {cur/(1024*1024):.2f} MB")
                        self.status_bar.showMessage(f"下载中 {cur/(1024*1024):.2f} MB")
                    except Exception:
                        pass

            def _on_finished(idx, ok, path, err):
                try:
                    progress.close()
                except Exception:
                    pass
                if ok:
                    self.status_bar.showMessage(self.i18n.t("下载完成: {file}").format(file=Path(path).name), 3000)
                    QMessageBox.information(self, self.i18n.t("完成"), self.i18n.t("已保存到:\n{path}").format(path=path))
                else:
                    if (str(err) == '403' or '403' in str(err)) and url_primary and url_fallback and (url_fallback != url_primary):
                        alt = _build_task(url_fallback)
                        if alt:
                            alt_progress = DownloadProgressDialog(self, i18n=self.i18n)
                            alt_progress.setup(int(image_data.get('file_size', 0) or 0), 0, ttl, f"{alt.site}_{alt.post_id}.{alt.ext}")
                            alt_progress.show()
                            dl2 = DownloadQueueThread([alt], auto_rename, save_metadata, max_retries)
                            self._single_dl_thread = dl2
                            alt_progress.canceled.connect(dl2.cancel)
                            dl2.task_progress.connect(lambda i,c,t: (_on_progress(i,c,t), alt_progress.set_value(c) if t>0 else alt_progress.set_text(f"已下载 {c/(1024*1024):.2f} MB")))
                            dl2.task_finished.connect(lambda i,ok2,p2,e2: (
                                alt_progress.close(),
                                QMessageBox.information(self, self.i18n.t("完成"), self.i18n.t("已保存到:\n{path}").format(path=p2)) if ok2 else QMessageBox.warning(self, self.i18n.t("下载失败"), self.i18n.t("错误: {msg}").format(msg=str(e2)))
                            ))
                            dl2.start()
                            return
                    QMessageBox.warning(self, self.i18n.t("下载失败"), self.i18n.t("错误: {msg}").format(msg=str(err)))

            dl.task_progress.connect(_on_progress)
            dl.task_finished.connect(_on_finished)
            dl.start()
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t("下载失败"), self.i18n.t("错误: {msg}").format(msg=str(e)))

class PerformancePanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("性能面板")
        self._parent = parent
        layout = QVBoxLayout(self)
        self.l1 = QLabel("")
        self.l2 = QLabel("")
        self.l3 = QLabel("")
        layout.addWidget(self.l1)
        layout.addWidget(self.l2)
        layout.addWidget(self.l3)

        from PyQt6.QtWidgets import QHBoxLayout, QSlider, QCheckBox, QPushButton
        ctrl_row1 = QHBoxLayout()
        ctrl_row2 = QHBoxLayout()

        ctrl_row1.addWidget(QLabel("并发上限"))
        self.concurrency_slider = QSlider(Qt.Orientation.Horizontal)
        self.concurrency_slider.setMinimum(1)
        self.concurrency_slider.setMaximum(32)
        self.concurrency_slider.setTickInterval(1)
        self.concurrency_slider.setSingleStep(1)
        self.concurrency_label = QLabel("-")
        ctrl_row1.addWidget(self.concurrency_slider)
        ctrl_row1.addWidget(self.concurrency_label)
        self.btn_apply = QPushButton("确定")
        ctrl_row2.addWidget(self.btn_apply)

        layout.addLayout(ctrl_row1)
        layout.addLayout(ctrl_row2)
        self.resize(420, 220)

        self._bind_loader()
        self.concurrency_slider.valueChanged.connect(self._on_concurrency_changed)
        self.btn_apply.clicked.connect(self._on_apply_concurrency)

    def _bind_loader(self):
        self._loader = None
        try:
            self._loader = getattr(self._parent.image_grid, 'image_loader', None)
        except Exception:
            self._loader = None
        # 初始化滑块值
        try:
            if self._loader:
                base = None
                if hasattr(self._loader, 'image_loader') and hasattr(self._loader.image_loader, 'get_max_concurrent'):
                    base = int(self._loader.image_loader.get_max_concurrent())
                elif hasattr(self._loader, 'get_max_concurrent'):
                    base = int(self._loader.get_max_concurrent())
                if base:
                    self.concurrency_slider.setValue(max(1, min(16, base)))
                    self.concurrency_label.setText(str(base))
        except Exception:
            pass

    def _on_concurrency_changed(self, v: int):
        self.concurrency_label.setText(str(int(v)))

    def _on_pause_toggled(self, checked: bool):
        try:
            if self._loader and hasattr(self._loader, 'set_paused'):
                self._loader.set_paused(bool(checked))
        except Exception:
            pass

    def _on_apply_concurrency(self):
        try:
            if not self._loader:
                return
            v = int(self.concurrency_slider.value())
            if hasattr(self._loader, 'image_loader') and hasattr(self._loader.image_loader, 'set_max_concurrent'):
                self._loader.image_loader.set_max_concurrent(v)
            elif hasattr(self._loader, 'set_max_concurrent'):
                self._loader.set_max_concurrent(v)
            try:
                if hasattr(self._loader, 'base_max_concurrent'):
                    self._loader.base_max_concurrent = v
            except Exception:
                pass
        except Exception:
            pass

    

    def update_stats(self, stats: dict, first_ms):
        try:
            active = int(stats.get('active_loads', 0))
            maxc = int(stats.get('max_concurrent', 0))
            pending = int(stats.get('pending_loads', 0))
            qsize = int(stats.get('preload_queue_size', 0))
            hit = float(stats.get('cache_hit_rate', 0.0))
            avg_ms = float(stats.get('avg_load_ms', 0.0))
            loaded = int(stats.get('loaded_count', 0))
            cancel = int(stats.get('cancel_count', 0))
            self.l1.setText(f"并发 {active}/{maxc} 等待 {pending} 预载 {qsize}")
            self.l2.setText(f"命中 {hit*100:.0f}% 平均 {avg_ms:.0f}ms 成功 {loaded} 取消 {cancel}")
            if first_ms is not None:
                self.l3.setText(f"首图 {first_ms:.0f}ms")
            # 跟随实际并发上限更新滑块显示（不改变用户拖动过程的即时反馈）
            if maxc > 0 and self.concurrency_slider.value() != maxc:
                self.concurrency_slider.blockSignals(True)
                self.concurrency_slider.setValue(max(1, min(16, maxc)))
                self.concurrency_label.setText(str(maxc))
                self.concurrency_slider.blockSignals(False)
        except Exception:
            pass
    
    
    def show_image_viewer_from_grid(self, grid_widget: ImageGridWidget, image_data: dict):
        """从指定图片网格打开图片查看器（用于收藏页子网格）。"""
        from .widgets.image_viewer import ImageViewerDialog
        images = []
        try:
            images = list(getattr(grid_widget, 'current_images', []) or [])
        except Exception:
            images = []
        cur_idx = 0
        try:
            cur_id = image_data.get('id')
            cur_site = image_data.get('site')
            cur_idx = next((i for i, it in enumerate(images)
                            if it.get('id') == cur_id and it.get('site') == cur_site), 0)
        except Exception:
            cur_idx = 0

        # 作为独立顶层窗口创建（不绑定父窗口），避免总在主窗口之上
        viewer = ImageViewerDialog(image_data, None, images_list=images, current_index=cur_idx)
        viewer.favorite_toggled.connect(self.on_favorite_toggled)
        viewer.download_requested.connect(self.download_image)
        viewer.tag_clicked.connect(self.on_viewer_tag_clicked)
        # 显示为独立窗口而不是模态对话框
        viewer.show()
        # 保存引用以防止被垃圾回收
        if not hasattr(self, 'image_viewers'):
            self.image_viewers = []
        self.image_viewers.append(viewer)
        # 窗口销毁后从列表中移除，避免残留引用
        try:
            viewer.destroyed.connect(self._on_viewer_destroyed)
        except Exception:
            pass
    
    def add_to_favorites(self, image_data: dict):
        """添加到默认收藏夹，并按站点分组展示"""
        try:
            favorite_id = self._get_default_favorite_id()
            img_id = str(image_data.get('id'))
            site = (image_data.get('site') or 'unknown').lower()
            success = self.db_manager.add_image_to_favorite(favorite_id, img_id, site, image_data)
            if success:
                self.status_bar.showMessage("已添加到收藏夹：默认收藏夹", 2000)
            else:
                self.status_bar.showMessage("该图片已在收藏夹中", 2000)
            # 若当前在收藏夹页，刷新显示
            self._refresh_favorites_if_active()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加到收藏夹失败：{str(e)}")

    def remove_from_favorites(self, image_data: dict):
        try:
            img_id = str(image_data.get('id'))
            site = (image_data.get('site') or 'unknown').lower()
            try:
                cnt = self.db_manager.remove_image_global(img_id, site)
                if cnt > 0:
                    self.status_bar.showMessage("已从收藏夹移除", 2000)
                else:
                    fav_id = self._get_site_default_fav_id(site) or self._get_default_favorite_id()
                    self.db_manager.remove_image_from_favorite(fav_id, img_id, site)
                    self.status_bar.showMessage("已从收藏夹移除", 2000)
            except Exception:
                fav_id = self._get_site_default_fav_id(site) or self._get_default_favorite_id()
                self.db_manager.remove_image_from_favorite(fav_id, img_id, site)
                self.status_bar.showMessage("已从收藏夹移除", 2000)
            self._refresh_favorites_if_active()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"移除收藏失败：{str(e)}")
    
    def on_favorite_toggled(self, image_data: dict, is_favorite: bool):
        """收藏状态切换：支持本地与在线，并按站点记住默认"""
        site = (image_data.get('site') or 'unknown').lower()
        if site == 'unknown':
            site = 'danbooru'
        if is_favorite:
            # 选择收藏目标（若已记住默认会直接返回）
            sel = self._choose_favorite_destination(site)
            if not sel:
                return
            if sel.get('destination') == 'local':
                fav_id = sel.get('folder_id') or self._get_default_favorite_id()
                try:
                    img_id = str(image_data.get('id'))
                    self.db_manager.add_image_to_favorite(fav_id, img_id, site, image_data)
                    self.status_bar.showMessage("已添加到本地收藏夹", 2000)
                    self._refresh_favorites_if_active()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加到本地收藏夹失败：{str(e)}")
            else:
                # 在线收藏（当前支持 Danbooru）
                post_id = str(image_data.get('id'))
                self._start_online_fav_op(site, 'add', post_id)
        else:
            # 取消收藏：根据站点默认目的地执行
            dest = self._get_site_dest_default(site)
            if dest == 'local':
                fav_id = self._get_site_default_fav_id(site) or self._get_default_favorite_id()
                try:
                    img_id = str(image_data.get('id'))
                    self.db_manager.remove_image_from_favorite(fav_id, img_id, site)
                    self.status_bar.showMessage("已从本地收藏夹移除", 2000)
                    self._refresh_favorites_if_active()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"移除本地收藏失败：{str(e)}")
            else:
                post_id = str(image_data.get('id'))
                self._start_online_fav_op(site, 'remove', post_id)
    
    # 侧栏已移除，不再有文件夹选择事件

    def _get_default_favorite_id(self) -> int:
        """获取或创建默认收藏夹ID"""
        favorites = self.db_manager.get_favorites()
        for fav in favorites:
            if fav.get('name') == '默认收藏夹':
                return fav.get('id')
        # 不存在则创建
        try:
            return self.db_manager.create_favorite('默认收藏夹', '合并收藏，按站点分组')
        except Exception:
            # 回退：若创建失败，尝试使用第一个收藏夹
            return favorites[0]['id'] if favorites else self.db_manager.create_favorite('默认收藏夹')

    def _load_favorites_into_tabs(self):
        """根据来源选择加载收藏夹数据到各站点选项卡（每站点独立本地收藏夹）"""
        try:
            source = self.fav_source
            # 按站点分别读取本地收藏夹ID
            local_grouped = {key: [] for _, key in self.site_tabs}
            try:
                for _, key in self.site_tabs:
                    fav_id = self._get_site_default_fav_id(key) or self._get_default_favorite_id()
                    if not fav_id:
                        continue
                    items = self.db_manager.get_favorite_images(fav_id)
                    for it in items:
                        site_key = (it.get('site') or 'unknown').lower()
                        data = it.get('image_data') or {}
                        if site_key == key:
                            local_grouped[key].append(data)
            except Exception:
                pass

            # 若选择本地，直接显示本地内容
            if source == 'local':
                for _, key in self.site_tabs:
                    grid = self.fav_grids.get(key)
                    if grid:
                        grid.set_images(local_grouped.get(key, []), 1, 1)
                return

            # 在线或合并：仅 Danbooru 支持在线收藏获取
            self._start_online_fav_fetch()
            # 先把其它站点显示为本地内容
            for _, key in self.site_tabs:
                if key != 'danbooru':
                    grid = self.fav_grids.get(key)
                    if grid:
                        grid.set_images(local_grouped.get(key, []), 1, 1)
            # Danbooru 临时显示本地，待在线结果回来后更新/合并
            grid = self.fav_grids.get('danbooru')
            if grid:
                grid.set_images(local_grouped.get('danbooru', []), 1, 1)
        except Exception as e:
            print(f"加载收藏夹失败: {e}")

    def _on_tab_changed(self, index: int):
        """标签页切换时处理收藏夹加载"""
        try:
            widget = self.tab_widget.widget(index)
            # 通过标签文本判断（简单可靠）
            tab_text = self.tab_widget.tabText(index)
            if tab_text == '收藏夹':
                self._load_favorites_into_tabs()
        except Exception:
            pass

    def _refresh_favorites_if_active(self):
        """若当前处于收藏夹页面，刷新数据"""
        try:
            current_index = self.tab_widget.currentIndex()
            if self.tab_widget.tabText(current_index) == '收藏夹':
                self._load_favorites_into_tabs()
        except Exception:
            pass

    def _on_fav_source_changed(self, idx: int):
        """收藏来源选择切换"""
        try:
            text = self.fav_source_box.currentText().strip()
            if text.startswith('本地'):
                self.fav_source = 'local'
            elif text.startswith('在线'):
                self.fav_source = 'online'
            else:
                self.fav_source = 'merge'
            self._cancel_online_fav_thread()
            self._load_favorites_into_tabs()
        except Exception:
            pass

    def _get_site_default_fav_id(self, site: str):
        try:
            data = self.config.data
            fav_def = (data.get('sites', {}).get(site, {}) or {}).get('favorite_default', {})
            return fav_def.get('folder_id')
        except Exception:
            return None

    def _get_site_dest_default(self, site: str) -> str:
        try:
            data = self.config.data
            fav_def = (data.get('sites', {}).get(site, {}) or {}).get('favorite_default', {})
            return fav_def.get('destination', 'local')
        except Exception:
            return 'local'

    def _set_site_fav_default(self, site: str, destination: str, folder_id):
        try:
            sites = self.config.data.setdefault('sites', {})
            site_cfg = sites.setdefault(site, {})
            fav_def = site_cfg.setdefault('favorite_default', {})
            fav_def['destination'] = destination
            fav_def['folder_id'] = folder_id
            self.config.save()
        except Exception:
            pass

    def _choose_favorite_destination(self, site: str):
        # 若已有默认，直接返回
        try:
            dest = self._get_site_dest_default(site)
            folder_id = self._get_site_default_fav_id(site)
            if dest == 'online' or (dest == 'local' and folder_id):
                return {'destination': dest, 'folder_id': folder_id, 'remember': False}
        except Exception:
            pass
        # 弹窗选择
        dlg = FavoriteDestinationDialog(site, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = dlg.get_selection()
            if sel.get('remember'):
                self._set_site_fav_default(site, sel.get('destination'), sel.get('folder_id'))
            return sel
        return None

    def _start_online_fav_op(self, site: str, op: str, post_id: str):
        try:
            th = getattr(self, '_online_fav_thread', None)
            if th and th.isRunning():
                try:
                    th.finished_ok.disconnect()
                    th.error.disconnect()
                except Exception:
                    pass
        except Exception:
            pass
        th = OnlineFavoriteOpThread(self.api_manager, site, op, post_id)
        th.finished_ok.connect(lambda ok: self.status_bar.showMessage('在线收藏已更新' if ok else '在线收藏更新失败', 3000))
        th.error.connect(lambda m: self.status_bar.showMessage(f'在线收藏操作错误：{m}', 5000))
        self._online_fav_thread = th
        th.start()

    def _start_online_fav_fetch(self):
        """启动在线收藏获取（仅 Danbooru）"""
        try:
            # 简单凭据检查
            username = self.config.get('sites.danbooru.username', '')
            api_key = self.config.get('sites.danbooru.api_key', '')
            if not username or not api_key:
                # 无凭据时提示，但继续显示本地内容
                self.status_bar.showMessage("Danbooru 在线收藏：请登录并配置用户名与API Key", 4000)
                return
        except Exception:
            pass

        # 取消旧线程
        self._cancel_online_fav_thread()
        try:
            thread = FavoritesFetchThread(self.api_manager, 'danbooru', page=1, limit=40)
            thread.favorites_ready.connect(self._on_online_fav_ready)
            thread.error.connect(self._on_online_fav_error)
            self.current_fav_thread = thread
            self.fav_source_box.setEnabled(False)
            self.status_bar.showMessage("正在获取 Danbooru 在线收藏...", 2000)
            thread.start()
        except Exception as e:
            self.status_bar.showMessage(f"启动在线收藏线程失败：{e}", 4000)

    def _on_online_fav_ready(self, results: list):
        """在线收藏获取完成，更新 Danbooru 网格"""
        try:
            # 拿到当前本地内容（用于合并模式）
            local_images = []
            grid = self.fav_grids.get('danbooru')
            if grid:
                try:
                    local_images = list(grid.current_images)
                except Exception:
                    local_images = []

            final_images = results or []
            if self.fav_source == 'merge':
                # 合并去重（按 id）
                seen = set()
                merged = []
                for it in (local_images + final_images):
                    iid = str(it.get('id')) + '@' + (it.get('site') or 'danbooru')
                    if iid not in seen:
                        seen.add(iid)
                        merged.append(it)
                final_images = merged

            if grid:
                grid.set_images(final_images, 1, 1)
            self.status_bar.showMessage("Danbooru 在线收藏已更新", 2000)
        except Exception as e:
            self.status_bar.showMessage(f"更新在线收藏失败：{e}", 4000)
        finally:
            self.fav_source_box.setEnabled(True)
            self._cancel_online_fav_thread()

    def _on_online_fav_error(self, msg: str):
        """在线收藏获取错误"""
        try:
            self.status_bar.showMessage(f"获取在线收藏失败：{msg}", 4000)
        except Exception:
            pass
        finally:
            self.fav_source_box.setEnabled(True)
            self._cancel_online_fav_thread()

    def _cancel_online_fav_thread(self):
        """取消并清理当前在线收藏线程"""
        try:
            th = getattr(self, 'current_fav_thread', None)
            if th:
                try:
                    th.cancel()
                except Exception:
                    pass
                try:
                    if th.isRunning():
                        th.wait(500)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.current_fav_thread = None
    
    
    def refresh_content(self):
        """刷新内容"""
        # 重新执行当前搜索
        self.perform_search()

    def copy_current_image_link(self):
        """复制当前选中图片链接到剪贴板"""
        try:
            if hasattr(self, 'image_grid') and self.image_grid:
                img = self.image_grid.get_selected_image()
                if not img:
                    self.status_bar.showMessage(self.i18n.t("请先选择一张图片"), 2000)
                    return
                url = img.get('file_url') or img.get('preview_url') or img.get('thumbnail_url')
                if not url:
                    self.status_bar.showMessage(self.i18n.t("该图片无可用链接"), 2000)
                    return
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(url)
                self.status_bar.showMessage(self.i18n.t("已复制链接到剪贴板"), 2000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("复制链接失败: {msg}").format(msg=str(e)), 3000)

    def open_downloads_dir(self):
        """打开下载目录"""
        try:
            base_path = self.config.get('download.path', './downloads')
            path = Path(base_path).expanduser()
            if not path.is_absolute():
                path = Path(self.config.app_dir) / path
            path.mkdir(parents=True, exist_ok=True)
            # Windows 优先使用系统方法打开
            try:
                if os.name == 'nt':
                    os.startfile(str(path))
                else:
                    from PyQt6.QtGui import QDesktopServices
                    from PyQt6.QtCore import QUrl
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            except Exception:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            self.status_bar.showMessage(self.i18n.t("已打开下载目录: {dir}").format(dir=str(path)), 3000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("打开下载目录失败: {msg}").format(msg=str(e)), 3000)

    def open_cache_dir(self):
        """打开图片缓存目录"""
        try:
            path = getattr(self.cache_manager, 'cache_dir', None) or self.config.cache_dir
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            if os.name == 'nt':
                os.startfile(str(path))
            else:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            self.status_bar.showMessage(self.i18n.t("已打开图片缓存目录: {dir}").format(dir=str(path)), 3000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("打开缓存目录失败: {msg}").format(msg=str(e)), 3000)

    def open_thumbnails_dir(self):
        """打开缩略图目录"""
        try:
            path = Path(getattr(self.cache_manager, 'thumbnails_dir', self.config.thumbnails_dir))
            path.mkdir(parents=True, exist_ok=True)
            if os.name == 'nt':
                os.startfile(str(path))
            else:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            self.status_bar.showMessage(self.i18n.t("已打开缩略图目录: {dir}").format(dir=str(path)), 3000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("打开缩略图目录失败: {msg}").format(msg=str(e)), 3000)

    def open_config_file(self):
        """打开配置文件"""
        try:
            path = Path(self.config.config_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                self.config.save_config()
            if os.name == 'nt':
                os.startfile(str(path))
            else:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            self.status_bar.showMessage(self.i18n.t("已打开配置文件: {file}").format(file=str(path)), 3000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("打开配置文件失败: {msg}").format(msg=str(e)), 3000)

    def clear_image_cache(self):
        """清理图片磁盘与内存缓存"""
        try:
            self.cache_manager.clear_all_cache()
            self.status_bar.showMessage(self.i18n.t("已清理图片缓存"), 3000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("清理图片缓存失败: {msg}").format(msg=str(e)), 3000)

    def clear_thumbnail_cache(self):
        """清理缩略图缓存"""
        try:
            self.cache_manager.clear_thumbnails()
            self.status_bar.showMessage(self.i18n.t("已清理缩略图缓存"), 3000)
        except Exception as e:
            self.status_bar.showMessage(self.i18n.t("清理缩略图缓存失败: {msg}").format(msg=str(e)), 3000)

    def switch_to_tab(self, tab_text: str):
        """切换到指定标签页"""
        try:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_text:
                    self.tab_widget.setCurrentIndex(i)
                    # 若是收藏夹，确保内容刷新
                    if tab_text == self.i18n.t("收藏夹"):
                        self._load_favorites_into_tabs()
                    break
        except Exception:
            pass
    
    def on_site_changed(self, site: str):
        """网站切换"""
        self.status_bar.showMessage(f"已切换到: {site}")
        # 切换站点后自动加载默认内容（如果搜索框为空则为默认流）
        self.perform_search()
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def show_account_management_dialog(self):
        """显示账号管理页面"""
        dialog = AccountManagementDialog(self)
        # 应用主题
        try:
            current_theme = self.theme_manager.get_current_theme()
            self.theme_manager.apply_theme(current_theme, dialog)
        except Exception:
            pass
        # 连接登录成功与登出请求
        dialog.login_success.connect(self.on_login_success)
        dialog.logout_requested.connect(self.logout_from_site)
        dialog.exec()
    
    def on_login_success(self, site: str, user_info: dict):
        """登录成功处理"""
        # 创建会话
        session_id = self.session_manager.create_session(
            site=site,
            user_info=user_info,
            remember=True  # 默认记住登录状态
        )
        
        self.status_bar.showMessage(f"已登录到 {site} - 欢迎 {user_info.get('username', '')}")
        
        # 更新 API 管理器的认证凭据并保存到配置
        try:
            site_key = site.lower()
            creds = {'username': user_info.get('username', '')}
            if site_key == 'danbooru':
                api_key = user_info.get('api_key', '')
                if api_key:
                    creds['api_key'] = api_key
            elif site_key in ('konachan', 'yande.re'):
                password = user_info.get('password', '')
                api_key = user_info.get('api_key', '')
                if password:
                    creds['password'] = password
                if api_key:
                    creds['api_key'] = api_key
            # 仅在有关键字段时更新
            if any(k in creds and creds[k] for k in ('api_key', 'password')) or creds.get('username'):
                self.api_manager.update_credentials(site, creds)
        except Exception:
            # 忽略凭据更新异常，不影响会话与UI
            pass
        
        # 刷新界面状态
        self.update_ui_for_login_state(site, user_info)

        # 将站点选择器切换到刚登录的网站，并加载默认内容
        try:
            self.site_selector.set_current_site(site)
        except Exception:
            pass
        # 清空搜索框，触发默认内容搜索
        self.search_input.setText("")
        self.perform_search()
    
    def update_ui_for_login_state(self, site: str, user_info: dict):
        """更新界面的登录状态"""
        # 简化：不再在工具栏显示登录状态，仅通过状态栏提示
        username = user_info.get('username', '')
        self.status_bar.showMessage(self.i18n.t("已登录到 {site} - 欢迎 {username}").format(site=site, username=username))
    
    def logout_from_site(self, site: str):
        """从指定网站登出"""
        # 删除会话
        user_info = self.session_manager.get_user_info(site)
        if user_info:
            user_id = user_info.get('user_id', user_info.get('username', ''))
            self.session_manager.delete_session(site, user_id)
        
        # 状态栏提示
        self.status_bar.showMessage(self.i18n.t("已从 {site} 登出").format(site=site))
    
    def check_existing_sessions(self):
        """检查现有会话并更新界面"""
        active_sessions = self.session_manager.get_all_active_sessions()
        if active_sessions:
            # 如果有活跃会话，显示第一个
            session = list(active_sessions.values())[0]
            site = session['site']
            user_info = session['user_info']
            self.update_ui_for_login_state(site, user_info)
    
    def show_settings_dialog(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self.config, self)
        # 应用当前主题到设置对话框
        current_theme = self.theme_manager.get_current_theme()
        self.theme_manager.apply_theme(current_theme, dialog)
        try:
            dialog.settings_changed.connect(self.apply_settings)
        except Exception:
            pass
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            # 应用设置更改
            self.apply_settings()
    
    def apply_settings(self):
        """应用设置更改"""
        theme = self.config.get('appearance.theme', 'win11')
        self.apply_theme(theme)

        try:
            lang = self.config.get('appearance.language', 'zh_CN')
            self.i18n.set_language(lang)
            self.menuBar().clear()
            self.create_menu_bar()
        except Exception:
            pass
        self.update()
        try:
            self.status_bar.showMessage(self.i18n.t("设置已应用"))
        except Exception:
            self.status_bar.showMessage("设置已应用")
    
    def apply_theme(self, theme: str):
        """应用主题"""
        self.theme_manager.apply_theme(theme, self)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            self.save_geometry()
        except Exception:
            event.accept()
            return
        
        # 关闭所有图片查看器窗口
        try:
            if hasattr(self, 'image_viewers'):
                for viewer in self.image_viewers[:]:  # 使用切片复制避免修改列表时出错
                    if viewer and not viewer.isHidden():
                        viewer.close()
                self.image_viewers.clear()
        except Exception:
            pass
        
        try:
            if hasattr(self, 'current_search_thread') and self.current_search_thread:
                if self.current_search_thread.isRunning():
                    # 先尝试正常退出并等待片刻
                    self.current_search_thread.quit()
                    if not self.current_search_thread.wait(500):
                        # 若未能在短时间内退出，则强制终止并等待
                        self.current_search_thread.terminate()
                        self.current_search_thread.wait()
        except Exception:
            pass
        
        # 取消网格中的所有图片加载
        try:
            if hasattr(self, 'image_grid') and self.image_grid and hasattr(self.image_grid, 'image_loader'):
                self.image_grid.image_loader.cancel_all()
        except Exception:
            pass

        try:
            for t in list(getattr(self, '_bg_threads', [])):
                try:
                    t.requestInterruption()
                except Exception:
                    pass
                try:
                    t.quit()
                    if not t.wait(500):
                        t.terminate()
                        t.wait()
                except Exception:
                    try:
                        t.terminate()
                        t.wait()
                    except Exception:
                        pass
            self._bg_threads.clear()
        except Exception:
            pass
        # 关闭 API 层的连接池与可能存在的会话
        try:
            if hasattr(self, 'api_manager') and self.api_manager:
                self.api_manager.shutdown()
        except Exception:
            pass
        
        event.accept()
    def on_viewer_tag_clicked(self, tag: str):
        """图片查看器标签点击：执行搜索"""
        # 支持 Ctrl+点击 将标签追加到现有查询；否则直接替换并搜索
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            modifiers = QApplication.keyboardModifiers()
        except Exception:
            modifiers = None

        if hasattr(self, 'search_input'):
            base = self.search_input.text().strip()
            if modifiers and (modifiers & Qt.KeyboardModifier.ControlModifier):
                query = (f"{base} {tag}" if base else tag).strip()
            else:
                query = tag
            self.search_input.setText(query)
            # 主窗口前置到最前，确保用户可见
            try:
                # 若主窗口被最小化，先恢复
                if self.windowState() & Qt.WindowState.WindowMinimized:
                    self.showNormal()
                # 激活并前置
                self.activateWindow()
                # PyQt 方法名为 raise_()
                self.raise_()
            except Exception:
                pass
            self.perform_search()

    def _remove_viewer_instance(self, viewer):
        """从管理列表中移除已销毁的查看器实例"""
        try:
            if hasattr(self, 'image_viewers') and viewer in self.image_viewers:
                self.image_viewers.remove(viewer)
        except Exception:
            pass

    def batch_download_current_page(self):
        """批量下载当前页图片"""
        try:
            images = list(getattr(self.image_grid, 'current_images', []) or [])
        except Exception:
            images = []
        if not images:
            try:
                self.status_bar.showMessage(self.i18n.t("当前页无图片"), 3000)
            except Exception:
                pass
            return
        try:
            dlg = BatchDownloadDialog(self, images, i18n=self.i18n, config=self.config)
            dlg.show()
        except Exception as e:
            try:
                QMessageBox.warning(self, "错误", f"批量下载窗口打开失败：{str(e)}")
            except Exception:
                pass
            try:
                progress.close()
            except Exception:
                pass
    def _fetch_tags_remote(self, query: str, on_done):
        try:
            s = self.site_selector.get_current_site()
            if s in ('yande.re', 'yande'):
                s = 'yandere'
            t = TagsQueryThread(self.api_manager, s, query, limit=120)
            t.tags_ready.connect(lambda tags, ss=s: self._on_remote_tags(ss, tags, on_done))
            t.error.connect(lambda msg: on_done([]))
            t.start()
            # 保持引用以便生命周期管理
            if not hasattr(self, '_tag_query_threads'):
                self._tag_query_threads = []
            self._tag_query_threads.append(t)
        except Exception:
            try:
                on_done([])
            except Exception:
                pass

    def _on_remote_tags(self, site: str, tags: list, on_done):
        try:
            existed = {t.get('name') for t in self._tag_cache.get(site, [])}
            merged = list(self._tag_cache.get(site, []))
            for t in (tags or []):
                n = t.get('name')
                if n and n not in existed:
                    merged.append({'name': n, 'count': int(t.get('count') or 0), 'type': t.get('type')})
            self._tag_cache[site] = merged
        except Exception:
            pass
        try:
            on_done(tags or [])
        except Exception:
            pass
