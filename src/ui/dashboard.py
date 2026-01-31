"""
Dashboard - 仪表盘视图模块

本模块实现仪表盘视图，显示系统概览、C盘使用率和快捷操作。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional
import shutil

from src.ui.main_window import MainWindow


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Dashboard(ttk.Frame):
    """
    仪表盘视图类

    显示系统概览信息，包括C盘使用率环形图、快速统计和快捷操作按钮。

    Attributes:
        parent: 父容器
        main_window: 主窗口引用
        c_drive_path: C盘路径
        usage_canvas: 使用率绘图画布
        stats_labels: 统计信息标签字典

    Example:
        >>> dashboard = Dashboard(parent_frame, main_window)
        >>> dashboard.pack(fill=tk.BOTH, expand=True)
    """

    def __init__(self, parent: tk.Widget, main_window: MainWindow):
        """
        初始化仪表盘视图

        Args:
            parent: 父容器
            main_window: 主窗口引用
        """
        super().__init__(parent)
        self.main_window = main_window
        self.c_drive_path = Path("C:/")
        self.usage_canvas: Optional[tk.Canvas] = None
        self.stats_labels = {}

        # 创建UI
        self._create_header()
        self._create_main_content()
        self._create_quick_actions()

        # 刷新数据
        self.refresh()

        logger.info("Dashboard initialized")

    def _create_header(self) -> None:
        """创建标题区域"""
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=20)

        # 标题
        title_label = ttk.Label(
            header_frame,
            text="系统概览",
            font=('Microsoft YaHei UI', 18, 'bold')
        )
        title_label.pack(side=tk.LEFT)

        # 副标题
        subtitle_label = ttk.Label(
            header_frame,
            text="查看系统状态和快速操作",
            font=('Microsoft YaHei UI', 10)
        )
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

    def _create_main_content(self) -> None:
        """创建主要内容区域"""
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 左侧：C盘使用率
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_disk_usage_card(left_frame)

        # 右侧：统计信息
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))

        self._create_stats_cards(right_frame)

    def _create_disk_usage_card(self, parent: ttk.Frame) -> None:
        """创建C盘使用率卡片"""
        card_frame = ttk.LabelFrame(parent, text="C盘使用情况", padding=20)
        card_frame.pack(fill=tk.BOTH, expand=True)

        # 使用率环形图
        self.usage_canvas = tk.Canvas(
            card_frame,
            width=300,
            height=300,
            bg='#F5F5F5',
            highlightthickness=0
        )
        self.usage_canvas.pack(pady=20)

        # 使用率文本
        self.usage_label = ttk.Label(
            card_frame,
            text="正在获取...",
            font=('Microsoft YaHei UI', 24, 'bold')
        )
        self.usage_label.pack(pady=10)

        # 容量信息
        self.capacity_label = ttk.Label(
            card_frame,
            text="",
            font=('Microsoft YaHei UI', 10)
        )
        self.capacity_label.pack(pady=5)

    def _create_stats_cards(self, parent: ttk.Frame) -> None:
        """创建统计信息卡片"""
        # 临时文件统计
        temp_card, temp_value = self._create_stat_card(
            parent,
            "临时文件",
            "扫描系统中的临时文件",
            "#FF9800",
            self._on_scan_temp
        )
        temp_card.pack(fill=tk.X, pady=5)
        self.stats_labels['temp'] = temp_value

        # 缓存文件统计
        cache_card, cache_value = self._create_stat_card(
            parent,
            "缓存文件",
            "扫描应用程序缓存",
            "#2196F3",
            self._on_scan_cache
        )
        cache_card.pack(fill=tk.X, pady=5)
        self.stats_labels['cache'] = cache_value

        # 日志文件统计
        log_card, log_value = self._create_stat_card(
            parent,
            "日志文件",
            "扫描系统日志文件",
            "#4CAF50",
            self._on_scan_logs
        )
        log_card.pack(fill=tk.X, pady=5)
        self.stats_labels['logs'] = log_value

        # 回收站统计
        recycle_card, recycle_value = self._create_stat_card(
            parent,
            "回收站",
            "清空回收站",
            "#F44336",
            self._on_empty_recycle
        )
        recycle_card.pack(fill=tk.X, pady=5)
        self.stats_labels['recycle'] = recycle_value

    def _create_stat_card(
        self,
        parent: ttk.Frame,
        title: str,
        description: str,
        color: str,
        command
    ) -> tuple[ttk.Frame, ttk.Label]:
        """
        创建统计卡片

        Args:
            parent: 父容器
            title: 卡片标题
            description: 描述文本
            color: 主题颜色
            command: 点击命令

        Returns:
            tuple[ttk.Frame, ttk.Label]: (卡片框架, 数值标签)
        """
        card_frame = ttk.Frame(parent, style='Card.TFrame')
        card_frame.pack(fill=tk.X, pady=5)

        # 左侧：图标和标题
        left_frame = ttk.Frame(card_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            left_frame,
            text=title,
            font=('Microsoft YaHei UI', 12, 'bold')
        )
        title_label.pack(anchor=tk.W)

        # 描述
        desc_label = ttk.Label(
            left_frame,
            text=description,
            font=('Microsoft YaHei UI', 9),
            foreground='#757575'
        )
        desc_label.pack(anchor=tk.W)

        # 右侧：数值和操作
        right_frame = ttk.Frame(card_frame)
        right_frame.pack(side=tk.RIGHT)

        # 数值标签
        value_label = ttk.Label(
            right_frame,
            text="未扫描",
            font=('Microsoft YaHei UI', 11),
            foreground=color
        )
        value_label.pack(anchor=tk.E)

        # 操作按钮
        action_btn = ttk.Button(
            right_frame,
            text="扫描",
            command=command,
            width=8
        )
        action_btn.pack(anchor=tk.E, pady=(5, 0))

        # 分隔线
        ttk.Separator(card_frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, pady=10
        )

        return card_frame, value_label

    def _create_quick_actions(self) -> None:
        """创建快捷操作区域"""
        actions_frame = ttk.LabelFrame(self, text="快捷操作", padding=20)
        actions_frame.pack(fill=tk.X, padx=20, pady=20)

        # 开始大扫描按钮
        scan_btn = tk.Button(
            actions_frame,
            text="开始全面扫描",
            command=self._on_start_scan,
            font=('Microsoft YaHei UI', 14, 'bold'),
            bg='#2E86AB',
            fg='white',
            relief=tk.FLAT,
            cursor='hand2',
            padx=30,
            pady=15
        )
        scan_btn.pack(side=tk.LEFT, padx=10)

        # 空间分析按钮
        analyze_btn = tk.Button(
            actions_frame,
            text="空间分析",
            command=self._on_start_analysis,
            font=('Microsoft YaHei UI', 12),
            bg='#4CAF50',
            fg='white',
            relief=tk.FLAT,
            cursor='hand2',
            padx=20,
            pady=10
        )
        analyze_btn.pack(side=tk.LEFT, padx=10)

        # 设置按钮
        settings_btn = tk.Button(
            actions_frame,
            text="设置",
            command=self._on_settings,
            font=('Microsoft YaHei UI', 12),
            bg='#757575',
            fg='white',
            relief=tk.FLAT,
            cursor='hand2',
            padx=20,
            pady=10
        )
        settings_btn.pack(side=tk.RIGHT, padx=10)

    def refresh(self) -> None:
        """刷新仪表盘数据"""
        self._update_disk_usage()
        self._update_stats()

    def _update_disk_usage(self) -> None:
        """更新C盘使用率"""
        try:
            # 获取磁盘使用信息
            usage = shutil.disk_usage(self.c_drive_path)

            # 计算使用百分比
            used_percent = (usage.used / usage.total) * 100

            # 绘制环形图
            self._draw_usage_circle(used_percent)

            # 更新文本
            self.usage_label.config(text=f"{used_percent:.1f}%")

            # 更新容量信息
            used_gb = usage.used / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)

            self.capacity_label.config(
                text=f"已用 {used_gb:.1f} GB / 总共 {total_gb:.1f} GB\n"
                     f"可用 {free_gb:.1f} GB"
            )

            # 根据使用率设置颜色
            if used_percent < 70:
                color = "#4CAF50"  # 绿色
            elif used_percent < 90:
                color = "#FF9800"  # 橙色
            else:
                color = "#F44336"  # 红色

            self.usage_label.config(foreground=color)

        except Exception as e:
            logger.error(f"Failed to update disk usage: {e}")
            self.usage_label.config(text="获取失败")

    def _draw_usage_circle(self, percentage: float) -> None:
        """
        绘制使用率环形图

        Args:
            percentage: 使用百分比 (0-100)
        """
        if not self.usage_canvas:
            return

        self.usage_canvas.delete("all")

        center_x = 150
        center_y = 150
        radius = 100
        width = 20

        # 背景圆环
        self.usage_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            width=width,
            outline='#E0E0E0'
        )

        # 进度圆环
        if percentage > 0:
            # 确定颜色
            if percentage < 70:
                color = "#4CAF50"
            elif percentage < 90:
                color = "#FF9800"
            else:
                color = "#F44336"

            # 计算角度（从顶部开始，顺时针）
            start_angle = 90
            extent_angle = - (percentage / 100) * 360

            # 绘制进度弧
            self.usage_canvas.create_arc(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                start=start_angle,
                extent=extent_angle,
                width=width,
                style=tk.ARC,
                outline=color
            )

        # 中心图标
        self.usage_canvas.create_text(
            center_x, center_y,
            text="💾",
            font=('Segoe UI Emoji', 48)
        )

    def _update_stats(self) -> None:
        """更新统计信息（占位符，实际数据来自扫描结果）"""
        # TODO: 从控制器获取实际统计信息
        for key, label in self.stats_labels.items():
            label.config(text="未扫描")

    # 事件处理器
    def _on_scan_temp(self) -> None:
        """扫描临时文件按钮事件"""
        self.main_window.show_cleaner_view()
        messagebox.showinfo("提示", "即将扫描临时文件...")

    def _on_scan_cache(self) -> None:
        """扫描缓存文件按钮事件"""
        self.main_window.show_cleaner_view()
        messagebox.showinfo("提示", "即将扫描缓存文件...")

    def _on_scan_logs(self) -> None:
        """扫描日志文件按钮事件"""
        self.main_window.show_cleaner_view()
        messagebox.showinfo("提示", "即将扫描日志文件...")

    def _on_empty_recycle(self) -> None:
        """清空回收站按钮事件"""
        if messagebox.askyesno("确认", "确定要清空回收站吗？"):
            # TODO: 实现清空回收站功能
            messagebox.showinfo("提示", "清空回收站功能开发中...")

    def _on_start_scan(self) -> None:
        """开始全面扫描按钮事件"""
        self.main_window.show_cleaner_view()
        # 触发扫描
        # TODO: 调用扫描控制器

    def _on_start_analysis(self) -> None:
        """开始空间分析按钮事件"""
        self.main_window.show_analyzer_view()
        # 触发分析
        # TODO: 调用分析控制器

    def _on_settings(self) -> None:
        """设置按钮事件"""
        messagebox.showinfo("设置", "设置功能开发中...")


def test_dashboard():
    """
    Dashboard Test Function

    测试仪表盘视图的基本功能。
    """
    import sys

    print("=" * 60)
    print("Dashboard Test")
    print("=" * 60)

    # 创建测试窗口
    print("\n[Step 1] Creating test window...")
    root = tk.Tk()
    root.title("Dashboard Test")
    root.geometry("1000x700")

    # 创建主窗口实例（简化版）
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

    # 创建仪表盘
    print("\n[Step 3] Creating dashboard...")
    dashboard = Dashboard(root, main_window)
    dashboard.pack(fill=tk.BOTH, expand=True)
    print("  [OK] Dashboard created")

    # 刷新数据
    print("\n[Step 4] Refreshing dashboard data...")
    dashboard.refresh()
    root.update()
    print("  [OK] Dashboard refreshed")

    # 测试自动关闭
    root.after(3000, lambda: root.destroy())

    print("\n[Step 5] Displaying dashboard (3 seconds)...")
    print("  [INFO] Window will close automatically after display")
    root.mainloop()

    print("\n" + "=" * 60)
    print("[OK] Dashboard test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_dashboard()
