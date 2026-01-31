#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C-Wiper 快速启动脚本

测试核心功能是否正常
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志到控制台（简化版）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_imports():
    """测试所有模块导入"""
    logger.info("=" * 50)
    logger.info("测试模块导入...")
    logger.info("=" * 50)

    try:
        import send2trash
        logger.info("✓ send2trash")

        import customtkinter
        logger.info("✓ customtkinter")

        from src.controllers.scan_controller import ScanController
        logger.info("✓ ScanController")

        from src.controllers.clean_controller import CleanController
        logger.info("✓ CleanController")

        from src.controllers.analysis_controller import AnalysisController
        logger.info("✓ AnalysisController")

        from src.ui.main_window import MainWindow
        logger.info("✓ MainWindow")

        logger.info("所有模块导入成功！")
        return True

    except Exception as e:
        logger.error(f"模块导入失败: {e}")
        return False


def test_controllers():
    """测试控制器初始化"""
    logger.info("=" * 50)
    logger.info("测试控制器初始化...")
    logger.info("=" * 50)

    try:
        from src.controllers.scan_controller import ScanController
        from src.controllers.clean_controller import CleanController
        from src.controllers.analysis_controller import AnalysisController

        scan_controller = ScanController()
        logger.info("✓ ScanController 初始化成功")

        clean_controller = CleanController()
        logger.info("✓ CleanController 初始化成功")

        analysis_controller = AnalysisController()
        logger.info("✓ AnalysisController 初始化成功")

        logger.info("所有控制器初始化成功！")
        return True

    except Exception as e:
        logger.error(f"控制器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_functionality():
    """测试基本功能"""
    logger.info("=" * 50)
    logger.info("测试基本功能...")
    logger.info("=" * 50)

    try:
        # 测试扫描器
        from src.core.scanner import CoreScanner
        from src.core.rule_engine import RuleEngine
        from src.core.security import SecurityLayer

        # 测试安全模块
        security = SecurityLayer()
        from pathlib import Path
        is_safe, reason = security.is_safe_to_delete(Path("C:\\Windows\\System32\\notepad.exe"), [])
        logger.info(f"✓ 安全检查测试: {is_safe}, {reason}")

        # 测试规则引擎
        rule_engine = RuleEngine(Path("config/rules.json"))
        logger.info("✓ 规则引擎加载成功")

        # 测试扫描器
        scanner = CoreScanner(None, None, use_winapi=False)
        logger.info("✓ 扫描器初始化成功")

        logger.info("基本功能测试通过！")
        return True

    except Exception as e:
        logger.error(f"基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("C-Wiper 快速功能测试")
    print("=" * 60 + "\n")

    # 测试导入
    if not test_imports():
        print("\n❌ 模块导入失败，请检查依赖")
        return False

    print()

    # 测试控制器
    if not test_controllers():
        print("\n❌ 控制器初始化失败")
        return False

    print()

    # 测试基本功能
    if not test_basic_functionality():
        print("\n❌ 基本功能测试失败")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！C-Wiper 核心功能正常")
    print("=" * 60)
    print("\n您现在可以运行以下命令启动 GUI:")
    print("  python main.py")
    print()
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试脚本出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
