from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QTimer, QPoint, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation
import re
import heapq
import time

class TagSuggest:
    def __init__(self, parent, i18n=None):
        self.parent = parent
        self.i18n = i18n
        self.popup = QListWidget(parent)
        self.popup.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.popup.setMouseTracking(True)
        self.popup.setMinimumWidth(280)
        self.popup.itemClicked.connect(self._on_item_clicked)
        self.tags = []
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._update_now)
        self._line = None
        self.max_items = 15
        self._debounce_interval_ms = 80
        self._last_input = ""
        self._pool_items = []
        self._loading = False
        self._chunk_timer = QTimer()
        self._chunk_timer.setSingleShot(True)
        self._chunk_timer.timeout.connect(self._process_chunk)
        self._cur_query = ""
        self._heap = []
        self._scan_index = 0
        self._scan_start_ms = 0.0
        # 平滑显示/隐藏动画
        self._opacity = QGraphicsOpacityEffect(self.popup)
        self.popup.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(80)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._visible = False
        self._remote_fetcher = None
        try:
            self.popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        except Exception:
            pass
        self.popup.setStyleSheet(
            """
            QListWidget { background: #133a6b; color: #fff; border: 1px solid #1f4a86; }
            QListWidget::item { height: 28px; padding: 4px 8px; }
            QListWidget::item:selected { background: #1c5aa6; }
            QListWidget::item:!enabled { color: #9bb2cc; }
            """
        )

    def attach(self, line_edit):
        self._line = line_edit
        line_edit.textChanged.connect(self._on_text_changed)
        line_edit.installEventFilter(self.parent)
        for _ in range(self.max_items):
            it = QListWidgetItem("")
            self.popup.addItem(it)
            it.setHidden(True)
            self._pool_items.append(it)
        self._loading_item = QListWidgetItem("正在加载...")
        self._loading_item.setFlags(self._loading_item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
        self.popup.addItem(self._loading_item)
        self._loading_item.setHidden(True)

    def set_tags(self, tags):
        self.tags = list(tags or [])

    def set_remote_fetcher(self, fetcher):
        # fetcher: callable(query: str, on_done: callable(list))
        self._remote_fetcher = fetcher

    def _score(self, name, count, query):
        n = name.lower()
        q = query.lower()
        if not q:
            return (False, False, -1, 0.0)
        perfect = (n == q)
        prefix = n.startswith(q)
        pos = n.find(q)
        if pos < 0:
            return (False, False, -1, 0.0)
        weight = (max(1, int(count)) ** 0.5) / 100.0
        return (perfect, prefix, pos, weight)

    @staticmethod
    def _sanitize_query(text: str) -> str:
        # 仅对最后一个 token 进行匹配，过滤特殊字符；保留常见的 tag 字符
        base = (text or '').strip()
        if not base:
            return ''
        tokens = re.split(r"\s+", base)
        last = tokens[-1]
        last = re.sub(r"[^a-zA-Z0-9_:\-]", "", last)
        return last

    @staticmethod
    def match(tags, query_text, max_items=15):
        q = TagSuggest._sanitize_query(query_text)
        if len(q) < 1:
            return []
        items = []
        qq = q.lower()
        for t in list(tags or []):
            name = (t.get('name') or '')
            cnt = int(t.get('count') or 0)
            n = name.lower()
            pos = n.find(qq)
            if pos < 0:
                continue
            perfect = (n == qq)
            prefix = n.startswith(qq)
            weight = (max(1, cnt) ** 0.5) / 100.0
            items.append((perfect, prefix, pos, -cnt, name, weight))
        # 排序：完全匹配优先；前缀匹配优先；出现位置越靠前越优；热度越高越优；字典序稳定
        items.sort(key=lambda x: (
            not x[0],           # perfect False 后置
            not x[1],           # prefix False 后置
            x[2],               # pos 小优先
            x[3],               # -count 小优先（即 count 大优先）
            x[4]
        ))
        out = []
        for it in items[:max_items]:
            out.append({'name': it[4], 'count': int(-it[3]), 'score': float(it[5]), 'pos': int(it[2]), 'perfect': bool(it[0]), 'prefix': bool(it[1])})
        return out

    def _format_count(self, c):
        try:
            n = int(c or 0)
        except Exception:
            n = 0
        if n >= 1000:
            return f"{n//1000}k"
        return str(n)

    def _on_text_changed(self, text):
        self._last_input = text
        if len(text) < 1:
            self.hide()
            return
        try:
            self._chunk_timer.stop()
        except Exception:
            pass
        self._debounce.start(self._debounce_interval_ms)

    def _update_now(self):
        q = self._last_input
        q_san = self._sanitize_query(q)
        if len(q_san) < 1:
            self.hide()
            return
        self._cur_query = q_san
        self._heap = []
        self._scan_index = 0
        self._scan_start_ms = time.perf_counter()
        self._show_loading()
        self._chunk_timer.start(0)
        self._position_popup()
        self._show_popup()
        try:
            self.popup.clearSelection()
        except Exception:
            pass

    def _process_chunk(self):
        budget_ms = 14.0
        t0 = time.perf_counter()
        qq = self._cur_query.lower()
        maxn = self.max_items
        n_tags = len(self.tags)
        while self._scan_index < n_tags:
            t = self.tags[self._scan_index]
            self._scan_index += 1
            name = (t.get('name') or '')
            cnt = int(t.get('count') or 0)
            n = name.lower()
            pos = n.find(qq)
            if pos >= 0:
                perfect = (n == qq)
                prefix = n.startswith(qq)
                # 构造“越大越好”的排名键（用于容量受限的最小堆）
                rank = (1 if perfect else 0, 1 if prefix else 0, -pos, cnt, name)
                item = {'name': name, 'count': cnt, 'pos': pos, 'perfect': perfect, 'prefix': prefix}
                if len(self._heap) < maxn:
                    heapq.heappush(self._heap, (rank, item))
                else:
                    # 根是当前保留集合中的“最差”项（rank 最小），新项更好则替换
                    if rank > self._heap[0][0]:
                        heapq.heapreplace(self._heap, (rank, item))
            if (time.perf_counter() - t0) * 1000.0 >= budget_ms:
                self._chunk_timer.start(0)
                return
        self._render_heap_results()
        try:
            # 若本地结果过少，触发远端补充
            if self._remote_fetcher and len(self._heap) <= max(1, self.max_items // 4):
                self._remote_fetcher(self._cur_query, self._apply_remote_results)
        except Exception:
            pass

    def _render_heap_results(self):
        self.popup.setUpdatesEnabled(False)
        try:
            # 排序 heap（按排名降序展示）
            items = [it for (_, it) in sorted(self._heap, key=lambda kv: kv[0], reverse=True)]
            used = 0
            for used in range(min(len(items), len(self._pool_items))):
                r = items[used]
                it = self._pool_items[used]
                it.setText(f"{r['name']}    {self._format_count(r['count'])}")
                it.setData(Qt.ItemDataRole.UserRole, {'name': r['name'], 'count': int(r['count']), 'pos': int(r['pos'])})
                it.setHidden(False)
            for j in range(used + 1, len(self._pool_items)):
                self._pool_items[j].setHidden(True)
            self._loading_item.setHidden(True)
            if used == 0:
                self._loading_item.setText("无匹配结果")
                self._loading_item.setHidden(False)
            self._position_popup(items_count=used)
            self._show_popup()
            try:
                self.popup.clearSelection()
            except Exception:
                pass
        finally:
            self.popup.setUpdatesEnabled(True)

    def _show_loading(self):
        self.popup.setUpdatesEnabled(False)
        try:
            for it in self._pool_items:
                it.setHidden(True)
            self._loading_item.setText("正在加载...")
            self._loading_item.setHidden(False)
        finally:
            self.popup.setUpdatesEnabled(True)

    def _position_popup(self, items_count: int | None = None):
        try:
            rect = self._line.geometry()
            gpos = self._line.mapToGlobal(QPoint(0, rect.height()))
            # SubWindow 需要父坐标；若为顶级窗口（Popup）则直接用全局坐标
            flags = self.popup.windowFlags()
            if flags & Qt.WindowType.SubWindow:
                ppos = self.parent.mapFromGlobal(gpos) if self.parent else gpos
                self.popup.move(ppos)
            else:
                self.popup.move(gpos)
            cnt = items_count if items_count is not None else max(1, self.popup.count())
            self.popup.resize(max(rect.width(), 280), min(300, 28 * max(1, cnt) + 8))
        except Exception:
            pass

    def _show_popup(self):
        try:
            if not self._visible:
                self._opacity.setOpacity(0.0)
                self.popup.show()
                self._anim.stop()
                self._anim.setDirection(QPropertyAnimation.Direction.Forward)
                self._anim.start()
                self._visible = True
            else:
                # 已可见时仅更新内容与大小，不重启动画
                if not self.popup.isVisible():
                    self.popup.show()
                self._opacity.setOpacity(1.0)
        except Exception:
            try:
                self.popup.show()
            except Exception:
                pass

    def hide(self):
        try:
            if self._visible and self.popup.isVisible():
                self._anim.stop()
                # 快速淡出不阻塞输入
                self._anim.setDirection(QPropertyAnimation.Direction.Backward)
                self._anim.start()
            self.popup.hide()
            self._visible = False
        except Exception:
            try:
                self.popup.hide()
            except Exception:
                pass

    def _apply_remote_results(self, results: list):
        try:
            # 合并到本地缓存并刷新显示
            existed = {t.get('name') for t in self.tags}
            for t in (results or []):
                n = t.get('name')
                if n and n not in existed:
                    self.tags.append({'name': n, 'count': int(t.get('count') or 0), 'type': t.get('type')})
                    existed.add(n)
        except Exception:
            pass
        try:
            # 重新更新当前查询
            self._update_now()
        except Exception:
            pass

    def hide(self):
        try:
            self.popup.hide()
        except Exception:
            pass

    def handle_key(self, event):
        if not self.popup.isVisible():
            return False
        if event.key() == Qt.Key.Key_Tab:
            r = self.popup.currentRow()
            r = (r + 1) % self.popup.count()
            self.popup.setCurrentRow(r)
            return True
        if event.key() == Qt.Key.Key_Down:
            r = self.popup.currentRow()
            r = min(self.popup.count() - 1, r + 1)
            self.popup.setCurrentRow(r)
            return True
        if event.key() == Qt.Key.Key_Up:
            r = self.popup.currentRow()
            r = max(0, r - 1)
            self.popup.setCurrentRow(r)
            return True
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            it = self.popup.currentItem()
            data = it.data(Qt.ItemDataRole.UserRole) if it else None
            if not data:
                return False
            self._choose_current()
            return True
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return True
        return False

    def _choose_current(self):
        it = self.popup.currentItem()
        if not it:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        if data is None:  # 提示条
            return
        name = data.get('name') if isinstance(data, dict) else it.text()
        base = self._line.text().strip()
        if base:
            if ' ' in base:
                parts = base.split()
                parts[-1] = name
                value = ' '.join(parts)
            else:
                value = name
        else:
            value = name
        self._line.setText(value)
        self.hide()

    def _on_item_clicked(self, item):
        self._choose_current()
