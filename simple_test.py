#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C-Wiper 简单启动脚本

绕过 UI 层，直接测试核心功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 简单日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s
)

logger = logging.getLogger(__name__)


def test_core_only():
    """仅测试核心功能，不启动 UI"""
    logger.info("=" * 60)
    logger.info("C-Wiper 核心功能测试")
    logger.info("=" * 60)

    try:
        # 1. 测试安全模块
        from src.core.security import SecurityLayer
        logger.info("1. 测试安全模块...")
        security = SecurityLayer()
        is_safe, reason = security.is_safe_to_delete(
            Path("C:/Windows/System32/notepad.exe"),
            []
        )
        logger.info(f"   安全检查: {is_safe}, {reason}")

        # 2. 测试规则引擎
        from src.core.rule_engine import RuleEngine
        logger.info("2. 测试规则引擎...")
        rule_engine = RuleEngine(Path("config/rules.json"))
        logger.info(f"   加载了 {len(rule_engine.rules)} 条规则")

        # 3. 测试扫描器
        from src.core.scanner import CoreScanner
        logger.info("3. 测试扫描器...")
        scanner = CoreScanner(None, None, use_winapi=False)

        # 4. 测试清理器
        from src.core.cleaner import CleanerExecutor
        logger.info("4. 测试清理器...")
        # 注意：这里不实际删除，只测试初始化
        # cleaner = CleanerExecutor(None, None, security)

        logger.info("\n" + "=" * 60)
        logger.info("SUCCESS - 所有核心模块初始化成功！")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def simple_test():
    """简单测试：扫描当前目录"""
    logger.info("=" * 60)
    logger.info("执行实际扫描测试...")
    logger.info("=" * 60)

    try:
        from src.core.scanner import CoreScanner
        from src.core.rule_engine import RuleEngine
        from src.core.security import SecurityLayer

        # 初始化
        security = SecurityLayer()
        rule_engine = RuleEngine(Path("config/rules.json"))
        scanner = CoreScanner(None, None, use_winapi=False)

        # 测试扫描当前目录
        logger.info("扫描当前目录...")
        from src.models.scan_result import ScanTarget

        target = ScanTarget(
            id="test",
            name="测试目录",
            path=Path.cwd(),
            requires_admin=False
        )

        # 执行扫描（只扫描前10个文件，避免太久）
        count = 0
        for result in scanner.scan([target]):
            for file_info in result.files:
                logger.info(f"  文件: {file_info.path.name} ({file_info.size} bytes)")
                count += 1
                if count >= 10:
                    break
            break

        logger.info(f"扫描完成，发现 {count} 个文件")

        # 测试规则匹配
        from src.models.scan_result import FileInfo
        from datetime import datetime

        test_file = FileInfo(
            path=Path.cwd() / "test.txt",
            size=1024,
            is_dir=False,
            modified_time=datetime.now()
        )

        match = rule_engine.match_file(test_file)
        logger.info(f"规则匹配测试: {match.matched} - {match.reason}")

        logger.info("扫描测试完成！")
        return True

    except Exception as e:
        logger.error(f"扫描测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("C-Wiper 简单启动脚本")
    print("=" * 60 + "\n")

    # 先测试核心模块
    if not test_core_only():
        print("\n核心功能测试失败")
        return False

    print("\n是否继续执行实际扫描测试？")
    print("这将扫描当前目录（仅前10个文件）")
    print("按 Ctrl+C 取消\n")

    try:
        # 简单测试
        import time
        time.sleep(2)

        choice = input("继续测试？[y/N]: ").strip().lower()
        if choice == 'y':
            simple_test()
        else:
            print("已跳过扫描测试")
            return True

    except KeyboardInterrupt:
        print("\n\n用户取消")
        return True

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已退出")
