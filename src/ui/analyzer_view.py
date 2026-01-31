"""
Analyzer View - 分析视图模块

本模块实现应用空间分析视图，显示应用占用空间和统计信息。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess

from src.ui.main_window import MainWindow
from src.core.analyzer import AppCluster
from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalyzerView(ttk.Frame):
    """
    分析视图类

    显示应用空间分析结果，包括应用列表、统计图表和操作按钮。

    Attributes:
        parent: 父容器
        main_window: 主窗口引用
        app_clusters: 应用簇列表
        selected_app: 选中的应用

    Example:
        >>> analyzer_view = AnalyzerView(parent_frame, main_window)
        >>> analyzer_view.pack(fill=tk.BOTH, expand=True)
    """

    def __init__(self, parent: tk.Widget, main_window: MainWindow):
        """
        初始化分析视图

        Args:
            parent: 父容器
            main_window: 主窗口引用
        """
        super().__init__(parent)
        self.main_window = main_window
        self.app_clusters: List[AppCluster] = []
        self.selected_app: Optional[AppCluster] = None

        # 创建UI组件
        self._create_header()
        self._create_control_panel()
        self._create_content_area()

        # 订阅分析完成事件
        self._subscribe_events()

        logger.info("AnalyzerView initialized")

    def _create_header(self) -> None:
        """创建标题区域"""
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=20)

        # 标题
        title_label = ttk.Label(
            header_frame,
            text="空间分析",
            font=('Microsoft YaHei UI', 18, 'bold')
        )
        title_label.pack(side=tk.LEFT)

        # 副标题
        subtitle_label = ttk.Label(
            header_frame,
            text="分析应用程序占用空间",
            font=('Microsoft YaHei UI', 10)
        )
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

    def _create_control_panel(self) -> None:
        """创建控制面板"""
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        # 开始分析按钮
        self.analyze_btn = ttk.Button(
            control_frame,
            text="开始分析",
            command=self._on_start_analysis,
            width=15
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 导出报告按钮
        export_btn = ttk.Button(
            control_frame,
            text="导出报告",
            command=self._on_export_report,
            width=12
        )
        export_btn.pack(side=tk.LEFT, padx=5)

        # 刷新按钮
        refresh_btn = ttk.Button(
            control_frame,
            text="刷新",
            command=self.refresh,
            width=10
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # 统计信息
        self.stats_label = ttk.Label(
            control_frame,
            text="未分析",
            font=('Microsoft YaHei UI', 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)

    def _create_content_area(self) -> None:
        """创建内容区域"""
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 使用 PanedWindow 分割左右两部分
        paned = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 左侧：应用列表
        left_frame = ttk.LabelFrame(paned, text="应用程序列表", padding=10)
        paned.add(left_frame, weight=2)

        self._create_app_list(left_frame)

        # 右侧：详细信息
        right_frame = ttk.LabelFrame(paned, text="详细信息", padding=10)
        paned.add(right_frame, weight=1)

        self._create_detail_view(right_frame)

    def _create_app_list(self, parent: ttk.Frame) -> None:
        """创建应用列表"""
        # 工具栏
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(toolbar_frame, text="排序:").pack(side=tk.LEFT, padx=(0, 5))

        self.sort_var = tk.StringVar(value="size")
        sort_combo = ttk.Combobox(
            toolbar_frame,
            textvariable=self.sort_var,
            values=["size", "name", "files"],
            state="readonly",
            width=10
        )
        sort_combo.pack(side=tk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", self._on_sort_changed)

        # 搜索框
        ttk.Label(toolbar_frame, text="搜索:").pack(side=tk.LEFT, padx=(20, 5))

        self.search_var = tk.StringVar()
        search_var_trace = self.search_var.trace_add("write", self._on_search_changed)

        search_entry = ttk.Entry(
            toolbar_frame,
            textvariable=self.search_var,
            width=20
        )
        search_entry.pack(side=tk.LEFT)

        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")

        columns = ("name", "size", "files")
        self.app_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set
        )

        self.app_tree.heading("name", text="应用名称")
        self.app_tree.heading("size", text="占用空间")
        self.app_tree.heading("files", text="文件数")

        self.app_tree.column("name", width=200, stretch=True)
        self.app_tree.column("size", width=100, stretch=False)
        self.app_tree.column("files", width=80, stretch=False)

        vsb.config(command=self.app_tree.yview)

        self.app_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定选择事件
        self.app_tree.bind("<<TreeviewSelect>>", self._on_app_selected)

    def _create_detail_view(self, parent: ttk.Frame) -> None:
        """创建详细信息视图"""
        # 应用名称
        self.detail_name_label = ttk.Label(
            parent,
            text="选择一个应用查看详情",
            font=('Microsoft YaHei UI', 14, 'bold')
        )
        self.detail_name_label.pack(pady=(0, 20), anchor=tk.W)

        # 统计卡片
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.X, pady=(0, 20))

        # 总大小
        size_frame = ttk.Frame(stats_frame)
        size_frame.pack(fill=tk.X, pady=5)
        ttk.Label(size_frame, text="总大小:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT)
        self.detail_size_label = ttk.Label(
            size_frame,
            text="-",
            font=('Microsoft YaHei UI', 12, 'bold'),
            foreground="#2196F3"
        )
        self.detail_size_label.pack(side=tk.RIGHT)

        # 静态文件数
        static_frame = ttk.Frame(stats_frame)
        static_frame.pack(fill=tk.X, pady=5)
        ttk.Label(static_frame, text="静态文件:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT)
        self.detail_static_label = ttk.Label(
            static_frame,
            text="-",
            font=('Microsoft YaHei UI', 11)
        )
        self.detail_static_label.pack(side=tk.RIGHT)

        # 动态文件数
        dynamic_frame = ttk.Frame(stats_frame)
        dynamic_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dynamic_frame, text="动态文件:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT)
        self.detail_dynamic_label = ttk.Label(
            dynamic_frame,
            text="-",
            font=('Microsoft YaHei UI', 11)
        )
        self.detail_dynamic_label.pack(side=tk.RIGHT)

        # 安装路径
        path_frame = ttk.Frame(stats_frame)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="安装路径:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT)
        self.detail_path_label = ttk.Label(
            path_frame,
            text="-",
            font=('Microsoft YaHei UI', 9),
            foreground="#757575"
        )
        self.detail_path_label.pack(side=tk.RIGHT)

        # 分隔线
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

        # 操作按钮
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Button(
            action_frame,
            text="打开文件夹",
            command=self._on_open_folder,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="查看文件列表",
            command=self._on_view_files,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        # 空间占比图表
        chart_frame = ttk.LabelFrame(parent, text="空间占比 Top 10", padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True)

        self.chart_canvas = tk.Canvas(
            chart_frame,
            bg='white',
            highlightthickness=0
        )
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)

    def refresh(self) -> None:
        """刷新视图"""
        self._update_stats()
        self._update_chart()

    def load_analysis_results(self, clusters: List[AppCluster]) -> None:
        """
        加载分析结果

        Args:
            clusters: 应用簇列表
        """
        self.app_clusters = clusters
        self._populate_app_list()
        self._update_stats()
        self._update_chart()

    def _populate_app_list(self) -> None:
        """填充应用列表"""
        # 清空现有项目
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)

        # 排序
        sorted_clusters = self._sort_clusters()

        # 添加到树形视图
        for cluster in sorted_clusters:
            self.app_tree.insert(
                "",
                tk.END,
                values=(
                    cluster.app_name,
                    cluster._format_size(cluster.total_size),
                    len(cluster.static_files) + len(cluster.dynamic_files)
                ),
                tags=(cluster.app_name,)
            )

            # 存储引用
            self.app_tree.set(
                self.app_tree.get_children()[-1],
                "cluster",
                cluster
            )

    def _sort_clusters(self) -> List[AppCluster]:
        """排序应用簇"""
        sort_by = self.sort_var.get()

        if sort_by == "size":
            return sorted(self.app_clusters, key=lambda x: x.total_size, reverse=True)
        elif sort_by == "name":
            return sorted(self.app_clusters, key=lambda x: x.app_name.lower())
        elif sort_by == "files":
            return sorted(
                self.app_clusters,
                key=lambda x: len(x.static_files) + len(x.dynamic_files),
                reverse=True
            )
        else:
            return self.app_clusters

    def _update_stats(self) -> None:
        """更新统计信息"""
        if not self.app_clusters:
            self.stats_label.config(text="未分析")
            return

        total_apps = len(self.app_clusters)
        total_size = sum(c.total_size for c in self.app_clusters)
        total_files = sum(
            len(c.static_files) + len(c.dynamic_files)
            for c in self.app_clusters
        )

        stats_text = (
            f"应用总数: {total_apps} | "
            f"总大小: {self._format_size(total_size)} | "
            f"文件总数: {total_files}"
        )

        self.stats_label.config(text=stats_text)

    def _update_chart(self) -> None:
        """更新空间占比图表"""
        if not self.app_clusters:
            self.chart_canvas.delete("all")
            self.chart_canvas.create_text(
                200, 150,
                text="暂无数据",
                font=('Microsoft YaHei UI', 12),
                fill='#757575'
            )
            return

        # 获取 Top 10
        top_10 = sorted(self.app_clusters, key=lambda x: x.total_size, reverse=True)[:10]

        # 清空画布
        self.chart_canvas.delete("all")

        # 绘制条形图
        canvas_width = self.chart_canvas.winfo_width()
        canvas_height = self.chart_canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            # 画布还未显示，延迟绘制
            self.chart_canvas.after(100, self._update_chart)
            return

        margin_left = 10
        margin_right = 50
        margin_top = 10
        margin_bottom = 30

        chart_width = canvas_width - margin_left - margin_right
        chart_height = canvas_height - margin_top - margin_bottom

        bar_height = chart_height / len(top_10)
        max_size = max(c.total_size for c in top_10)

        colors = [
            "#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0",
            "#00BCD4", "#8BC34A", "#FFC107", "#E91E63", "#3F51B5"
        ]

        for i, cluster in enumerate(top_10):
            y = margin_top + i * bar_height
            bar_width = (cluster.total_size / max_size) * chart_width
            color = colors[i % len(colors)]

            # 绘制条形
            self.chart_canvas.create_rectangle(
                margin_left, y + 5,
                margin_left + bar_width, y + bar_height - 5,
                fill=color,
                outline=""
            )

            # 应用名称
            self.chart_canvas.create_text(
                margin_left + 5, y + bar_height / 2,
                text=cluster.app_name[:20],
                anchor=tk.W,
                font=('Microsoft YaHei UI', 8)
            )

            # 大小标签
            self.chart_canvas.create_text(
                margin_left + bar_width + 5, y + bar_height / 2,
                text=cluster._format_size(cluster.total_size),
                anchor=tk.W,
                font=('Microsoft YaHei UI', 8)
            )

    def _on_sort_changed(self, event) -> None:
        """排序改变事件"""
        self._populate_app_list()

    def _on_search_changed(self, *args) -> None:
        """搜索改变事件"""
        search_term = self.search_var.get().lower()

        # 清空现有项目
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)

        # 筛选并添加
        for cluster in self.app_clusters:
            if search_term in cluster.app_name.lower():
                self.app_tree.insert(
                    "",
                    tk.END,
                    values=(
                        cluster.app_name,
                        cluster._format_size(cluster.total_size),
                        len(cluster.static_files) + len(cluster.dynamic_files)
                    )
                )

                # 存储引用
                self.app_tree.set(
                    self.app_tree.get_children()[-1],
                    "cluster",
                    cluster
                )

    def _on_app_selected(self, event) -> None:
        """应用选择事件"""
        selection = self.app_tree.selection()

        if not selection:
            return

        item = selection[0]
        cluster = self.app_tree.set(item, "cluster")

        if cluster:
            self.selected_app = cluster
            self._update_detail_view(cluster)

    def _update_detail_view(self, cluster: AppCluster) -> None:
        """更新详细信息视图"""
        self.detail_name_label.config(text=cluster.app_name)
        self.detail_size_label.config(text=cluster._format_size(cluster.total_size))
        self.detail_static_label.config(text=str(len(cluster.static_files)))
        self.detail_dynamic_label.config(text=str(len(cluster.dynamic_files)))
        self.detail_path_label.config(text=str(cluster.install_path))

    def _on_start_analysis(self) -> None:
        """开始分析按钮事件"""
        self.main_window.update_status("正在分析...")
        self.analyze_btn.config(state=tk.DISABLED)

        try:
            # 调用分析控制器
            success = self.main_window.analysis_controller.start_analysis(
                progress_callback=self._on_analysis_progress
            )

            if not success:
                messagebox.showerror("错误", "无法启动分析")
                self.analyze_btn.config(state=tk.NORMAL)
            else:
                logger.info("Analysis started")
                # 结果将通过事件处理

        except Exception as e:
            logger.error(f"Failed to start analysis: {e}")
            messagebox.showerror("错误", f"分析启动失败：{str(e)}")
            self.analyze_btn.config(state=tk.NORMAL)

    def _on_analysis_progress(self, stage: str, current: int, total: int) -> None:
        """分析进度回调"""
        progress = (current / total * 100) if total > 0 else 0
        self.main_window.update_status(f"{stage}... {current}/{total}", progress)

    def _on_export_report(self) -> None:
        """导出报告按钮事件"""
        if not self.app_clusters:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="导出分析报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            # 生成报告
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("C-Wiper 空间分析报告\n")
                f.write("=" * 60 + "\n\n")

                # 总体统计
                total_size = sum(c.total_size for c in self.app_clusters)
                total_files = sum(
                    len(c.static_files) + len(c.dynamic_files)
                    for c in self.app_clusters
                )

                f.write(f"应用总数: {len(self.app_clusters)}\n")
                f.write(f"总大小: {self._format_size(total_size)}\n")
                f.write(f"文件总数: {total_files}\n\n")

                f.write("-" * 60 + "\n")
                f.write("Top 10 应用\n")
                f.write("-" * 60 + "\n\n")

                # Top 10
                top_10 = sorted(self.app_clusters, key=lambda x: x.total_size, reverse=True)[:10]

                for i, cluster in enumerate(top_10, 1):
                    f.write(f"{i}. {cluster.app_name}\n")
                    f.write(f"   大小: {cluster._format_size(cluster.total_size)}\n")
                    f.write(f"   静态文件: {len(cluster.static_files)}\n")
                    f.write(f"   动态文件: {len(cluster.dynamic_files)}\n")
                    f.write(f"   路径: {cluster.install_path}\n\n")

            messagebox.showinfo("成功", f"报告已导出到：\n{file_path}")

        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            messagebox.showerror("错误", f"导出报告失败：{str(e)}")

    def _on_open_folder(self) -> None:
        """打开文件夹按钮事件"""
        if not self.selected_app:
            messagebox.showwarning("警告", "请先选择应用")
            return

        folder_path = str(self.selected_app.install_path)

        try:
            subprocess.Popen(['explorer', folder_path])
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            messagebox.showerror("错误", f"无法打开文件夹：{str(e)}")

    def _on_view_files(self) -> None:
        """查看文件列表按钮事件"""
        if not self.selected_app:
            messagebox.showwarning("警告", "请先选择应用")
            return

        # TODO: 显示文件列表对话框
        messagebox.showinfo("文件列表", "文件列表功能开发中...")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _subscribe_events(self) -> None:
        """订阅事件总线事件"""
        event_bus = EventBus()
        event_bus.subscribe(EventType.ANALYSIS_COMPLETED, self._on_analysis_completed)
        event_bus.subscribe(EventType.ANALYSIS_FAILED, self._on_analysis_failed)
        logger.debug("AnalyzerView subscribed to analysis events")

    def _on_analysis_completed(self, event: Event) -> None:
        """
        分析完成事件处理器

        从 AnalysisController 获取分析结果并加载到视图中。
        """
        try:
            clusters = self.main_window.analysis_controller.get_clusters()
            if clusters:
                logger.info(f"Loading {len(clusters)} app clusters into view")
                self.load_analysis_results(clusters)
                self.analyze_btn.config(state=tk.NORMAL)
            else:
                logger.warning("No clusters found")
                self.app_clusters.clear()
                self._populate_app_list()
                self._update_stats()
                self.analyze_btn.config(state=tk.NORMAL)
        except Exception as e:
            logger.error(f"Error loading analysis results: {e}", exc_info=True)
            self.analyze_btn.config(state=tk.NORMAL)

    def _on_analysis_failed(self, event: Event) -> None:
        """分析失败事件处理器"""
        reason = event.data.get('reason', '未知错误')
        logger.error(f"Analysis failed: {reason}")
        self.analyze_btn.config(state=tk.NORMAL)


def test_analyzer_view():
    """
    AnalyzerView Test Function

    测试分析视图的基本功能。
    """
    print("=" * 60)
    print("AnalyzerView Test")
    print("=" * 60)

    # 创建测试窗口
    print("\n[Step 1] Creating test window...")
    root = tk.Tk()
    root.title("AnalyzerView Test")
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

    # 创建分析视图
    print("\n[Step 3] Creating analyzer view...")
    analyzer_view = AnalyzerView(root, main_window)
    analyzer_view.pack(fill=tk.BOTH, expand=True)
    print("  [OK] Analyzer view created")

    # 自动关闭
    root.after(3000, lambda: root.destroy())

    print("\n[Step 4] Displaying view (3 seconds)...")
    root.mainloop()

    print("\n" + "=" * 60)
    print("[OK] AnalyzerView test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_analyzer_view()
