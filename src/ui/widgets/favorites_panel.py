# -*- coding: utf-8 -*-
"""
收藏夹面板组件
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                            QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                            QMenu, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from ...core.database import DatabaseManager

class FavoritesPanel(QWidget):
    """收藏夹面板"""
    
    folder_selected = pyqtSignal(int, str)  # 文件夹选择信号 (folder_id, folder_name)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_favorites()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title_label = QLabel("收藏夹")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 5px;
            }
        """)
        layout.addWidget(title_label)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_folder_button = QPushButton("新建")
        self.add_folder_button.setFixedHeight(25)
        self.add_folder_button.clicked.connect(self.add_folder)
        toolbar_layout.addWidget(self.add_folder_button)
        
        self.delete_button = QPushButton("删除")
        self.delete_button.setFixedHeight(25)
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_button.setEnabled(False)
        toolbar_layout.addWidget(self.delete_button)
        
        layout.addLayout(toolbar_layout)
        
        # 收藏夹树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # 设置样式
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            
            QTreeWidget::item {
                padding: 4px;
                border: none;
            }
            
            QTreeWidget::item:hover {
                background-color: #4a4a4a;
            }
            
            QTreeWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        
        layout.addWidget(self.tree_widget)
    
    def load_favorites(self):
        """加载收藏夹"""
        # 清空现有项目
        self.tree_widget.clear()
        
        # 本地收藏夹
        local_root = QTreeWidgetItem(self.tree_widget, ["本地收藏"])
        local_root.setExpanded(True)
        
        # 从数据库加载本地收藏夹
        folders = self.db_manager.get_folders()
        for folder in folders:
            folder_item = QTreeWidgetItem(local_root, [folder['name']])
            folder_item.setData(0, Qt.ItemDataRole.UserRole, folder['id'])
        
        # 如果没有文件夹，创建默认文件夹
        if not folders:
            default_folders = ["未分类", "精选", "壁纸", "角色"]
            for folder_name in default_folders:
                folder_id = self.db_manager.create_folder(folder_name)
                folder_item = QTreeWidgetItem(local_root, [folder_name])
                folder_item.setData(0, Qt.ItemDataRole.UserRole, folder_id)
        
        # 在线收藏夹
        online_root = QTreeWidgetItem(self.tree_widget, ["在线收藏"])
        online_root.setExpanded(True)
        
        # 各网站收藏夹
        sites = ["Danbooru", "Konachan", "Yande.re"]
        for site in sites:
            site_item = QTreeWidgetItem(online_root, [site])
            site_item.setData(0, Qt.ItemDataRole.UserRole, f"online_{site.lower()}")
    
    def add_folder(self):
        """添加新文件夹"""
        current_item = self.tree_widget.currentItem()
        
        # 确定父文件夹
        parent_id = None
        if current_item:
            if current_item.text(0) == "本地收藏":
                parent_id = None
            elif current_item.parent() and current_item.parent().text(0) == "本地收藏":
                parent_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        # 获取文件夹名称
        name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:")
        if ok and name.strip():
            try:
                folder_id = self.db_manager.create_folder(name.strip(), parent_id)
                
                # 添加到界面
                local_root = self.tree_widget.topLevelItem(0)  # 本地收藏根节点
                folder_item = QTreeWidgetItem(local_root, [name.strip()])
                folder_item.setData(0, Qt.ItemDataRole.UserRole, folder_id)
                
                QMessageBox.information(self, "成功", "文件夹创建成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建文件夹失败：{str(e)}")
    
    def delete_selected(self):
        """删除选中项"""
        current_item = self.tree_widget.currentItem()
        if current_item and current_item.parent() and current_item.parent().text(0) == "本地收藏":
            folder_id = current_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(folder_id, int):  # 只删除本地收藏夹
                reply = QMessageBox.question(
                    self, "确认删除", 
                    f"确定要删除 '{current_item.text(0)}' 吗？\n这将删除文件夹中的所有收藏。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        self.db_manager.delete_folder(folder_id)
                        current_item.parent().removeChild(current_item)
                        QMessageBox.information(self, "成功", "文件夹删除成功！")
                    except Exception as e:
                        QMessageBox.warning(self, "错误", f"删除文件夹失败：{str(e)}")
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        if item.parent():  # 子项目
            if item.parent().text(0) == "本地收藏":  # 只对本地收藏夹显示菜单
                rename_action = QAction("重命名", self)
                rename_action.triggered.connect(lambda: self.rename_item(item))
                menu.addAction(rename_action)
                
                delete_action = QAction("删除", self)
                delete_action.triggered.connect(lambda: self.delete_item(item))
                menu.addAction(delete_action)
        else:  # 根项目
            if item.text(0) == "本地收藏":
                add_action = QAction("新建文件夹", self)
                add_action.triggered.connect(self.add_folder)
                menu.addAction(add_action)
        
        if menu.actions():  # 只有在有菜单项时才显示
            menu.exec(self.tree_widget.mapToGlobal(position))
    
    def rename_item(self, item):
        """重命名项目"""
        folder_id = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(folder_id, int):
            new_name, ok = QInputDialog.getText(
                self, "重命名文件夹", 
                "请输入新名称:", 
                text=item.text(0)
            )
            if ok and new_name.strip():
                try:
                    self.db_manager.rename_folder(folder_id, new_name.strip())
                    item.setText(0, new_name.strip())
                    QMessageBox.information(self, "成功", "重命名成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"重命名失败：{str(e)}")
    
    def delete_item(self, item):
        """删除项目"""
        folder_id = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(folder_id, int):
            reply = QMessageBox.question(
                self, "确认删除", 
                f"确定要删除 '{item.text(0)}' 吗？\n这将删除文件夹中的所有收藏。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.db_manager.delete_folder(folder_id)
                    item.parent().removeChild(item)
                    QMessageBox.information(self, "成功", "文件夹删除成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"删除文件夹失败：{str(e)}")
    
    def on_selection_changed(self):
        """选择改变事件"""
        current_item = self.tree_widget.currentItem()
        # 只有本地收藏夹的子项目才能删除
        can_delete = (current_item is not None and 
                     current_item.parent() is not None and 
                     current_item.parent().text(0) == "本地收藏")
        self.delete_button.setEnabled(can_delete)
        
        if current_item:
            folder_data = current_item.data(0, Qt.ItemDataRole.UserRole)
            folder_name = current_item.text(0)
            
            if isinstance(folder_data, int):  # 本地收藏夹
                self.folder_selected.emit(folder_data, folder_name)
            elif isinstance(folder_data, str):  # 在线收藏夹
                self.folder_selected.emit(-1, folder_data)  # 使用-1表示在线收藏夹
    
    def on_item_double_clicked(self, item, column):
        """双击事件"""
        # 双击展开/折叠或选择文件夹
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
        else:
            self.on_selection_changed()
    
    def refresh_folders(self):
        """刷新文件夹列表"""
        self.load_favorites()