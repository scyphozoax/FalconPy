#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

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
    app.setApplicationVersion("pre-251130.0")
    app.setOrganizationName("FalconPy")
    icon_path = r"d:\0\falconpy\assets\falcon.ico"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    config = Config()

    main_window = MainWindow()
    main_window.show()

    t1 = perf_counter()
    print(f"[启动耗时] 初始化至窗口显示: {t1 - t0:.3f}s")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
