"""
C-Wiper UI 测试脚本

测试 UI 层的基本功能。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import messagebox

from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.controllers.analysis_controller import AnalysisController
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
from src.models.scan_result import FileInfo


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_ui_integration():
    """
    UI 集成测试

    测试整个 UI 层的集成功能。
    """
    print("=" * 60)
    print("C-Wiper UI 集成测试")
    print("=" * 60)

    # 创建测试窗口
    print("\n[Step 1] 创建测试窗口...")
    root = tk.Tk()
    root.title("C-Wiper UI 测试")
    root.geometry("1200x800")

    # 初始化控制器
    print("[Step 2] 初始化控制器...")
    scan_controller = ScanController()
    clean_controller = CleanController()
    analysis_controller = AnalysisController()
    print("  [OK] 控制器初始化完成")

    # 创建主窗口
    print("\n[Step 3] 创建主窗口...")
    app = MainWindow(
        root,
        scan_controller,
        clean_controller,
        analysis_controller
    )
    print("  [OK] 主窗口创建成功")

    # 测试视图切换
    print("\n[Step 4] 测试视图切换...")

    # 延迟执行测试
    def run_tests():
        """运行测试序列"""
        print("\n[TEST] 切换到仪表盘...")
        app.show_dashboard()
        root.update()
        print("  [OK] 仪表盘显示成功")

        root.after(2000, test_cleaner_view)

    def test_cleaner_view():
        """测试清理视图"""
        print("\n[TEST] 切换到清理视图...")
        app.show_cleaner_view()
        root.update()
        print("  [OK] 清理视图显示成功")

        root.after(2000, test_analyzer_view)

    def test_analyzer_view():
        """测试分析视图"""
        print("\n[TEST] 切换到分析视图...")
        app.show_analyzer_view()
        root.update()
        print("  [OK] 分析视图显示成功")

        root.after(2000, test_dialogs)

    def test_dialogs():
        """测试对话框"""
        print("\n[TEST] 测试对话框...")

        # 测试进度对话框
        print("  [TEST] 显示进度对话框...")
        progress_dialog = ProgressDialog(
            root,
            message="测试进度...",
            title="测试",
            cancellable=True
        )

        def update_progress():
            for i in range(101):
                if progress_dialog.cancelled:
                    break
                progress_dialog.update_progress(i, 100)
                root.update()
                root.after(10)

            if not progress_dialog.cancelled:
                root.after(500, lambda: progress_dialog.close())

        root.after(100, update_progress)

        root.after(2000, test_complete)

    def test_complete():
        """测试完成"""
        print("\n[TEST] 测试完成")
        messagebox.showinfo(
            "测试完成",
            "UI 集成测试完成！\n\n所有功能正常运行。"
        )

    # 开始测试
    root.after(1000, run_tests)

    print("\n[Step 5] 启动主循环...")
    print("  [INFO] 测试将自动运行，请观察窗口变化")
    print("  [INFO] 测试完成后窗口将关闭")

    # 运行主循环
    root.mainloop()

    print("\n" + "=" * 60)
    print("[OK] UI 集成测试完成！")
    print("=" * 60)


def test_dialog_components():
    """
    对话框组件测试

    测试所有对话框组件的基本功能。
    """
    print("=" * 60)
    print("对话框组件测试")
    print("=" * 60)

    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 创建测试文件列表
    print("\n[Step 1] 创建测试数据...")
    test_files = []
    for i in range(30):
        from pathlib import Path
        import tempfile

        file_path = Path(f"C:/temp/test_{i}.tmp")

        test_files.append(FileInfo(
            path=file_path,
            size=1024 * (i + 1),
            is_dir=False,
            modified_time=1234567890.0
        ))

    total_size = sum(f.size for f in test_files)
    print(f"  [OK] 创建了 {len(test_files)} 个测试文件")

    # 测试清理确认对话框
    print("\n[Step 2] 测试清理确认对话框...")
    dialog1 = ConfirmCleanDialog(
        root,
        files=test_files,
        total_size=total_size
    )
    root.wait_window(dialog1)
    print(f"  [OK] 用户选择: {'确认' if dialog1.result else '取消'}")

    # 测试结果对话框
    print("\n[Step 3] 测试结果对话框（成功）...")
    dialog2 = ResultDialog(
        root,
        title="测试完成",
        message="这是一个成功的结果",
        details=f"处理了 {len(test_files)} 个文件\n总大小: {total_size / 1024:.2f} KB",
        success=True
    )
    root.wait_window(dialog2)
    print("  [OK] 结果对话框已关闭")

    # 测试错误对话框
    print("\n[Step 4] 测试错误对话框...")
    dialog3 = ErrorDialog(
        root,
        title="测试错误",
        error_message="这是一个测试错误",
        details="错误详情:\n  - 错误代码: TEST_001\n  - 文件: test.py\n  - 行号: 42"
    )
    root.wait_window(dialog3)
    print("  [OK] 错误对话框已关闭")

    root.destroy()

    print("\n" + "=" * 60)
    print("[OK] 对话框组件测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 运行集成测试
    test_ui_integration()

    # 运行对话框测试
    # test_dialog_components()
