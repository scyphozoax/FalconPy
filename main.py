#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFontDatabase, QFont

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.main_window import MainWindow
from src.core.config import Config

def main():
    """主函数"""
    from time import perf_counter
    t0 = perf_counter()

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("FalconPy")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("FalconPy")
    icon_path = r"d:\0\falconpy\assets\falcon.ico"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    config = Config()

    def apply_fonts_later():
        try:
            root_dir = os.path.dirname(os.path.abspath(__file__))
            fonts_dir = os.path.join(root_dir, 'fonts')
            if not os.path.isdir(fonts_dir):
                return
            font_files = []
            for name in os.listdir(fonts_dir):
                if name.lower().endswith(('.ttf', '.otf')):
                    font_files.append(os.path.join(fonts_dir, name))
            for fp in font_files:
                try:
                    QFontDatabase.addApplicationFont(fp)
                except Exception:
                    pass
        except Exception as e:
            print(f"扫描并注册字体失败: {e}")

    main_window = MainWindow()
    main_window.show()

    QTimer.singleShot(0, apply_fonts_later)

    t1 = perf_counter()
    print(f"[启动耗时] 初始化至窗口显示: {t1 - t0:.3f}s")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
