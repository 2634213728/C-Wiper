"""
C-Wiper - C盘轻量化清理与分析工具

主程序入口文件

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import sys
import logging
import tkinter as tk
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.controllers.analysis_controller import AnalysisController
from src.ui.main_window import MainWindow


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('c-wiper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_admin_privileges() -> bool:
    """
    检查是否具有管理员权限

    Returns:
        bool: 是否具有管理员权限
    """
    import ctypes
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logger.error(f"Failed to check admin privileges: {e}")
        return False


def run_as_admin() -> None:
    """
    以管理员权限重新运行程序
    """
    import ctypes
    try:
        # 获取当前脚本路径
        script_path = sys.executable if getattr(sys, 'frozen', False) else __file__

        # 请求管理员权限重新运行
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            script_path,
            " ".join(sys.argv[1:]),
            None,
            1
        )
    except Exception as e:
        logger.error(f"Failed to restart as admin: {e}")


def main():
    """
    主函数

    初始化控制器和UI，启动应用程序。
    """
    logger.info("=" * 60)
    logger.info("C-Wiper 启动中...")
    logger.info("=" * 60)

    # 检查管理员权限（可选）
    is_admin = check_admin_privileges()

    if is_admin:
        logger.info("运行在管理员模式")
    else:
        logger.warning("未检测到管理员权限，某些功能可能受限")

        # 可选：提示用户以管理员权限运行
        # response = tk.messagebox.askyesno(
        #     "权限提示",
        #     "检测到当前不是管理员模式。\n"
        #     "建议以管理员权限运行以获得完整功能。\n\n"
        #     "是否以管理员权限重新启动？"
        # )
        # if response:
        #     run_as_admin()
        #     return

    try:
        # 创建 Tkinter 根窗口
        logger.info("初始化图形界面...")
        root = tk.Tk()
        root.title("C-Wiper")

        # 初始化控制器
        logger.info("初始化控制器...")
        scan_controller = ScanController()
        clean_controller = CleanController()
        analysis_controller = AnalysisController()

        # 初始化主窗口
        logger.info("初始化主窗口...")
        app = MainWindow(
            root,
            scan_controller,
            clean_controller,
            analysis_controller
        )

        logger.info("C-Wiper 启动完成")

        # 启动主循环
        root.mainloop()

        logger.info("C-Wiper 正常退出")

    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)

        # 显示错误对话框
        try:
            error_root = tk.Tk()
            error_root.withdraw()
            tk.messagebox.showerror(
                "启动失败",
                f"C-Wiper 启动失败！\n\n错误信息：{str(e)}\n\n请查看日志文件 c-wiper.log 获取详细信息。"
            )
            error_root.destroy()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
