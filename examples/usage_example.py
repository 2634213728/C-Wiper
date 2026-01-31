"""
C-Wiper 使用示例

本示例展示如何使用 CoreScanner 和 RuleEngine 进行文件扫描和规则匹配。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.scanner import CoreScanner
from src.core.rule_engine import RuleEngine, RiskLevel
from src.models.scan_result import ScanTarget
from src.utils.event_bus import EventBus, EventType


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_section(text):
    """打印小节"""
    print(f"\n{text}")
    print("-" * 60)


def example_1_basic_scan():
    """示例 1: 基本扫描"""
    print_header("示例 1: 基本文件扫描")

    # 创建扫描器
    scanner = CoreScanner()

    # 定义扫描目标（使用 Windows 临时目录）
    import tempfile
    temp_dir = Path(tempfile.gettempdir())

    target = ScanTarget(
        id="temp_files",
        name="临时文件目录",
        path=temp_dir,
        description="扫描 Windows 临时文件目录"
    )

    print(f"扫描目标: {target.name}")
    print(f"扫描路径: {target.path}")

    # 执行扫描（限制前 10 个文件，避免扫描时间过长）
    result = scanner.scan_single_target(target)

    print(f"\n扫描结果:")
    print(f"  文件数量: {result.file_count}")
    print(f"  目录数量: {result.dir_count}")
    print(f"  总大小: {result.format_total_size()}")
    print(f"  扫描耗时: {result.scan_duration:.2f} 秒")

    # 显示前 5 个文件
    print(f"\n前 5 个文件:")
    for i, file_info in enumerate(result.files[:5], 1):
        print(f"  {i}. {file_info.path.name} ({file_info.format_size()})")


def example_2_rule_matching():
    """示例 2: 规则匹配"""
    print_header("示例 2: 文件规则匹配")

    # 创建规则引擎
    engine = RuleEngine()
    engine.load_rules()

    print(f"已加载 {len(engine.get_enabled_rules())} 条规则")

    # 显示所有规则
    print_section("规则列表:")
    rules = engine.get_enabled_rules()
    for i, rule in enumerate(rules, 1):
        print(f"  {i}. [{rule.risk_level.name}] {rule.name} ({rule.category})")

    # 创建测试文件
    import tempfile
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建不同类型的测试文件
        test_files = [
            ("temp_file.tmp", "临时文件内容"),
            ("app_log.log", "应用程序日志"),
            ("cache_file.cache", "缓存数据"),
            ("normal_doc.txt", "普通文档")
        ]

        for filename, content in test_files:
            (Path(tmpdir) / filename).write_text(content)

        print_section(f"\n测试文件匹配:")
        for filename, _ in test_files:
            file_path = Path(tmpdir) / filename

            from src.models.scan_result import FileInfo
            file_info = FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=time.time()
            )

            match = engine.match_file(file_info)

            if match.matched:
                print(f"  [{match.risk_level.name}] {filename:20} -> {match.rule.name}")
            else:
                print(f"  [UNMATCHED]  {filename:20} -> 无匹配规则")


def example_3_combined_scan():
    """示例 3: 扫描 + 规则匹配"""
    print_header("示例 3: 完整扫描流程（扫描 + 规则匹配）")

    # 创建测试环境
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建测试文件
        test_files = {
            "temp1.tmp": "Temporary file",
            "temp2.temp": "Temporary file 2",
            "app.log": "Application log",
            "data.cache": "Cache data",
            "document.txt": "Normal document",
            "backup.bak": "Backup file"
        }

        for filename, content in test_files.items():
            (test_dir / filename).write_text(content)

        print(f"创建测试目录: {test_dir}")
        print(f"创建文件数: {len(test_files)}")

        # 执行扫描
        print_section("\n执行扫描:")
        scanner = CoreScanner()
        engine = RuleEngine()
        engine.load_rules()

        target = ScanTarget(
            id="test_scan",
            name="测试扫描",
            path=test_dir
        )

        result = scanner.scan_single_target(target)

        # 分析扫描结果
        print_section("\n扫描结果分析:")

        l1_safe = []
        l2_review = []
        unmatched = []

        for file_info in result.files:
            match = engine.match_file(file_info)
            if match.matched:
                if match.risk_level == RiskLevel.L1_SAFE:
                    l1_safe.append(file_info)
                elif match.risk_level == RiskLevel.L2_REVIEW:
                    l2_review.append(file_info)
            else:
                unmatched.append(file_info)

        # 统计信息
        total_size = result.total_size
        l1_size = sum(f.size for f in l1_safe)
        l2_size = sum(f.size for f in l2_review)

        print(f"\n统计信息:")
        print(f"  总文件数: {result.file_count}")
        print(f"  总大小: {result.format_total_size()}")
        print(f"  L1_SAFE: {len(l1_safe)} 个文件 ({scanner._format_size(l1_size)})")
        print(f"  L2_REVIEW: {len(l2_review)} 个文件 ({scanner._format_size(l2_size)})")
        print(f"  UNMATCHED: {len(unmatched)} 个文件")

        # 详细列表
        if l1_safe:
            print(f"\n  [L1_SAFE - 可安全删除]")
            for f in l1_safe:
                match = engine.match_file(f)
                print(f"    - {f.path.name} ({f.format_size()}) - {match.rule.name}")

        if l2_review:
            print(f"\n  [L2_REVIEW - 需用户确认]")
            for f in l2_review:
                match = engine.match_file(f)
                print(f"    - {f.path.name} ({f.format_size()}) - {match.rule.name}")

        if unmatched:
            print(f"\n  [UNMATCHED - 无匹配规则]")
            for f in unmatched:
                print(f"    - {f.path.name} ({f.format_size()})")


def example_4_event_notification():
    """示例 4: 事件通知"""
    print_header("示例 4: 事件通知机制")

    # 创建事件总线
    event_bus = EventBus()

    # 创建事件计数器
    event_counts = {
        "SCAN_STARTED": 0,
        "SCAN_PROGRESS": 0,
        "SCAN_COMPLETED": 0
    }

    # 定义事件处理器
    def on_scan_started(event):
        event_counts["SCAN_STARTED"] += 1
        print(f"  [事件] 扫描开始 - 目标数: {event.data.get('target_count', 0)}")

    def on_scan_progress(event):
        event_counts["SCAN_PROGRESS"] += 1
        current = event.data.get('current', 0)
        total = event.data.get('total', 0)
        print(f"  [事件] 扫描进度: {current}/{total}")

    def on_scan_completed(event):
        event_counts["SCAN_COMPLETED"] += 1
        print(f"  [事件] 扫描完成 - 已扫描: {event.data.get('targets_scanned', 0)} 个目标")

    # 订阅事件
    event_bus.subscribe(EventType.SCAN_STARTED, on_scan_started)
    event_bus.subscribe(EventType.SCAN_PROGRESS, on_scan_progress)
    event_bus.subscribe(EventType.SCAN_COMPLETED, on_scan_completed)

    print_section("\n执行扫描（监听事件）:")

    # 创建扫描器并扫描
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.tmp").write_text("test")

        scanner = CoreScanner(event_bus=event_bus)

        target = ScanTarget(
            id="event_test",
            name="事件测试",
            path=test_dir
        )

        results = list(scanner.scan([target]))

    print_section("\n事件统计:")
    for event_name, count in event_counts.items():
        print(f"  {event_name}: {count} 次")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print(" " * 15 + "C-Wiper Usage Examples")
    print("=" * 60)

    # 运行所有示例
    example_1_basic_scan()
    example_2_rule_matching()
    example_3_combined_scan()
    example_4_event_notification()

    print("\n" + "=" * 60)
    print("[OK] All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
