"""
Cleaner View - 清理视图模块

本模块实现清理视图，显示扫描结果、文件列表和清理操作。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.ui.main_window import MainWindow
from src.models.scan_result import FileInfo, ScanTarget
from src.controllers.state_manager import SystemState


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanerView(ttk.Frame):
    """
    清理视图类

    显示扫描结果和文件列表，支持筛选、排序和清理操作。

    Attributes:
        parent: 父容器
        main_window: 主窗口引用
        scan_results: 扫描结果列表
        selected_files: 选中的文件列表
        current_filter: 当前筛选条件
        sort_column: 当前排序列
        sort_reverse: 是否反向排序

    Example:
        >>> cleaner_view = CleanerView(parent_frame, main_window)
        >>> cleaner_view.pack(fill=tk.BOTH, expand=True)
    """

    def __init__(self, parent: tk.Widget, main_window: MainWindow):
        """
        初始化清理视图

        Args:
            parent: 父容器
            main_window: 主窗口引用
        """
        super().__init__(parent)
        self.main_window = main_window
        self.scan_results: List[FileInfo] = []
        self.selected_files: List[FileInfo] = []
        self.current_filter = tk.StringVar(value="all")
        self.sort_column = "size"
        self.sort_reverse = True

        # 创建UI组件
        self._create_header()
        self._create_filter_bar()
        self._create_results_tree()
        self._create_action_bar()

        logger.info("CleanerView initialized")

    def _create_header(self) -> None:
        """创建标题区域"""
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=20)

        # 标题
        title_label = ttk.Label(
            header_frame,
            text="清理工具",
            font=('Microsoft YaHei UI', 18, 'bold')
        )
        title_label.pack(side=tk.LEFT)

        # 副标题
        subtitle_label = ttk.Label(
            header_frame,
            text="扫描并清理系统垃圾文件",
            font=('Microsoft YaHei UI', 10)
        )
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

    def _create_filter_bar(self) -> None:
        """创建筛选栏"""
        filter_frame = ttk.LabelFrame(self, text="扫描选项", padding=10)
        filter_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        # 左侧：扫描目标
        left_frame = ttk.Frame(filter_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 扫描目标复选框
        self.scan_targets = {
            'temp': tk.BooleanVar(value=True),
            'cache': tk.BooleanVar(value=True),
            'logs': tk.BooleanVar(value=False),
            'recycle': tk.BooleanVar(value=False)
        }

        targets = [
            ('temp', '临时文件'),
            ('cache', '缓存文件'),
            ('logs', '日志文件'),
            ('recycle', '回收站')
        ]

        for key, text in targets:
            chk = ttk.Checkbutton(
                left_frame,
                text=text,
                variable=self.scan_targets[key]
            )
            chk.pack(side=tk.LEFT, padx=10)

        # 右侧：扫描按钮
        right_frame = ttk.Frame(filter_frame)
        right_frame.pack(side=tk.RIGHT)

        self.scan_btn = ttk.Button(
            right_frame,
            text="开始扫描",
            command=self._on_start_scan,
            width=15
        )
        self.scan_btn.pack()

    def _create_results_tree(self) -> None:
        """创建结果树形视图"""
        results_frame = ttk.LabelFrame(self, text="扫描结果", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        # 顶部工具栏
        toolbar_frame = ttk.Frame(results_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))

        # 筛选下拉框
        ttk.Label(toolbar_frame, text="筛选:").pack(side=tk.LEFT, padx=(0, 5))

        filter_combo = ttk.Combobox(
            toolbar_frame,
            textvariable=self.current_filter,
            values=["all", "L1_SAFE", "L2_REVIEW", "L3_SYSTEM"],
            state="readonly",
            width=15
        )
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # 全选/反选按钮
        ttk.Button(
            toolbar_frame,
            text="全选",
            command=self._on_select_all,
            width=8
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar_frame,
            text="反选",
            command=self._on_invert_selection,
            width=8
        ).pack(side=tk.LEFT, padx=5)

        # 统计信息
        self.stats_label = ttk.Label(
            toolbar_frame,
            text="未扫描",
            font=('Microsoft YaHei UI', 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # 创建 Treeview
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        columns = ("name", "path", "size", "risk_level", "modified_time")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        # 配置列
        self.tree.heading("#0", text="选择")
        self.tree.heading("name", text="文件名", command=lambda: self._sort_by_column("name"))
        self.tree.heading("path", text="路径", command=lambda: self._sort_by_column("path"))
        self.tree.heading("size", text="大小", command=lambda: self._sort_by_column("size"))
        self.tree.heading("risk_level", text="风险", command=lambda: self._sort_by_column("risk_level"))
        self.tree.heading("modified_time", text="修改时间", command=lambda: self._sort_by_column("modified_time"))

        self.tree.column("#0", width=50, stretch=False)
        self.tree.column("name", width=200, stretch=True)
        self.tree.column("path", width=300, stretch=True)
        self.tree.column("size", width=100, stretch=False)
        self.tree.column("risk_level", width=100, stretch=False)
        self.tree.column("modified_time", width=150, stretch=False)

        # 配置滚动条
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 绑定事件
        self.tree.bind("<Button-1>", self._on_tree_click)

    def _create_action_bar(self) -> None:
        """创建操作栏"""
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        # 左侧：选中文件统计
        self.selection_label = ttk.Label(
            action_frame,
            text="未选择文件",
            font=('Microsoft YaHei UI', 10)
        )
        self.selection_label.pack(side=tk.LEFT, padx=10)

        # 右侧：操作按钮
        right_frame = ttk.Frame(action_frame)
        right_frame.pack(side=tk.RIGHT)

        self.clean_btn = ttk.Button(
            right_frame,
            text="清理选中文件",
            command=self._on_clean_selected,
            state=tk.DISABLED,
            width=15
        )
        self.clean_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            right_frame,
            text="打开文件夹",
            command=self._on_open_folder,
            width=12
        ).pack(side=tk.LEFT, padx=5)

    def refresh(self) -> None:
        """刷新视图"""
        self._update_stats()
        self._update_selection_label()

    def load_scan_results(self, results: List[FileInfo]) -> None:
        """
        加载扫描结果

        Args:
            results: 文件信息列表
        """
        self.scan_results = results
        self._populate_tree()
        self._update_stats()

    def _populate_tree(self) -> None:
        """填充树形视图"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 筛选结果
        filtered_results = self._filter_results()

        # 排序结果
        sorted_results = self._sort_results(filtered_results)

        # 添加到树形视图
        for file_info in sorted_results:
            # 检查是否被选中
            checked = "☑" if file_info in self.selected_files else "☐"

            # 插入项目
            item_id = self.tree.insert(
                "",
                tk.END,
                text=checked,
                values=(
                    file_info.path.name,
                    str(file_info.path.parent),
                    self._format_size(file_info.size),
                    self._get_risk_label(file_info),
                    self._format_time(file_info.modified_time)
                )
            )

            # 存储文件信息引用
            self.tree.set(item_id, "file_info", file_info)

    def _filter_results(self) -> List[FileInfo]:
        """筛选结果"""
        filter_value = self.current_filter.get()

        if filter_value == "all":
            return self.scan_results.copy()
        else:
            # 根据风险等级筛选
            return [
                f for f in self.scan_results
                if hasattr(f, 'risk_level') and f.risk_level.name == filter_value
            ]

    def _sort_results(self, results: List[FileInfo]) -> List[FileInfo]:
        """排序结果"""
        reverse = self.sort_reverse

        if self.sort_column == "name":
            return sorted(results, key=lambda x: x.path.name.lower(), reverse=reverse)
        elif self.sort_column == "path":
            return sorted(results, key=lambda x: str(x.path), reverse=reverse)
        elif self.sort_column == "size":
            return sorted(results, key=lambda x: x.size, reverse=reverse)
        elif self.sort_column == "modified_time":
            return sorted(results, key=lambda x: x.modified_time, reverse=reverse)
        elif self.sort_column == "risk_level":
            return sorted(
                results,
                key=lambda x: getattr(x, 'risk_level', 'UNKNOWN').name,
                reverse=reverse
            )
        else:
            return results

    def _sort_by_column(self, column: str) -> None:
        """按列排序"""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = True

        self._populate_tree()

    def _update_stats(self) -> None:
        """更新统计信息"""
        total_count = len(self.scan_results)
        total_size = sum(f.size for f in self.scan_results)

        # 按风险等级统计
        risk_stats = {
            "L1_SAFE": 0,
            "L2_REVIEW": 0,
            "L3_SYSTEM": 0
        }

        for file_info in self.scan_results:
            risk = getattr(file_info, 'risk_level', None)
            if risk and risk.name in risk_stats:
                risk_stats[risk.name] += 1

        stats_text = (
            f"总计: {total_count} 个文件 | "
            f"总大小: {self._format_size(total_size)} | "
            f"L1安全: {risk_stats['L1_SAFE']} | "
            f"L2审查: {risk_stats['L2_REVIEW']} | "
            f"L3系统: {risk_stats['L3_SYSTEM']}"
        )

        self.stats_label.config(text=stats_text)

    def _update_selection_label(self) -> None:
        """更新选择标签"""
        selected_count = len(self.selected_files)
        selected_size = sum(f.size for f in self.selected_files)

        if selected_count > 0:
            text = f"已选择 {selected_count} 个文件，总计 {self._format_size(selected_size)}"
            self.clean_btn.config(state=tk.NORMAL)
        else:
            text = "未选择文件"
            self.clean_btn.config(state=tk.DISABLED)

        self.selection_label.config(text=text)

    def _on_tree_click(self, event) -> None:
        """处理树形视图点击事件（复选框）"""
        region = self.tree.identify_region(event.x, event.y)

        if region == "tree":
            item = self.tree.identify_row(event.y)

            if item:
                # 获取文件信息
                file_info = self.tree.set(item, "file_info")

                if file_info in self.selected_files:
                    self.selected_files.remove(file_info)
                    self.tree.item(item, text="☐")
                else:
                    self.selected_files.append(file_info)
                    self.tree.item(item, text="☑")

                self._update_selection_label()

    def _on_filter_changed(self, event) -> None:
        """筛选条件改变事件"""
        self._populate_tree()

    def _on_select_all(self) -> None:
        """全选"""
        filtered_results = self._filter_results()
        self.selected_files.extend(filtered_results)
        self._populate_tree()
        self._update_selection_label()

    def _on_invert_selection(self) -> None:
        """反选"""
        filtered_results = self._filter_results()

        for file_info in filtered_results:
            if file_info in self.selected_files:
                self.selected_files.remove(file_info)
            else:
                self.selected_files.append(file_info)

        self._populate_tree()
        self._update_selection_label()

    def _on_start_scan(self) -> None:
        """开始扫描按钮事件"""
        # 检查是否有选中的扫描目标
        selected_targets = [
            key for key, var in self.scan_targets.items()
            if var.get()
        ]

        if not selected_targets:
            messagebox.showwarning("警告", "请至少选择一个扫描目标")
            return

        # 准备扫描目标
        targets = self._prepare_scan_targets(selected_targets)

        if not targets:
            messagebox.showwarning("警告", "无法创建扫描目标")
            return

        # 开始扫描
        self.main_window.update_status("正在扫描...")
        self.scan_btn.config(state=tk.DISABLED)

        try:
            # 调用扫描控制器
            success = self.main_window.scan_controller.start_scan(
                targets,
                progress_callback=self._on_scan_progress
            )

            if success:
                logger.info(f"Scan started for {len(targets)} targets")
            else:
                messagebox.showerror("错误", "无法启动扫描")
                self.scan_btn.config(state=tk.NORMAL)

        except Exception as e:
            logger.error(f"Failed to start scan: {e}")
            messagebox.showerror("错误", f"扫描启动失败：{str(e)}")
            self.scan_btn.config(state=tk.NORMAL)

    def _prepare_scan_targets(self, selected_targets: List[str]) -> List[ScanTarget]:
        """
        准备扫描目标

        Args:
            selected_targets: 选中的目标列表

        Returns:
            List[ScanTarget]: 扫描目标列表
        """
        targets = []

        target_configs = {
            'temp': {
                'id': 'temp',
                'name': '临时文件',
                'paths': [
                    Path("C:/Windows/Temp"),
                    Path(os.environ.get('TEMP', "C:/Windows/Temp")),
                    Path(os.environ.get('TMP', "C:/Windows/Temp"))
                ]
            },
            'cache': {
                'id': 'cache',
                'name': '缓存文件',
                'paths': [
                    Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cache",
                    Path.home() / "AppData/Local/Microsoft/Windows/INetCache"
                ]
            },
            'logs': {
                'id': 'logs',
                'name': '日志文件',
                'paths': [
                    Path("C:/Windows/Logs"),
                    Path("C:/Windows/Debug")
                ]
            },
            'recycle': {
                'id': 'recycle',
                'name': '回收站',
                'paths': [
                    Path("C:/") / "$Recycle.Bin"
                ]
            }
        }

        for key in selected_targets:
            if key in target_configs:
                config = target_configs[key]
                for path in config['paths']:
                    if path.exists():
                        targets.append(ScanTarget(
                            id=config['id'],
                            name=config['name'],
                            path=path,
                            description=f"扫描{config['name']}"
                        ))

        return targets

    def _on_scan_progress(self, current: int, total: int, result) -> None:
        """扫描进度回调"""
        progress = (current / total * 100) if total > 0 else 0
        self.main_window.update_status(f"扫描中... {current}/{total}", progress)

    def _on_clean_selected(self) -> None:
        """清理选中文件按钮事件"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要清理的文件")
            return

        # 显示确认对话框
        total_size = sum(f.size for f in self.selected_files)

        from src.ui.dialogs import ConfirmCleanDialog
        dialog = ConfirmCleanDialog(
            self,
            files=self.selected_files,
            total_size=total_size
        )

        if dialog.result:
            # 用户确认清理
            self.main_window.update_status("正在清理...")

            # 预览清理
            preview = self.main_window.clean_controller.preview_clean(
                self.selected_files
            )

            # 显示预览信息
            preview_text = (
                f"将删除 {preview['file_count']} 个文件\n"
                f"释放空间: {preview['formatted_size']}\n"
                f"安全文件: {preview['safe_files']}\n"
                f"需审查文件: {preview['risky_files']}"
            )

            if preview['system_files'] > 0:
                preview_text += f"\n系统文件（将被跳过）: {preview['system_files']}"

            if messagebox.askyesno("确认清理", preview_text):
                # 确认清理
                self.main_window.clean_controller.confirm_clean()

                # 执行清理
                success = self.main_window.clean_controller.start_clean(
                    self.selected_files,
                    require_confirmation=False  # 已经确认过了
                )

                if success:
                    # 等待完成
                    self.main_window.clean_controller.wait_for_completion(timeout=300)

                    # 从结果中移除已清理的文件
                    result = self.main_window.clean_controller.get_result()
                    if result and result.success:
                        # 清理成功，移除已删除的文件
                        for file in self.selected_files:
                            if file in self.scan_results:
                                self.scan_results.remove(file)

                        self.selected_files.clear()
                        self._populate_tree()
                        self._update_stats()
                        self._update_selection_label()

    def _on_open_folder(self) -> None:
        """打开文件夹按钮事件"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择文件")
            return

        # 打开第一个选中文件的文件夹
        file_info = self.selected_files[0]
        folder_path = str(file_info.path.parent)

        import subprocess
        try:
            subprocess.Popen(['explorer', folder_path])
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            messagebox.showerror("错误", f"无法打开文件夹：{str(e)}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def _format_time(timestamp: float) -> str:
        """格式化时间戳"""
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _get_risk_label(self, file_info: FileInfo) -> str:
        """获取风险等级标签"""
        risk = getattr(file_info, 'risk_level', None)
        if not risk:
            return "未分类"

        risk_labels = {
            "L1_SAFE": "安全",
            "L2_REVIEW": "需审查",
            "L3_SYSTEM": "系统"
        }

        return risk_labels.get(risk.name, "未知")


def test_cleaner_view():
    """
    CleanerView Test Function

    测试清理视图的基本功能。
    """
    import tempfile

    print("=" * 60)
    print("CleanerView Test")
    print("=" * 60)

    # 创建测试窗口
    print("\n[Step 1] Creating test window...")
    root = tk.Tk()
    root.title("CleanerView Test")
    root.geometry("1200x800")

    # 创建主窗口
    print("\n[Step 2] Creating main window...")
    from src.ui.main_window import MainWindow
    from src.controllers.scan_controller import ScanController
    from src.controllers.clean_controller import CleanController
    from src.controllers.analysis_controller import AnalysisController

    scan_ctrl = ScanController()
    clean_ctrl = CleanController()
    analysis_ctrl = AnalysisController()

    main_window = MainWindow(
        root,
        scan_ctrl,
        clean_ctrl,
        analysis_ctrl
    )

    # 创建清理视图
    print("\n[Step 3] Creating cleaner view...")
    cleaner_view = CleanerView(root, main_window)
    cleaner_view.pack(fill=tk.BOTH, expand=True)
    print("  [OK] Cleaner view created")

    # 创建测试数据
    print("\n[Step 4] Creating test data...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir)

        # 创建测试文件
        test_files = []
        for i in range(20):
            file_path = test_path / f"test_{i}.tmp"
            file_path.write_text(f"Test content {i} " * 100)

            test_files.append(FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            ))

        # 加载测试数据
        print("\n[Step 5] Loading test data...")
        cleaner_view.load_scan_results(test_files)
        print(f"  [OK] Loaded {len(test_files)} test files")

        # 自动关闭
        root.after(3000, lambda: root.destroy())

        print("\n[Step 6] Displaying view (3 seconds)...")
        root.mainloop()

    print("\n" + "=" * 60)
    print("[OK] CleanerView test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_cleaner_view()
