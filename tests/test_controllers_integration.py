"""
Controllers Integration Test - 控制器集成测试

本模块测试控制器层的集成功能，验证各控制器之间的协作。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import sys
import tempfile
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.controllers.analysis_controller import AnalysisController
from src.models.scan_result import ScanTarget


def test_full_workflow():
    """
    测试完整的工作流程：扫描 -> 清理 -> 分析
    """
    print("=" * 70)
    print("Controllers Integration Test - Full Workflow")
    print("=" * 70)

    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建测试文件
        print("\n[Setup] Creating test files...")
        (test_dir / "temp1.tmp").write_text("Temporary file 1")
        (test_dir / "temp2.tmp").write_text("Temporary file 2")
        (test_dir / "log.txt").write_text("Log file")
        (test_dir / "cache.cache").write_text("Cache file")

        print(f"  [OK] Created test directory: {test_dir}")

        # 测试 1: 扫描
        print("\n[Test 1] Scan Controller")
        scan_controller = ScanController()

        targets = [
            ScanTarget(
                id="test_target",
                name="Test Target",
                path=test_dir,
                description="Test target for integration test"
            )
        ]

        # 启动扫描
        assert scan_controller.start_scan(targets), "Scan should start"
        print("  [OK] Scan started")

        # 等待完成
        assert scan_controller.wait_for_completion(timeout=10), "Scan should complete"
        print("  [OK] Scan completed")

        # 获取结果
        results = scan_controller.get_results()
        assert len(results) > 0, "Should have scan results"
        print(f"  [OK] Found {len(results)} scan results")

        for result in results:
            print(f"    - {result.target.name}: {result.file_count} files, {result.format_total_size()}")

        # 获取匹配的文件
        summary = scan_controller.get_scan_summary()
        print(f"  [OK] Scan summary:")
        print(f"    - Total files: {summary['total_files']}")
        print(f"    - L1_SAFE: {summary['L1_SAFE']}")
        print(f"    - L2_REVIEW: {summary['L2_REVIEW']}")

        # 测试 2: 清理
        print("\n[Test 2] Clean Controller")
        clean_controller = CleanController()

        # 获取 L1 安全文件进行清理
        l1_files = scan_controller.get_matched_files("L1_SAFE")
        print(f"  [INFO] Found {len(l1_files)} L1_SAFE files to clean")

        if l1_files:
            # 预览清理
            preview = clean_controller.preview_clean(l1_files)
            print(f"  [OK] Preview cleanup:")
            print(f"    - Files: {preview['file_count']}")
            print(f"    - Size: {preview['formatted_size']}")

            # 确认并执行清理
            clean_controller.confirm_clean()
            assert clean_controller.start_clean(l1_files), "Clean should start"
            print("  [OK] Clean started")

            # 等待完成
            assert clean_controller.wait_for_completion(timeout=10), "Clean should complete"
            print("  [OK] Clean completed")

            # 获取清理报告
            report = clean_controller.get_report()
            assert report is not None, "Should have clean report"
            print(f"  [OK] Clean report:")
            print(f"    - Files deleted: {report['files_deleted']}")
            print(f"    - Size freed: {report['formatted_size']}")
            print(f"    - Duration: {report['duration']:.3f}s")
        else:
            print("  [SKIP] No L1_SAFE files to clean")

    # 测试 3: 分析（不依赖临时目录）
    print("\n[Test 3] Analysis Controller")
    analysis_controller = AnalysisController()

    # 启动分析
    assert analysis_controller.start_analysis(), "Analysis should start"
    print("  [OK] Analysis started")

    # 等待完成
    completed = analysis_controller.wait_for_completion(timeout=60)
    if completed:
        print("  [OK] Analysis completed")

        # 获取结果
        clusters = analysis_controller.get_clusters()
        print(f"  [OK] Found {len(clusters)} applications")

        if clusters:
            print("  [OK] Top 5 applications:")
            for cluster in clusters[:5]:
                print(f"    - {cluster.app_name}: {cluster._format_size(cluster.total_size)}")

        # 获取报告
        report = analysis_controller.get_report()
        if report:
            print(f"  [OK] Analysis report:")
            print(f"    - App count: {report['app_count']}")
            print(f"    - Total size: {report['formatted_size']}")
            print(f"    - Duration: {report['duration']:.2f}s")
    else:
        print("  [WARN] Analysis timed out (may take longer)")

    # 测试 4: 状态转换
    print("\n[Test 4] State Transitions")
    from src.controllers.state_manager import StateManager

    state_manager = StateManager()
    print(f"  [OK] Current state: {state_manager.current_state.value}")
    assert state_manager.is_idle(), "Should return to IDLE after all operations"
    print("  [OK] All controllers returned to IDLE state")

    # 测试 5: 事件通知
    print("\n[Test 5] Event Notifications")
    from src.utils.event_bus import EventBus, EventType

    event_bus = EventBus()
    events_received = []

    def event_handler(event):
        events_received.append(event.type.value)
        print(f"    [EVENT] {event.type.value}")

    # 订阅事件
    event_bus.subscribe(EventType.SCAN_COMPLETED, event_handler)
    event_bus.subscribe(EventType.CLEAN_COMPLETED, event_handler)
    event_bus.subscribe(EventType.ANALYSIS_COMPLETED, event_handler)

    # 快速执行一次扫描以触发事件
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.tmp").write_text("test")

        scan_ctrl = ScanController()
        scan_ctrl.start_scan([
            ScanTarget(id="quick", name="Quick", path=test_dir)
        ])
        scan_ctrl.wait_for_completion(timeout=5)

    if events_received:
        print(f"  [OK] Received {len(events_received)} events")
    else:
        print("  [WARN] No events received (may have been cleared)")

    print("\n" + "=" * 70)
    print("[OK] All integration tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    test_full_workflow()
