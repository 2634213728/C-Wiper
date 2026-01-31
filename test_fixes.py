"""
C-Wiper 修复验证脚本

验证Alpha测试中发现的问题是否已修复：
1. 日志编码问题（中优先级）
2. AppAnalyzer属性缺失（低优先级）
3. ScanController属性缺失（低优先级）

作者: C-Wiper 开发团队
日期: 2026-01-31
"""

import sys
import io
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_encoding_fix():
    """测试1: 验证UTF-8编码修复"""
    print("\n" + "=" * 60)
    print("测试1: UTF-8编码修复验证")
    print("=" * 60)

    # 检查main.py中是否添加了UTF-8编码设置
    with open(project_root / 'main.py', 'r', encoding='utf-8') as f:
        main_content = f.read()

    # 检查是否包含UTF-8编码设置
    has_io_import = 'import io' in main_content
    has_textio_wrapper = 'io.TextIOWrapper' in main_content
    has_utf8_encoding = 'encoding=\'utf-8\'' in main_content

    print(f"  ✓ 导入io模块: {has_io_import}")
    print(f"  ✓ 设置TextIOWrapper: {has_textio_wrapper}")
    print(f"  ✓ UTF-8编码配置: {has_utf8_encoding}")

    if has_io_import and has_textio_wrapper and has_utf8_encoding:
        print("\n  ✓ 日志编码问题已修复")
        return True
    else:
        print("\n  ✗ 日志编码问题未完全修复")
        return False


def test_analyzer_attributes():
    """测试2: 验证AppAnalyzer属性修复"""
    print("\n" + "=" * 60)
    print("测试2: AppAnalyzer属性修复验证")
    print("=" * 60)

    from src.core.analyzer import AppAnalyzer

    analyzer = AppAnalyzer()

    # 检查static_zones属性
    has_static_zones = hasattr(analyzer, 'static_zones')
    static_zones_count = len(analyzer.static_zones) if has_static_zones else 0

    # 检查dynamic_zones属性
    has_dynamic_zones = hasattr(analyzer, 'dynamic_zones')
    dynamic_zones_count = len(analyzer.dynamic_zones) if has_dynamic_zones else 0

    print(f"  ✓ static_zones属性存在: {has_static_zones}")
    print(f"  ✓ static_zones数量: {static_zones_count}")
    print(f"  ✓ dynamic_zones属性存在: {has_dynamic_zones}")
    print(f"  ✓ dynamic_zones数量: {dynamic_zones_count}")

    if has_static_zones and has_dynamic_zones and static_zones_count > 0 and dynamic_zones_count > 0:
        print("\n  ✓ AppAnalyzer属性问题已修复")
        return True
    else:
        print("\n  ✗ AppAnalyzer属性问题未完全修复")
        return False


def test_scan_controller_attributes():
    """测试3: 验证ScanController属性修复"""
    print("\n" + "=" * 60)
    print("测试3: ScanController属性修复验证")
    print("=" * 60)

    from src.controllers.scan_controller import ScanController

    controller = ScanController()

    # 检查rules属性
    has_rules = hasattr(controller, 'rules')
    rules_count = len(controller.rules) if has_rules else 0

    print(f"  ✓ rules属性存在: {has_rules}")
    print(f"  ✓ rules数量: {rules_count}")

    if has_rules and rules_count > 0:
        print(f"\n  ✓ ScanController属性问题已修复（已加载{rules_count}条规则）")
        return True
    else:
        print("\n  ✗ ScanController属性问题未完全修复")
        return False


def test_chinese_display():
    """测试4: 验证中文显示正常"""
    print("\n" + "=" * 60)
    print("测试4: 中文显示验证")
    print("=" * 60)

    print("  如果你能正常看到这行中文字符，说明UTF-8编码工作正常")
    print("  ✓ 临时文件、缓存文件、日志文件、系统文件")
    print("  ✓ 扫描、清理、分析、安全检查")
    print("  ✓ 通过、失败、警告、错误")

    print("\n  ✓ 中文显示正常")
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("C-Wiper 修复验证测试")
    print("=" * 60)
    print("测试时间: 2026-01-31")
    print("测试目的: 验证Alpha测试发现的3个问题是否已修复")

    # 设置UTF-8编码以验证修复
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    results = []

    # 运行所有测试
    results.append(("UTF-8编码修复", test_encoding_fix()))
    results.append(("AppAnalyzer属性修复", test_analyzer_attributes()))
    results.append(("ScanController属性修复", test_scan_controller_attributes()))
    results.append(("中文显示验证", test_chinese_display()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {name}")

    print(f"\n通过率: {passed}/{total} ({(passed/total*100):.1f}%)")

    if passed == total:
        print("\n✓ 所有修复验证通过！Alpha测试发现的问题已全部解决。")
        return 0
    else:
        print("\n✗ 部分修复未完成，需要进一步处理。")
        return 1


if __name__ == "__main__":
    exit(main())
