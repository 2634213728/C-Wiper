"""
Integration Test - Complete Scan Workflow

本模块测试完整的扫描工作流程，包括启动扫描、进度跟踪、取消操作等。

测试场景：
1. 启动扫描
2. 扫描指定目录
3. 匹配规则
4. 生成结果
5. 取消操作

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
import time
from pathlib import Path

from src.controllers.scan_controller import ScanController
from src.models.scan_result import ScanTarget


@pytest.mark.integration
class TestScanWorkflow:
    """测试扫描工作流程"""

    def test_complete_scan_workflow(self, test_files_dir):
        """测试完整的扫描工作流程"""
        print("\n" + "=" * 70)
        print("Integration Test: Complete Scan Workflow")
        print("=" * 70)

        # 步骤 1: 创建扫描控制器
        print("\n[Step 1] Creating ScanController")
        controller = ScanController()
        print("  [OK] ScanController created")

        # 步骤 2: 定义扫描目标
        print("\n[Step 2] Defining scan target")
        target = ScanTarget(
            id="workflow_test",
            name="Workflow Test Target",
            path=test_files_dir,
            description="Integration test target"
        )
        print(f"  [OK] Target defined: {target.name}")
        print(f"       Path: {target.path}")

        # 步骤 3: 启动扫描
        print("\n[Step 3] Starting scan")
        start_time = time.time()
        scan_started = controller.start_scan([target])
        assert scan_started is True, "Scan should start successfully"
        print(f"  [OK] Scan started at {time.strftime('%H:%M:%S')}")

        # 步骤 4: 监控扫描进度
        print("\n[Step 4] Monitoring scan progress")
        while controller.state_manager.is_scanning:
            time.sleep(0.1)
            # 可以在这里添加进度检查
        scan_duration = time.time() - start_time
        print(f"  [OK] Scan completed in {scan_duration:.3f}s")

        # 步骤 5: 获取扫描结果
        print("\n[Step 5] Retrieving scan results")
        results = controller.get_results()
        assert len(results) > 0, "Should have scan results"
        print(f"  [OK] Retrieved {len(results)} result(s)")

        for result in results:
            print(f"\n  Result: {result.target.name}")
            print(f"    Files: {result.file_count}")
            print(f"    Size: {result.format_total_size()}")
            print(f"    Duration: {result.scan_duration:.3f}s")
            print(f"    Status: {'Success' if result.is_success() else 'Failed'}")

            if result.error_message:
                print(f"    Error: {result.error_message}")

        # 步骤 6: 获取扫描摘要
        print("\n[Step 6] Getting scan summary")
        summary = controller.get_scan_summary()
        print(f"  [OK] Scan summary:")
        print(f"    Total files: {summary['total_files']}")
        print(f"    Total size: {summary['formatted_size']}")
        print(f"    L1_SAFE: {summary['L1_SAFE']}")
        print(f"    L2_REVIEW: {summary['L2_REVIEW']}")

        # 步骤 7: 获取匹配的文件
        print("\n[Step 7] Getting matched files by risk level")

        l1_files = controller.get_matched_files("L1_SAFE")
        print(f"  [OK] L1_SAFE files: {len(l1_files)}")
        for f in l1_files[:5]:  # 显示前5个
            print(f"    - {f.path.name} ({f.size} bytes)")

        l2_files = controller.get_matched_files("L2_REVIEW")
        print(f"  [OK] L2_REVIEW files: {len(l2_files)}")
        for f in l2_files[:5]:  # 显示前5个
            print(f"    - {f.path.name} ({f.size} bytes)")

        # 验证结果
        assert summary['total_files'] > 0, "Should scan at least one file"
        assert result.is_success(), "Scan should be successful"

        print("\n" + "=" * 70)
        print("[OK] Complete scan workflow test passed!")
        print("=" * 70)

    def test_scan_with_cancellation(self, test_files_dir):
        """测试扫描取消工作流程"""
        print("\n" + "=" * 70)
        print("Integration Test: Scan Cancellation Workflow")
        print("=" * 70)

        # 创建大量文件以允许取消
        print("\n[Setup] Creating large test directory")
        for i in range(500):
            (test_files_dir / f"file_{i:04d}.tmp").write_text("x" * 1024)
        print(f"  [OK] Created 500 test files")

        # 启动扫描
        print("\n[Step 1] Starting scan")
        controller = ScanController()
        target = ScanTarget(
            id="cancel_test",
            name="Cancel Test",
            path=test_files_dir
        )

        controller.start_scan([target])
        print("  [OK] Scan started")

        # 等待一小段时间后取消
        print("\n[Step 2] Waiting 0.1s before cancellation")
        time.sleep(0.1)

        print("\n[Step 3] Cancelling scan")
        cancel_start = time.time()
        cancelled = controller.cancel_scan()
        cancel_time = time.time() - cancel_start

        assert cancelled is True, "Cancellation should succeed"
        print(f"  [OK] Scan cancelled in {cancel_time:.3f}s")

        # 等待取消完成
        print("\n[Step 4] Waiting for cancellation to complete")
        controller.wait_for_completion(timeout=5)
        print("  [OK] Cancellation completed")

        # 验证状态
        print("\n[Step 5] Verifying state")
        from src.controllers.state_manager import SystemState
        assert controller.state_manager.current_state == SystemState.IDLE
        print("  [OK] State returned to IDLE")

        print("\n" + "=" * 70)
        print("[OK] Scan cancellation workflow test passed!")
        print("=" * 70)

    def test_scan_multiple_targets(self, temp_dir):
        """测试扫描多个目标的工作流程"""
        print("\n" + "=" * 70)
        print("Integration Test: Multiple Targets Scan Workflow")
        print("=" * 70)

        # 创建多个测试目录
        print("\n[Setup] Creating multiple test directories")
        dir1 = temp_dir / "target1"
        dir2 = temp_dir / "target2"
        dir3 = temp_dir / "target3"

        for d in [dir1, dir2, dir3]:
            d.mkdir()

        # 在每个目录中创建文件
        (dir1 / "file1.tmp").write_text("content1")
        (dir1 / "file2.log").write_text("log1")

        (dir2 / "file3.tmp").write_text("content2")
        (dir2 / "file4.cache").write_text("cache")

        (dir3 / "file5.txt").write_text("document")
        (dir3 / "file6.tmp").write_text("content3")

        print("  [OK] Created 3 targets with files")

        # 定义多个目标
        print("\n[Step 1] Defining multiple targets")
        targets = [
            ScanTarget(id="target1", name="Target 1", path=dir1),
            ScanTarget(id="target2", name="Target 2", path=dir2),
            ScanTarget(id="target3", name="Target 3", path=dir3)
        ]
        print(f"  [OK] Defined {len(targets)} targets")

        # 启动扫描
        print("\n[Step 2] Starting scan of multiple targets")
        controller = ScanController()
        start_time = time.time()

        controller.start_scan(targets)
        print("  [OK] Scan started")

        # 等待完成
        print("\n[Step 3] Waiting for completion")
        controller.wait_for_completion(timeout=30)
        scan_duration = time.time() - start_time
        print(f"  [OK] All targets scanned in {scan_duration:.3f}s")

        # 获取结果
        print("\n[Step 4] Retrieving results for all targets")
        results = controller.get_results()
        assert len(results) == 3, "Should have 3 results"

        for i, result in enumerate(results, 1):
            print(f"\n  Target {i}: {result.target.name}")
            print(f"    Files: {result.file_count}")
            print(f"    Size: {result.format_total_size()}")
            assert result.is_success(), f"Target {i} should succeed"

        # 获取汇总
        print("\n[Step 5] Getting aggregate summary")
        summary = controller.get_scan_summary()
        print(f"  [OK] Total files across all targets: {summary['total_files']}")
        print(f"  [OK] Total size: {summary['formatted_size']}")

        print("\n" + "=" * 70)
        print("[OK] Multiple targets scan workflow test passed!")
        print("=" * 70)

    def test_scan_with_event_tracking(self, test_files_dir):
        """测试扫描事件跟踪工作流程"""
        print("\n" + "=" * 70)
        print("Integration Test: Scan Event Tracking Workflow")
        print("=" * 70)

        # 事件追踪器
        events_log = []

        def event_tracker(event):
            events_log.append({
                'type': event.type.value,
                'timestamp': time.time(),
                'data': event.data
            })

        # 订阅事件
        print("\n[Setup] Setting up event tracking")
        from src.utils.event_bus import EventBus, EventType
        event_bus = EventBus()

        event_types = [
            EventType.SCAN_STARTED,
            EventType.SCAN_PROGRESS,
            EventType.SCAN_COMPLETED,
            EventType.SCAN_FAILED
        ]

        for event_type in event_types:
            event_bus.subscribe(event_type, event_tracker)

        print(f"  [OK] Subscribed to {len(event_types)} event types")

        # 执行扫描
        print("\n[Step 1] Starting scan with event tracking")
        controller = ScanController(event_bus=event_bus)
        target = ScanTarget(
            id="event_test",
            name="Event Test",
            path=test_files_dir
        )

        start_time = time.time()
        controller.start_scan([target])
        controller.wait_for_completion(timeout=30)
        duration = time.time() - start_time

        print(f"  [OK] Scan completed in {duration:.3f}s")

        # 分析事件
        print("\n[Step 2] Analyzing captured events")
        print(f"  [OK] Total events captured: {len(events_log)}")

        for event in events_log:
            print(f"    - {event['type']} at {time.strftime('%H:%M:%S', time.localtime(event['timestamp']))}")

        # 验证关键事件存在
        print("\n[Step 3] Verifying critical events")
        event_types_received = [e['type'] for e in events_log]

        assert "SCAN_STARTED" in event_types_received, "Should receive SCAN_STARTED"
        print("  [OK] SCAN_STARTED event received")

        assert "SCAN_COMPLETED" in event_types_received, "Should receive SCAN_COMPLETED"
        print("  [OK] SCAN_COMPLETED event received")

        if "SCAN_PROGRESS" in event_types_received:
            print("  [OK] SCAN_PROGRESS events received")

        print("\n" + "=" * 70)
        print("[OK] Scan event tracking workflow test passed!")
        print("=" * 70)


@pytest.mark.integration
class TestScanEdgeCases:
    """测试扫描边界情况"""

    def test_scan_empty_directory(self, temp_dir):
        """测试扫描空目录"""
        print("\n" + "=" * 70)
        print("Integration Test: Empty Directory Scan")
        print("=" * 70)

        # 创建空目录
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        print(f"\n[Setup] Created empty directory: {empty_dir}")

        # 扫描
        controller = ScanController()
        target = ScanTarget(id="empty", name="Empty", path=empty_dir)

        controller.start_scan([target])
        controller.wait_for_completion(timeout=10)

        results = controller.get_results()
        assert len(results) == 1
        assert results[0].file_count == 0
        print("  [OK] Empty directory scanned correctly")

        print("=" * 70)
        print("[OK] Empty directory scan test passed!")
        print("=" * 70)

    def test_scan_single_file(self, temp_dir):
        """测试扫描单个文件"""
        print("\n" + "=" * 70)
        print("Integration Test: Single File Scan")
        print("=" * 70)

        # 创建单个文件
        test_file = temp_dir / "single.txt"
        test_file.write_text("single file content")

        print(f"\n[Setup] Created single file: {test_file}")

        # 扫描
        controller = ScanController()
        target = ScanTarget(id="single", name="Single File", path=test_file)

        controller.start_scan([target])
        controller.wait_for_completion(timeout=10)

        results = controller.get_results()
        assert len(results) == 1
        assert results[0].file_count == 1
        print("  [OK] Single file scanned correctly")

        print("=" * 70)
        print("[OK] Single file scan test passed!")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
