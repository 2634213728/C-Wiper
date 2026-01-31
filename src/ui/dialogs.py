"""
Dialogs - 对话框组件模块

本模块实现各类对话框，包括清理确认、进度显示、结果展示和错误提示。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.models.scan_result import FileInfo


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfirmCleanDialog(tk.Toplevel):
    """
    清理确认对话框

    显示清理操作的预览信息，要求用户确认。

    Attributes:
        files: 要清理的文件列表
        total_size: 总大小（字节）
        result: 用户确认结果（True/False）

    Example:
        >>> dialog = ConfirmCleanDialog(parent, files=file_list, total_size=size)
        >>> dialog.wait_window()
        >>> if dialog.result:
        ...     # 用户确认清理
    """

    def __init__(
        self,
        parent: tk.Widget,
        files: List[FileInfo],
        total_size: int
    ):
        """
        初始化清理确认对话框

        Args:
            parent: 父窗口
            files: 要清理的文件列表
            total_size: 总大小（字节）
        """
        super().__init__(parent)
        self.files = files
        self.total_size = total_size
        self.result = False

        self._setup_window()
        self._create_ui()

        logger.debug("ConfirmCleanDialog created")

    def _setup_window(self) -> None:
        """配置窗口"""
        self.title("确认清理")
        self.geometry("600x500")
        self.resizable(False, False)

        # 模态对话框
        self.transient(self.master)
        self.grab_set()

        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f'600x500+{x}+{y}')

    def _create_ui(self) -> None:
        """创建UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="确认清理操作",
            font=('Microsoft YaHei UI', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # 警告图标和文本
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 20))

        warning_label = ttk.Label(
            warning_frame,
            text="⚠️",
            font=('Segoe UI Emoji', 32)
        )
        warning_label.pack(side=tk.LEFT, padx=(0, 10))

        warning_text = ttk.Label(
            warning_frame,
            text="您即将删除以下文件，此操作不可撤销！\n"
                 "建议先仔细检查文件列表，确认无误后再执行。",
            font=('Microsoft YaHei UI', 10),
            foreground='#FF9800'
        )
        warning_text.pack(side=tk.LEFT)

        # 统计信息
        stats_frame = ttk.LabelFrame(main_frame, text="清理统计", padding=15)
        stats_frame.pack(fill=tk.X, pady=(0, 20))

        # 文件数量
        count_frame = ttk.Frame(stats_frame)
        count_frame.pack(fill=tk.X, pady=5)
        ttk.Label(count_frame, text="文件数量:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT)
        ttk.Label(
            count_frame,
            text=f"{len(self.files)} 个",
            font=('Microsoft YaHei UI', 12, 'bold'),
            foreground="#2196F3"
        ).pack(side=tk.RIGHT)

        # 总大小
        size_frame = ttk.Frame(stats_frame)
        size_frame.pack(fill=tk.X, pady=5)
        ttk.Label(size_frame, text="总大小:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT)
        formatted_size = self._format_size(self.total_size)
        ttk.Label(
            size_frame,
            text=formatted_size,
            font=('Microsoft YaHei UI', 12, 'bold'),
            foreground="#4CAF50"
        ).pack(side=tk.RIGHT)

        # 文件列表（前20个）
        list_frame = ttk.LabelFrame(main_frame, text="文件列表（部分）", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # 创建滚动文本框
        list_text = tk.Text(
            list_frame,
            height=10,
            width=60,
            font=('Consolas', 9),
            wrap=tk.NONE,
            state=tk.DISABLED
        )

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=list_text.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=list_text.xview)

        list_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        list_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 添加文件列表（前20个）
        list_text.config(state=tk.NORMAL)
        for file_info in self.files[:20]:
            list_text.insert(
                tk.END,
                f"{file_info.path.name:<50} {self._format_size(file_info.size):>10}\n"
            )

        if len(self.files) > 20:
            list_text.insert(tk.END, f"\n... 还有 {len(self.files) - 20} 个文件\n")

        list_text.config(state=tk.DISABLED)

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="取消",
            command=self._on_cancel,
            width=12
        ).pack(side=tk.RIGHT, padx=5)

        # 确认按钮（红色）
        confirm_btn = tk.Button(
            button_frame,
            text="确认清理",
            command=self._on_confirm,
            font=('Microsoft YaHei UI', 11, 'bold'),
            bg="#F44336",
            fg="white",
            relief=tk.FLAT,
            cursor='hand2',
            padx=20,
            pady=8,
            width=12
        )
        confirm_btn.pack(side=tk.RIGHT, padx=5)

    def _on_confirm(self) -> None:
        """确认按钮事件"""
        self.result = True
        self.destroy()

    def _on_cancel(self) -> None:
        """取消按钮事件"""
        self.result = False
        self.destroy()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


class ProgressDialog(tk.Toplevel):
    """
    进度对话框

    显示操作进度的对话框，支持取消操作。

    Attributes:
        title: 对话框标题
        message: 提示消息
        cancellable: 是否可取消
        cancelled: 用户是否点击了取消
        progress_var: 进度变量

    Example:
        >>> dialog = ProgressDialog(parent, "正在扫描...", "扫描中", cancellable=True)
        >>> # 更新进度
        >>> dialog.update_progress(50, 100)
        >>> dialog.close()
    """

    def __init__(
        self,
        parent: tk.Widget,
        message: str,
        title: str = "操作进行中",
        cancellable: bool = True
    ):
        """
        初始化进度对话框

        Args:
            parent: 父窗口
            message: 提示消息
            title: 对话框标题
            cancellable: 是否可取消
        """
        super().__init__(parent)
        self.message = message
        self.cancellable = cancellable
        self.cancelled = False
        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value=message)

        self._setup_window(title)
        self._create_ui()

        logger.debug(f"ProgressDialog created: {title}")

    def _setup_window(self, title: str) -> None:
        """配置窗口"""
        self.title(title)
        self.geometry("500x200")
        self.resizable(False, False)

        # 模态对话框
        self.transient(self.master)
        self.grab_set()

        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (200 // 2)
        self.geometry(f'500x200+{x}+{y}')

    def _create_ui(self) -> None:
        """创建UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 消息标签
        message_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=('Microsoft YaHei UI', 11)
        )
        message_label.pack(pady=(0, 30))

        # 进度条
        progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        progress_bar.pack(pady=(0, 20))

        # 进度百分比标签
        self.percent_label = ttk.Label(
            main_frame,
            text="0%",
            font=('Microsoft YaHei UI', 10)
        )
        self.percent_label.pack(pady=(0, 20))

        # 取消按钮
        if self.cancellable:
            cancel_btn = ttk.Button(
                main_frame,
                text="取消",
                command=self._on_cancel,
                width=12
            )
            cancel_btn.pack()

    def update_progress(self, current: int, total: int, message: Optional[str] = None) -> None:
        """
        更新进度

        Args:
            current: 当前进度
            total: 总数
            message: 新的提示消息（可选）
        """
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.percent_label.config(text=f"{progress:.1f}%")

        if message:
            self.status_var.set(message)

        self.update_idletasks()

    def _on_cancel(self) -> None:
        """取消按钮事件"""
        self.cancelled = True
        self.destroy()

    def close(self) -> None:
        """关闭对话框"""
        self.destroy()


class ResultDialog(tk.Toplevel):
    """
    结果展示对话框

    显示操作结果的对话框。

    Attributes:
        title: 对话框标题
        message: 结果消息
        details: 详细信息
        success: 是否成功

    Example:
        >>> dialog = ResultDialog(parent, "扫描完成", "发现 100 个文件", success=True)
        >>> dialog.wait_window()
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        message: str,
        details: Optional[str] = None,
        success: bool = True
    ):
        """
        初始化结果对话框

        Args:
            parent: 父窗口
            title: 对话框标题
            message: 结果消息
            details: 详细信息（可选）
            success: 是否成功
        """
        super().__init__(parent)
        self.title = title
        self.message = message
        self.details = details
        self.success = success

        self._setup_window(title)
        self._create_ui()

        logger.debug(f"ResultDialog created: {title}")

    def _setup_window(self, title: str) -> None:
        """配置窗口"""
        self.title(title)
        self.geometry("600x400")
        self.resizable(True, True)

        # 模态对话框
        self.transient(self.master)
        self.grab_set()

        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (400 // 2)
        self.geometry(f'600x400+{x}+{y}')

    def _create_ui(self) -> None:
        """创建UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图标和标题
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 20))

        if self.success:
            icon_label = ttk.Label(
                header_frame,
                text="✅",
                font=('Segoe UI Emoji', 48)
            )
            color = "#4CAF50"
        else:
            icon_label = ttk.Label(
                header_frame,
                text="❌",
                font=('Segoe UI Emoji', 48)
            )
            color = "#F44336"

        icon_label.pack(side=tk.LEFT, padx=(0, 15))

        title_label = ttk.Label(
            header_frame,
            text=self.title,
            font=('Microsoft YaHei UI', 14, 'bold'),
            foreground=color
        )
        title_label.pack(side=tk.LEFT)

        # 消息
        message_label = ttk.Label(
            main_frame,
            text=self.message,
            font=('Microsoft YaHei UI', 10),
            wraplength=550
        )
        message_label.pack(pady=(0, 20))

        # 详细信息（如果有）
        if self.details:
            details_frame = ttk.LabelFrame(main_frame, text="详细信息", padding=10)
            details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

            details_text = tk.Text(
                details_frame,
                height=10,
                font=('Consolas', 9),
                wrap=tk.WORD,
                state=tk.DISABLED
            )

            vsb = ttk.Scrollbar(details_frame, orient="vertical", command=details_text.yview)
            details_text.configure(yscrollcommand=vsb.set)

            details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)

            details_frame.grid_rowconfigure(0, weight=1)
            details_frame.grid_columnconfigure(0, weight=1)

            # 添加详细信息
            details_text.config(state=tk.NORMAL)
            details_text.insert(tk.END, self.details)
            details_text.config(state=tk.DISABLED)

        # 关闭按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="关闭",
            command=self.destroy,
            width=12
        ).pack(side=tk.RIGHT)


class ErrorDialog(tk.Toplevel):
    """
    错误提示对话框

    显示错误信息的对话框。

    Attributes:
        title: 对话框标题
        error_message: 错误消息
        details: 详细信息

    Example:
        >>> dialog = ErrorDialog(parent, "操作失败", "无法访问文件")
        >>> dialog.wait_window()
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        error_message: str,
        details: Optional[str] = None
    ):
        """
        初始化错误对话框

        Args:
            parent: 父窗口
            title: 对话框标题
            error_message: 错误消息
            details: 详细信息（可选）
        """
        super().__init__(parent)
        self.title = title
        self.error_message = error_message
        self.details = details

        self._setup_window(title)
        self._create_ui()

        logger.debug(f"ErrorDialog created: {title}")

    def _setup_window(self, title: str) -> None:
        """配置窗口"""
        self.title(title)
        self.geometry("500x300")
        self.resizable(True, True)

        # 模态对话框
        self.transient(self.master)
        self.grab_set()

        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (300 // 2)
        self.geometry(f'500x300+{x}+{y}')

    def _create_ui(self) -> None:
        """创建UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图标和标题
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 20))

        icon_label = ttk.Label(
            header_frame,
            text="⚠️",
            font=('Segoe UI Emoji', 48)
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))

        title_label = ttk.Label(
            header_frame,
            text="发生错误",
            font=('Microsoft YaHei UI', 14, 'bold'),
            foreground="#F44336"
        )
        title_label.pack(side=tk.LEFT)

        # 错误消息
        error_label = ttk.Label(
            main_frame,
            text=self.error_message,
            font=('Microsoft YaHei UI', 10),
            wraplength=450,
            foreground="#757575"
        )
        error_label.pack(pady=(0, 20))

        # 详细信息（如果有）
        if self.details:
            details_frame = ttk.LabelFrame(main_frame, text="详细信息", padding=10)
            details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

            details_text = tk.Text(
                details_frame,
                height=6,
                font=('Consolas', 9),
                wrap=tk.WORD,
                state=tk.DISABLED
            )

            vsb = ttk.Scrollbar(details_frame, orient="vertical", command=details_text.yview)
            details_text.configure(yscrollcommand=vsb.set)

            details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)

            # 添加详细信息
            details_text.config(state=tk.NORMAL)
            details_text.insert(tk.END, self.details)
            details_text.config(state=tk.DISABLED)

        # 关闭按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="确定",
            command=self.destroy,
            width=12
        ).pack(side=tk.RIGHT)


def test_dialogs():
    """
    Dialogs Test Function

    测试所有对话框的基本功能。
    """
    import tempfile
    from pathlib import Path

    print("=" * 60)
    print("Dialogs Test")
    print("=" * 60)

    # 创建测试窗口
    print("\n[Step 1] Creating test window...")
    root = tk.Tk()
    root.title("Dialogs Test")
    root.withdraw()  # 隐藏主窗口

    # 创建测试文件列表
    print("\n[Step 2] Creating test data...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir)

        test_files = []
        for i in range(30):
            file_path = test_path / f"test_{i}.tmp"
            file_path.write_text(f"Test content {i} " * 100)

            test_files.append(FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            ))

        total_size = sum(f.size for f in test_files)
        print(f"  [OK] Created {len(test_files)} test files")

        # 测试 ConfirmCleanDialog
        print("\n[Step 3] Testing ConfirmCleanDialog...")
        dialog1 = ConfirmCleanDialog(
            root,
            files=test_files,
            total_size=total_size
        )
        print("  [INFO] Close the dialog to continue...")
        root.wait_window(dialog1)
        print(f"  [OK] Result: {dialog1.result}")

        # 测试 ProgressDialog
        print("\n[Step 4] Testing ProgressDialog...")
        dialog2 = ProgressDialog(
            root,
            message="正在扫描...",
            title="扫描进行中",
            cancellable=True
        )

        # 模拟进度更新
        def update_progress():
            for i in range(101):
                if dialog2.cancelled:
                    break
                dialog2.update_progress(i, 100, f"扫描中... {i}%")
                root.update()
                root.after(20)

            if not dialog2.cancelled:
                root.after(500, dialog2.close)

        root.after(100, update_progress)
        root.wait_window(dialog2)
        print(f"  [OK] Cancelled: {dialog2.cancelled}")

        # 测试 ResultDialog（成功）
        print("\n[Step 5] Testing ResultDialog (success)...")
        dialog3 = ResultDialog(
            root,
            title="扫描完成",
            message="扫描成功完成！",
            details=f"发现 {len(test_files)} 个文件\n总大小: {dialog1._format_size(total_size)}",
            success=True
        )
        print("  [INFO] Close the dialog to continue...")
        root.wait_window(dialog3)
        print("  [OK] ResultDialog (success) completed")

        # 测试 ResultDialog（失败）
        print("\n[Step 6] Testing ResultDialog (failure)...")
        dialog4 = ResultDialog(
            root,
            title="扫描失败",
            message="扫描过程中发生错误",
            details="无法访问某些文件\n权限不足",
            success=False
        )
        print("  [INFO] Close the dialog to continue...")
        root.wait_window(dialog4)
        print("  [OK] ResultDialog (failure) completed")

        # 测试 ErrorDialog
        print("\n[Step 7] Testing ErrorDialog...")
        dialog5 = ErrorDialog(
            root,
            title="操作失败",
            error_message="无法完成操作",
            details="错误代码: 0x80070005\n访问被拒绝"
        )
        print("  [INFO] Close the dialog to continue...")
        root.wait_window(dialog5)
        print("  [OK] ErrorDialog completed")

    print("\n" + "=" * 60)
    print("[OK] All dialogs tests completed!")
    print("=" * 60)

    root.destroy()


if __name__ == "__main__":
    test_dialogs()
