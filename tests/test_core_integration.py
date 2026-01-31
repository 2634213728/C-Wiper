"""
Integration Test - Core Scanner and Rule Engine

This test verifies the integration between CoreScanner and RuleEngine modules.

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import logging
import sys
import tempfile
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.scanner import CoreScanner
from src.core.rule_engine import RuleEngine, RiskLevel
from src.models.scan_result import ScanTarget
from src.controllers.state_manager import StateManager
from src.utils.event_bus import EventBus, EventType


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_scanner_rule_integration():
    """
    集成测试：扫描器和规则引擎协作

    测试场景：
    1. 创建测试目录结构（包含临时文件、日志文件等）
    2. 使用 CoreScanner 扫描目录
    3. 使用 RuleEngine 匹配文件到规则
    4. 验证风险等级分类
    """
    print("=" * 60)
    print("Integration Test: CoreScanner + RuleEngine")
    print("=" * 60)

    # 创建测试环境
    print("\n[Setup] Creating test environment")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建不同类型的测试文件
        test_files = {
            "temp1.tmp": "Temporary file 1",
            "temp2.temp": "Temporary file 2",
            "app.log": "Application log",
            "cache.cache": "Cache file",
            "document.txt": "Normal document",
            "backup.bak": "Backup file"
        }

        for filename, content in test_files.items():
            (test_dir / filename).write_text(content)

        print(f"  [OK] Created {len(test_files)} test files in {test_dir}")

        # 测试 1: 扫描目录
        print("\n[Test 1] Scanning directory with CoreScanner")
        scanner = CoreScanner()

        target = ScanTarget(
            id="test_integration",
            name="Integration Test Target",
            path=test_dir,
            description="Test directory for integration testing"
        )

        result = scanner.scan_single_target(target)
        print(f"  [OK] Scanned {result.file_count} files")
        print(f"  [OK] Total size: {result.format_total_size()}")

        assert result.file_count == len(test_files), f"Expected {len(test_files)} files, got {result.file_count}"
        assert result.is_success(), "Scan should be successful"

        # 测试 2: 加载规则
        print("\n[Test 2] Loading rules with RuleEngine")
        rule_engine = RuleEngine()
        rule_engine.load_rules()

        rules = rule_engine.get_enabled_rules()
        print(f"  [OK] Loaded {len(rules)} enabled rules")

        # 测试 3: 匹配文件到规则
        print("\n[Test 3] Matching files to rules")
        l1_safe_count = 0
        l2_review_count = 0
        unmatched_count = 0

        for file_info in result.files:
            match = rule_engine.match_file(file_info)

            if match.matched:
                risk = match.risk_level
                if risk == RiskLevel.L1_SAFE:
                    l1_safe_count += 1
                    print(f"  [L1_SAFE] {file_info.path.name} - {match.rule.name}")
                elif risk == RiskLevel.L2_REVIEW:
                    l2_review_count += 1
                    print(f"  [L2_REVIEW] {file_info.path.name} - {match.rule.name}")
            else:
                unmatched_count += 1
                print(f"  [UNMATCHED] {file_info.path.name}")

        print(f"\n  Summary:")
        print(f"    L1_SAFE: {l1_safe_count} files")
        print(f"    L2_REVIEW: {l2_review_count} files")
        print(f"    UNMATCHED: {unmatched_count} files")

        # 测试 4: 验证风险分类
        print("\n[Test 4] Validating risk classification")
        assert l1_safe_count > 0, "Should have at least one L1_SAFE file"
        assert l2_review_count > 0, "Should have at least one L2_REVIEW file"
        print("  [OK] Risk classification works correctly")

        # 测试 5: 生成清理报告
        print("\n[Test 5] Generating cleanup report")
        total_size = result.total_size
        safe_size = sum(
            f.size for f in result.files
            if rule_engine.match_file(f).risk_level == RiskLevel.L1_SAFE
        )

        print(f"  Total size: {result.format_total_size()}")
        print(f"  L1_SAFE size: {scanner._format_size(safe_size)} ({safe_size/total_size*100:.1f}%)")
        print("  [OK] Report generated successfully")

    print("\n" + "=" * 60)
    print("[OK] All integration tests passed!")
    print("=" * 60)


def test_event_integration():
    """
    事件集成测试

    测试扫描过程中的事件通知机制。
    """
    print("\n" + "=" * 60)
    print("Integration Test: Event Notifications")
    print("=" * 60)

    # 创建事件追踪器
    events_received = []

    def scan_started_handler(event):
        events_received.append("SCAN_STARTED")
        print(f"  [EVENT] Scan started: {event.data}")

    def progress_handler(event):
        events_received.append("SCAN_PROGRESS")
        print(f"  [EVENT] Progress: {event.data['current']}/{event.data['total']}")

    def completed_handler(event):
        events_received.append("SCAN_COMPLETED")
        print(f"  [EVENT] Scan completed: {event.data}")

    # 订阅事件
    event_bus = EventBus()
    event_bus.subscribe(EventType.SCAN_STARTED, scan_started_handler)
    event_bus.subscribe(EventType.SCAN_PROGRESS, progress_handler)
    event_bus.subscribe(EventType.SCAN_COMPLETED, completed_handler)

    # 执行扫描
    print("\n[Setup] Creating test environment")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.tmp").write_text("test")

        print("\n[Test] Scanning with event notifications")
        scanner = CoreScanner(event_bus=event_bus)

        target = ScanTarget(id="event_test", name="Event Test", path=test_dir)
        targets = [target]

        results = list(scanner.scan(targets))

        print(f"\n[Result] Received {len(events_received)} events")
        assert "SCAN_STARTED" in events_received, "Should receive SCAN_STARTED event"
        assert "SCAN_PROGRESS" in events_received, "Should receive SCAN_PROGRESS event"
        assert "SCAN_COMPLETED" in events_received, "Should receive SCAN_COMPLETED event"

        print("  [OK] All expected events received")

    print("\n" + "=" * 60)
    print("[OK] Event integration test passed!")
    print("=" * 60)


def test_cancellation_integration():
    """
    取消操作集成测试

    测试扫描取消功能。
    """
    print("\n" + "=" * 60)
    print("Integration Test: Scan Cancellation")
    print("=" * 60)

    # 创建大量文件的测试目录
    print("\n[Setup] Creating test directory with many files")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建子目录和文件
        for i in range(100):
            (test_dir / f"file{i}.tmp").write_text(f"content {i}")

        print(f"  [OK] Created 100 test files")

        # 测试取消
        print("\n[Test] Testing scan cancellation")
        scanner = CoreScanner()
        target = ScanTarget(id="cancel_test", name="Cancel Test", path=test_dir)

        # 在后台线程中扫描
        import threading
        results = []

        def scan_worker():
            for result in scanner.scan([target]):
                results.append(result)

        thread = threading.Thread(target=scan_worker)
        thread.start()

        # 等待一小段时间后取消
        time.sleep(0.1)
        scanner.cancel()

        thread.join(timeout=2)

        print(f"  [OK] Scan cancelled after {len(results)} results")
        assert len(results) <= 1, "Should be cancelled before completion"

    print("\n" + "=" * 60)
    print("[OK] Cancellation integration test passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_scanner_rule_integration()
    test_event_integration()
    test_cancellation_integration()

    print("\n" + "=" * 60)
    print("[SUCCESS] All integration tests passed!")
    print("=" * 60)
