"""
Main Window - 主窗口模块

本模块实现 C-Wiper 应用的主窗口，包括菜单栏、工具栏、状态栏和页面切换逻辑。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any

from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.controllers.analysis_controller import AnalysisController
from src.utils.event_bus import EventBus, EventType, Event
from src.controllers.state_manager import StateManager, SystemState


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MainWindow:
    """
    主窗口类

    实现应用主窗口，包含菜单栏、工具栏、状态栏和三个主要视图页面。
    采用 MVC 模式，与控制器层松耦合。

    Attributes:
        root: Tkinter 根窗口
        scan_controller: 扫描控制器实例
        clean_controller: 清理控制器实例
        analysis_controller: 分析控制器实例
        event_bus: 事件总线实例
        state_manager: 状态管理器实例
        current_view: 当前显示的视图
        status_var: 状态栏文本变量
        progress_var: 进度条变量

    Example:
        >>> root = tk.Tk()
        >>> scan_ctrl = ScanController()
        >>> clean_ctrl = CleanController()
        >>> analysis_ctrl = AnalysisController()
        >>> app = MainWindow(root, scan_ctrl, clean_ctrl, analysis_ctrl)
        >>> root.mainloop()
    """

    # 窗口配置
    WINDOW_TITLE = "C-Wiper - C盘轻量化清理与分析工具"
    WINDOW_MIN_SIZE = (900, 600)
    WINDOW_SIZE = "1200x800"

    # 颜色主题
    COLOR_PRIMARY = "#2E86AB"  # 主色调
    COLOR_SUCCESS = "#4CAF50"  # 成功色
    COLOR_WARNING = "#FF9800"  # 警告色
    COLOR_ERROR = "#F44336"    # 错误色
    COLOR_BG = "#F5F5F5"       # 背景色
    COLOR_FG = "#212121"       # 前景色

    def __init__(
        self,
        root: tk.Tk,
        scan_controller: ScanController,
        clean_controller: CleanController,
        analysis_controller: AnalysisController,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        """
        初始化主窗口

        Args:
            root: Tkinter 根窗口
            scan_controller: 扫描控制器实例
            clean_controller: 清理控制器实例
            analysis_controller: 分析控制器实例
            event_bus: 事件总线实例，默认使用全局单例
            state_manager: 状态管理器实例，默认使用全局单例
        """
        self.root = root
        self.scan_controller = scan_controller
        self.clean_controller = clean_controller
        self.analysis_controller = analysis_controller
        self.event_bus = event_bus or EventBus()
        self.state_manager = state_manager or StateManager()

        # UI 变量
        self.status_var = tk.StringVar(value="就绪")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.current_view: Optional[tk.Frame] = None

        # 容器引用
        self.menu_bar: Optional[tk.Menu] = None
        self.toolbar_frame: Optional[ttk.Frame] = None
        self.status_bar_frame: Optional[ttk.Frame] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.content_frame: Optional[ttk.Frame] = None

        # 视图容器
        self.views: Dict[str, tk.Frame] = {}

        # 配置窗口
        self._setup_window()
        self._setup_styles()

        # 创建 UI 组件
        self.create_menu()
        self.create_toolbar()
        self.create_status_bar()
        self.create_content_area()

        # 订阅事件
        self._subscribe_events()

        # 显示默认页面
        self.show_dashboard()

        logger.info("MainWindow initialized")

    def _setup_window(self) -> None:
        """配置窗口基本属性"""
        self.root.title(self.WINDOW_TITLE)
        self.root.geometry(self.WINDOW_SIZE)
        self.root.minsize(*self.WINDOW_MIN_SIZE)

        # 设置窗口图标（如果存在）
        try:
            # TODO: 添加应用图标
            # self.root.iconbitmap('assets/icon.ico')
            pass
        except Exception as e:
            logger.warning(f"Failed to load window icon: {e}")

        # 居中显示
        self._center_window()

    def _center_window(self) -> None:
        """将窗口居中显示在屏幕上"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _setup_styles(self) -> None:
        """配置 UI 样式"""
        style = ttk.Style()

        # 设置主题
        try:
            style.theme_use('clam')
        except:
            pass

        # 自定义样式
        style.configure('Primary.TButton', font=('Microsoft YaHei UI', 10))
        style.configure('Toolbar.TFrame', background='#ECECEC')
        style.configure('Status.TLabel', font=('Microsoft YaHei UI', 9))
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 14, 'bold'))

    def create_menu(self) -> None:
        """
        创建菜单栏

        创建包含文件、编辑、视图、帮助等菜单的菜单栏。
        """
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # 文件菜单
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="退出", command=self._on_exit, accelerator="Alt+F4")

        # 编辑菜单
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="首选项", command=self._on_preferences)
        edit_menu.add_separator()
        edit_menu.add_command(label="清空缓存", command=self._on_clear_cache)

        # 视图菜单
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="仪表盘", command=self.show_dashboard, accelerator="Ctrl+1")
        view_menu.add_command(label="清理工具", command=self.show_cleaner_view, accelerator="Ctrl+2")
        view_menu.add_command(label="空间分析", command=self.show_analyzer_view, accelerator="Ctrl+3")
        view_menu.add_separator()
        view_menu.add_command(label="刷新", command=self._on_refresh, accelerator="F5")

        # 帮助菜单
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用指南", command=self._on_help)
        help_menu.add_command(label="关于", command=self._on_about)

        # 绑定快捷键
        self.root.bind('<Control-1>', lambda e: self.show_dashboard())
        self.root.bind('<Control-2>', lambda e: self.show_cleaner_view())
        self.root.bind('<Control-3>', lambda e: self.show_analyzer_view())
        self.root.bind('<F5>', lambda e: self._on_refresh())

        logger.debug("Menu bar created")

    def create_toolbar(self) -> None:
        """
        创建工具栏

        创建包含快捷操作按钮的工具栏。
        """
        self.toolbar_frame = ttk.Frame(self.root, relief=tk.RAISED)
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # 快速扫描按钮
        scan_btn = ttk.Button(
            self.toolbar_frame,
            text="快速扫描",
            command=self._on_quick_scan,
            style='Primary.TButton'
        )
        scan_btn.pack(side=tk.LEFT, padx=5)

        # 空间分析按钮
        analyze_btn = ttk.Button(
            self.toolbar_frame,
            text="空间分析",
            command=self._on_quick_analyze,
            style='Primary.TButton'
        )
        analyze_btn.pack(side=tk.LEFT, padx=5)

        # 分隔符
        ttk.Separator(self.toolbar_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        # 管理员模式指示器
        self.admin_label = ttk.Label(
            self.toolbar_frame,
            text="● 普通模式",
            foreground=self.COLOR_WARNING,
            font=('Microsoft YaHei UI', 9)
        )
        self.admin_label.pack(side=tk.LEFT, padx=5)
        self._update_admin_indicator()

        # 右侧填充
        ttk.Label(self.toolbar_frame, text="").pack(side=tk.RIGHT, expand=True)

        logger.debug("Toolbar created")

    def create_status_bar(self) -> None:
        """
        创建状态栏

        创建显示系统状态和进度的状态栏。
        """
        self.status_bar_frame = ttk.Frame(self.root)
        self.status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 状态标签
        status_label = ttk.Label(
            self.status_bar_frame,
            textvariable=self.status_var,
            style='Status.TLabel',
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.X, expand=True)

        # 进度条
        self.progress_bar = ttk.Progressbar(
            self.status_bar_frame,
            variable=self.progress_var,
            maximum=100,
            length=200,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=5, pady=2)
        self.progress_bar.pack_forget()  # 默认隐藏

        logger.debug("Status bar created")

    def create_content_area(self) -> None:
        """
        创建内容区域

        创建用于显示不同视图的内容容器。
        """
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        logger.debug("Content area created")

    def show_dashboard(self) -> None:
        """
        显示仪表盘视图

        切换到仪表盘页面，显示系统概览和快捷操作。
        """
        # 清除当前视图
        self._clear_current_view()

        # 创建仪表盘视图
        from src.ui.dashboard import Dashboard
        dashboard = Dashboard(self.content_frame, self)
        dashboard.pack(fill=tk.BOTH, expand=True)

        self.current_view = dashboard
        self.views['dashboard'] = dashboard

        self.update_status("仪表盘")
        logger.info("Switched to Dashboard view")

    def show_cleaner_view(self) -> None:
        """
        显示清理视图

        切换到清理页面，显示扫描结果和清理操作。
        """
        # 清除当前视图
        self._clear_current_view()

        # 创建清理视图
        from src.ui.cleaner_view import CleanerView
        cleaner_view = CleanerView(self.content_frame, self)
        cleaner_view.pack(fill=tk.BOTH, expand=True)

        self.current_view = cleaner_view
        self.views['cleaner'] = cleaner_view

        self.update_status("清理工具")
        logger.info("Switched to Cleaner view")

    def show_analyzer_view(self) -> None:
        """
        显示分析视图

        切换到分析页面，显示应用空间分析结果。
        """
        # 清除当前视图
        self._clear_current_view()

        # 创建分析视图
        from src.ui.analyzer_view import AnalyzerView
        analyzer_view = AnalyzerView(self.content_frame, self)
        analyzer_view.pack(fill=tk.BOTH, expand=True)

        self.current_view = analyzer_view
        self.views['analyzer'] = analyzer_view

        self.update_status("空间分析")
        logger.info("Switched to Analyzer view")

    def update_status(self, message: str, progress: Optional[float] = None) -> None:
        """
        更新状态栏

        Args:
            message: 状态消息
            progress: 进度值（0-100），None 表示隐藏进度条
        """
        self.status_var.set(message)

        if progress is not None:
            self.progress_var.set(progress)
            self.progress_bar.pack(side=tk.RIGHT, padx=5, pady=2)
        else:
            self.progress_bar.pack_forget()

        logger.debug(f"Status updated: {message}")

    def show_progress(self, show: bool = True) -> None:
        """
        显示或隐藏进度条

        Args:
            show: True 显示进度条，False 隐藏进度条
        """
        if show:
            self.progress_bar.pack(side=tk.RIGHT, padx=5, pady=2)
        else:
            self.progress_bar.pack_forget()

    def _clear_current_view(self) -> None:
        """清除当前视图"""
        if self.current_view:
            self.current_view.destroy()
            self.current_view = None

    def _update_admin_indicator(self) -> None:
        """更新管理员模式指示器"""
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                self.admin_label.config(
                    text="● 管理员模式",
                    foreground=self.COLOR_SUCCESS
                )
            else:
                self.admin_label.config(
                    text="● 普通模式",
                    foreground=self.COLOR_WARNING
                )
        except Exception as e:
            logger.warning(f"Failed to check admin status: {e}")
            self.admin_label.config(text="● 未知模式", foreground=self.COLOR_FG)

    def _subscribe_events(self) -> None:
        """订阅事件总线事件"""
        # 扫描事件
        self.event_bus.subscribe(EventType.SCAN_PROGRESS, self._on_scan_progress)
        self.event_bus.subscribe(EventType.SCAN_COMPLETED, self._on_scan_completed)
        self.event_bus.subscribe(EventType.SCAN_FAILED, self._on_scan_failed)

        # 清理事件
        self.event_bus.subscribe(EventType.CLEAN_PROGRESS, self._on_clean_progress)
        self.event_bus.subscribe(EventType.CLEAN_COMPLETED, self._on_clean_completed)
        self.event_bus.subscribe(EventType.CLEAN_FAILED, self._on_clean_failed)

        # 分析事件
        self.event_bus.subscribe(EventType.ANALYSIS_PROGRESS, self._on_analysis_progress)
        self.event_bus.subscribe(EventType.ANALYSIS_COMPLETED, self._on_analysis_completed)
        self.event_bus.subscribe(EventType.ANALYSIS_FAILED, self._on_analysis_failed)

        # 系统事件
        self.event_bus.subscribe(EventType.SYSTEM_STATE_CHANGED, self._on_state_changed)

        logger.debug("Subscribed to event bus events")

    # 事件处理器
    def _on_scan_progress(self, event: Event) -> None:
        """处理扫描进度事件"""
        data = event.data
        current = data.get('current', 0)
        total = data.get('total', 100)
        progress = (current / total * 100) if total > 0 else 0
        self.update_status(f"扫描中... {current}/{total}", progress)

    def _on_scan_completed(self, event: Event) -> None:
        """处理扫描完成事件"""
        data = event.data
        total_files = data.get('total_files', 0)
        total_size = data.get('total_size', 0)
        self.update_status(f"扫描完成：{total_files} 个文件")
        messagebox.showinfo("扫描完成", f"扫描完成！\n发现 {total_files} 个文件\n总大小：{self._format_size(total_size)}")

    def _on_scan_failed(self, event: Event) -> None:
        """处理扫描失败事件"""
        reason = event.data.get('reason', '未知错误')
        self.update_status("扫描失败")
        messagebox.showerror("扫描失败", f"扫描失败：{reason}")

    def _on_clean_progress(self, event: Event) -> None:
        """处理清理进度事件"""
        data = event.data
        current = data.get('current', 0)
        total = data.get('total', 100)
        progress = (current / total * 100) if total > 0 else 0
        self.update_status(f"清理中... {current}/{total}", progress)

    def _on_clean_completed(self, event: Event) -> None:
        """处理清理完成事件"""
        data = event.data
        files_deleted = data.get('files_deleted', 0)
        freed_space = data.get('freed_space', 0)
        self.update_status("清理完成")
        messagebox.showinfo("清理完成", f"清理完成！\n删除 {files_deleted} 个文件\n释放空间：{self._format_size(freed_space)}")

    def _on_clean_failed(self, event: Event) -> None:
        """处理清理失败事件"""
        reason = event.data.get('reason', '未知错误')
        self.update_status("清理失败")
        messagebox.showerror("清理失败", f"清理失败：{reason}")

    def _on_analysis_progress(self, event: Event) -> None:
        """处理分析进度事件"""
        data = event.data
        stage = data.get('stage', '分析中')
        current = data.get('current', 0)
        total = data.get('total', 100)
        progress = (current / total * 100) if total > 0 else 0
        self.update_status(f"{stage}... {current}/{total}", progress)

    def _on_analysis_completed(self, event: Event) -> None:
        """处理分析完成事件"""
        data = event.data
        app_count = data.get('app_count', 0)
        self.update_status("分析完成")
        messagebox.showinfo("分析完成", f"分析完成！\n发现 {app_count} 个应用程序")

    def _on_analysis_failed(self, event: Event) -> None:
        """处理分析失败事件"""
        reason = event.data.get('reason', '未知错误')
        self.update_status("分析失败")
        messagebox.showerror("分析失败", f"分析失败：{reason}")

    def _on_state_changed(self, event: Event) -> None:
        """处理系统状态变化事件"""
        new_state = event.data.get('new_state', 'idle')
        logger.info(f"System state changed to: {new_state}")

    # 菜单和工具栏事件处理器
    def _on_quick_scan(self) -> None:
        """快速扫描按钮事件"""
        self.show_cleaner_view()
        # TODO: 触发快速扫描

    def _on_quick_analyze(self) -> None:
        """空间分析按钮事件"""
        self.show_analyzer_view()
        # TODO: 触发空间分析

    def _on_exit(self) -> None:
        """退出应用"""
        if messagebox.askokcancel("退出", "确定要退出 C-Wiper 吗？"):
            # 检查是否有正在进行的操作
            if not self.state_manager.is_idle():
                if not messagebox.askyesno("确认", "有正在进行的操作，确定要强制退出吗？"):
                    return
            self.root.quit()

    def _on_preferences(self) -> None:
        """首选项对话框"""
        messagebox.showinfo("首选项", "首选项功能开发中...")

    def _on_clear_cache(self) -> None:
        """清空缓存"""
        # TODO: 实现清空缓存功能
        messagebox.showinfo("清空缓存", "清空缓存功能开发中...")

    def _on_refresh(self) -> None:
        """刷新当前视图"""
        if self.current_view and hasattr(self.current_view, 'refresh'):
            self.current_view.refresh()
        self.update_status("已刷新")

    def _on_help(self) -> None:
        """帮助文档"""
        messagebox.showinfo(
            "使用指南",
            "C-Wiper 使用指南\n\n"
            "1. 仪表盘：查看系统概览\n"
            "2. 清理工具：扫描并清理垃圾文件\n"
            "3. 空间分析：分析应用占用空间\n\n"
            "详细文档请访问项目主页。"
        )

    def _on_about(self) -> None:
        """关于对话框"""
        messagebox.showinfo(
            "关于 C-Wiper",
            "C-Wiper v1.0\n\n"
            "C盘轻量化清理与分析工具\n\n"
            "开发团队：C-Wiper Team\n"
            "许可协议：MIT License\n\n"
            "© 2026 C-Wiper Project"
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """
        格式化文件大小为人类可读格式

        Args:
            size_bytes: 大小（字节）

        Returns:
            str: 格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def test_main_window():
    """
    MainWindow Test Function

    测试主窗口的基本功能。
    """
    import sys

    print("=" * 60)
    print("MainWindow Test")
    print("=" * 60)

    # 创建控制器实例
    print("\n[Step 1] Creating controllers...")
    scan_controller = ScanController()
    clean_controller = CleanController()
    analysis_controller = AnalysisController()
    print("  [OK] Controllers created")

    # 创建主窗口
    print("\n[Step 2] Creating main window...")
    root = tk.Tk()
    app = MainWindow(
        root,
        scan_controller,
        clean_controller,
        analysis_controller
    )
    print("  [OK] Main window created")

    # 测试视图切换
    print("\n[Step 3] Testing view switching...")

    # 模拟切换到清理视图
    def test_switch_to_cleaner():
        print("  [TEST] Switching to cleaner view...")
        app.show_cleaner_view()
        root.update()

    # 模拟切换到分析视图
    def test_switch_to_analyzer():
        print("  [TEST] Switching to analyzer view...")
        app.show_analyzer_view()
        root.update()

    # 模拟切换回仪表盘
    def test_switch_to_dashboard():
        print("  [TEST] Switching to dashboard...")
        app.show_dashboard()
        root.update()

    # 延迟执行测试
    root.after(1000, test_switch_to_cleaner)
    root.after(2000, test_switch_to_analyzer)
    root.after(3000, test_switch_to_dashboard)
    root.after(4000, lambda: root.destroy())

    print("\n[Step 4] Starting main loop (4 seconds)...")
    print("  [INFO] Window will close automatically after tests")
    root.mainloop()

    print("\n" + "=" * 60)
    print("[OK] MainWindow test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_main_window()
