"""
C-Wiper UI Layer - 用户界面层

本模块提供图形用户界面，包括主窗口、仪表盘、清理视图、分析视图和对话框组件。

模块:
    main_window: 主窗口框架
    dashboard: 仪表盘视图
    cleaner_view: 清理工具视图
    analyzer_view: 空间分析视图
    dialogs: 对话框组件

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

from src.ui.main_window import MainWindow
from src.ui.dashboard import Dashboard
from src.ui.cleaner_view import CleanerView
from src.ui.analyzer_view import AnalyzerView
from src.ui.dialogs import (
    ConfirmCleanDialog,
    ProgressDialog,
    ResultDialog,
    ErrorDialog
)

__all__ = [
    'MainWindow',
    'Dashboard',
    'CleanerView',
    'AnalyzerView',
    'ConfirmCleanDialog',
    'ProgressDialog',
    'ResultDialog',
    'ErrorDialog'
]
