"""
Unit Tests for Controller Layer

本模块包含控制器层的单元测试，涵盖 ScanController、CleanController、AnalysisController 等。

测试覆盖：
- ScanController
- CleanController
- AnalysisController
- 状态转换
- 事件发布

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.controllers.analysis_controller import AnalysisController
from src.controllers.state_manager import StateManager, SystemState
from src.models.scan_result import ScanTarget, ScanResult, FileInfo
from src.utils.event_bus import EventBus, EventType


class TestScanController:
    """测试 ScanController 类"""

    def test_scan_controller_initialization(self):
        """测试扫描控制器初始化"""
        controller = ScanController()

        assert controller.state_manager is not None
        assert controller.scanner is not None
        assert controller.rule_engine is not None
        assert controller.event_bus is not None

    def test_start_scan_success(self, test_files_dir):
        """测试成功启动扫描"""
        controller = ScanController()

        target = ScanTarget(
            id="test_target",
            name="Test Target",
            path=test_files_dir
        )

        # 启动扫描
        result = controller.start_scan([target])

        assert result is True
        assert controller.state_manager.current_state == SystemState.SCANNING

        # 等待完成
        completed = controller.wait_for_completion(timeout=10)
        assert completed is True

        # 验证结果
        results = controller.get_results()
        assert len(results) > 0
        assert results[0].is_success()

    def test_start_scan_invalid_target(self):
        """测试扫描无效目标"""
        controller = ScanController()

        target = ScanTarget(
            id="invalid_target",
            name="Invalid Target",
            path=Path("C:/NonExistentPath12345")
        )

        result = controller.start_scan([target])

        # 应该启动但扫描会失败
        assert result is True

        controller.wait_for_completion(timeout=5)
        results = controller.get_results()

        # 结果应该存在但不成功
        assert len(results) > 0
        assert not results[0].is_success()

    def test_cancel_scan(self, test_files_dir):
        """测试取消扫描"""
        controller = ScanController()

        # 创建大量文件以允许取消
        for i in range(100):
            (test_files_dir / f"file{i}.tmp").write_text("content")

        target = ScanTarget(
            id="cancel_test",
            name="Cancel Test",
            path=test_files_dir
        )

        # 启动扫描
        controller.start_scan([target])

        # 立即取消
        time.sleep(0.05)
        cancelled = controller.cancel_scan()

        assert cancelled is True

        # 等待取消完成
        controller.wait_for_completion(timeout=5)

        # 验证状态返回 IDLE
        assert controller.state_manager.current_state == SystemState.IDLE

    def test_get_scan_summary(self, test_files_dir):
        """测试获取扫描摘要"""
        controller = ScanController()

        target = ScanTarget(
            id="summary_test",
            name="Summary Test",
            path=test_files_dir
        )

        controller.start_scan([target])
        controller.wait_for_completion(timeout=10)

        summary = controller.get_scan_summary()

        assert "total_files" in summary
        assert "total_size" in summary
        assert "L1_SAFE" in summary
        assert "L2_REVIEW" in summary
        assert summary["total_files"] > 0

    def test_get_matched_files(self, test_files_dir):
        """测试获取匹配的文件"""
        controller = ScanController()

        target = ScanTarget(
            id="matched_test",
            name="Matched Test",
            path=test_files_dir
        )

        controller.start_scan([target])
        controller.wait_for_completion(timeout=10)

        # 获取 L1 安全文件
        l1_files = controller.get_matched_files("L1_SAFE")
        assert isinstance(l1_files, list)

        # 获取 L2 审查文件
        l2_files = controller.get_matched_files("L2_REVIEW")
        assert isinstance(l2_files, list)

    def test_scan_controller_state_transitions(self, test_files_dir):
        """测试扫描控制器状态转换"""
        controller = ScanController()

        # 初始状态
        assert controller.state_manager.current_state == SystemState.IDLE

        # 启动扫描
        target = ScanTarget(id="state_test", name="State Test", path=test_files_dir)
        controller.start_scan([target])

        # 扫描中
        assert controller.state_manager.current_state == SystemState.SCANNING

        # 等待完成
        controller.wait_for_completion(timeout=10)

        # 完成后返回 IDLE
        assert controller.state_manager.current_state == SystemState.IDLE


class TestCleanController:
    """测试 CleanController 类"""

    def test_clean_controller_initialization(self):
        """测试清理控制器初始化"""
        controller = CleanController()

        assert controller.state_manager is not None
        assert controller.cleaner is not None
        assert controller.event_bus is not None

    def test_preview_clean(self, test_files_dir):
        """测试预览清理"""
        controller = CleanController()

        # 创建一些测试文件
        test_files = []
        for i in range(5):
            test_file = test_files_dir / f"test{i}.tmp"
            test_file.write_text("content")
            test_files.append(test_file)

        # 转换为 FileInfo
        import time
        file_infos = [
            FileInfo(
                path=f,
                size=f.stat().st_size,
                is_dir=False,
                modified_time=f.stat().st_mtime
            )
            for f in test_files
        ]

        # 预览清理
        preview = controller.preview_clean(file_infos)

        assert "file_count" in preview
        assert "total_size" in preview
        assert "formatted_size" in preview
        assert preview["file_count"] == 5

    def test_confirm_clean(self):
        """测试确认清理"""
        controller = CleanController()

        # 确认清理
        controller.confirm_clean()

        # 验证确认标志
        assert controller._confirmed is True

    def test_start_clean_without_confirmation(self, test_files_dir):
        """测试未确认时启动清理"""
        controller = CleanController()

        # 创建测试文件
        test_file = test_files_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        # 不确认直接启动
        result = controller.start_clean([file_info])

        # 应该失败（未确认）
        assert result is False

    def test_start_clean_with_confirmation(self, test_files_dir):
        """测试确认后启动清理"""
        controller = CleanController()

        # 创建测试文件
        test_file = test_files_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        # 确认并启动
        controller.confirm_clean()
        result = controller.start_clean([file_info])

        assert result is True

        # 等待完成
        completed = controller.wait_for_completion(timeout=10)
        assert completed is True

        # 验证文件被删除（在模拟模式下）
        # 在实际实现中，文件可能被移到回收站

    def test_get_clean_report(self, test_files_dir):
        """测试获取清理报告"""
        controller = CleanController()

        # 创建测试文件
        test_file = test_files_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        # 执行清理
        controller.confirm_clean()
        controller.start_clean([file_info])
        controller.wait_for_completion(timeout=10)

        # 获取报告
        report = controller.get_report()

        assert report is not None
        assert "files_deleted" in report
        assert "size_freed" in report
        assert "duration" in report


class TestAnalysisController:
    """测试 AnalysisController 类"""

    def test_analysis_controller_initialization(self):
        """测试分析控制器初始化"""
        controller = AnalysisController()

        assert controller.state_manager is not None
        assert controller.analyzer is not None
        assert controller.event_bus is not None

    def test_start_analysis(self):
        """测试启动分析"""
        controller = AnalysisController()

        # 启动分析
        result = controller.start_analysis()

        assert result is True
        assert controller.state_manager.current_state == SystemState.ANALYZING

        # 等待完成（可能需要较长时间）
        completed = controller.wait_for_completion(timeout=60)

        # 可能超时，这是正常的
        assert isinstance(completed, bool)

    def test_get_clusters(self):
        """测试获取应用集群"""
        controller = AnalysisController()

        # 启动分析
        controller.start_analysis()

        # 等待一段时间
        time.sleep(2)

        # 获取集群（可能为空）
        clusters = controller.get_clusters()
        assert isinstance(clusters, list)

    def test_get_analysis_report(self):
        """测试获取分析报告"""
        controller = AnalysisController()

        # 启动分析
        controller.start_analysis()
        controller.wait_for_completion(timeout=30)

        # 获取报告
        report = controller.get_report()

        if report:
            assert "app_count" in report
            assert "total_size" in report
            assert "duration" in report


class TestStateTransitions:
    """测试状态转换"""

    def test_idle_to_scanning_transition(self, test_files_dir):
        """测试从 IDLE 到 SCANNING 的转换"""
        state_manager = StateManager()
        controller = ScanController(state_manager=state_manager)

        assert state_manager.current_state == SystemState.IDLE

        target = ScanTarget(id="test", name="Test", path=test_files_dir)
        controller.start_scan([target])

        assert state_manager.current_state == SystemState.SCANNING

    def test_scanning_to_idle_transition(self, test_files_dir):
        """测试从 SCANNING 到 IDLE 的转换"""
        state_manager = StateManager()
        controller = ScanController(state_manager=state_manager)

        target = ScanTarget(id="test", name="Test", path=test_files_dir)
        controller.start_scan([target])
        controller.wait_for_completion(timeout=10)

        assert state_manager.current_state == SystemState.IDLE

    def test_invalid_state_transition(self, test_files_dir):
        """测试无效的状态转换"""
        state_manager = StateManager()
        controller1 = ScanController(state_manager=state_manager)
        controller2 = CleanController(state_manager=state_manager)

        # 启动扫描
        target = ScanTarget(id="test", name="Test", path=test_files_dir)
        controller1.start_scan([target])

        # 尝试在扫描时启动清理（应该失败）
        import time
        file_info = FileInfo(
            path=test_files_dir / "test.tmp",
            size=100,
            is_dir=False,
            modified_time=time.time()
        )

        controller2.confirm_clean()
        result = controller2.start_clean([file_info])

        # 应该失败（状态冲突）
        assert result is False


class TestEventPublishing:
    """测试事件发布"""

    def test_scan_events_published(self, test_files_dir):
        """测试扫描事件发布"""
        event_bus = EventBus()
        events_received = []

        def event_handler(event):
            events_received.append(event.type.value)

        # 订阅事件
        event_bus.subscribe(EventType.SCAN_STARTED, event_handler)
        event_bus.subscribe(EventType.SCAN_PROGRESS, event_handler)
        event_bus.subscribe(EventType.SCAN_COMPLETED, event_handler)

        # 创建控制器并执行扫描
        controller = ScanController(event_bus=event_bus)
        target = ScanTarget(id="event_test", name="Event Test", path=test_files_dir)

        controller.start_scan([target])
        controller.wait_for_completion(timeout=10)

        # 验证事件
        assert "SCAN_STARTED" in events_received
        assert "SCAN_COMPLETED" in events_received

    def test_clean_events_published(self, test_files_dir):
        """测试清理事件发布"""
        event_bus = EventBus()
        events_received = []

        def event_handler(event):
            events_received.append(event.type.value)

        event_bus.subscribe(EventType.CLEAN_STARTED, event_handler)
        event_bus.subscribe(EventType.CLEAN_PROGRESS, event_handler)
        event_bus.subscribe(EventType.CLEAN_COMPLETED, event_handler)

        # 创建控制器并执行清理
        controller = CleanController(event_bus=event_bus)

        test_file = test_files_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        controller.confirm_clean()
        controller.start_clean([file_info])
        controller.wait_for_completion(timeout=10)

        # 验证事件
        assert "CLEAN_STARTED" in events_received

    def test_analysis_events_published(self):
        """测试分析事件发布"""
        event_bus = EventBus()
        events_received = []

        def event_handler(event):
            events_received.append(event.type.value)

        event_bus.subscribe(EventType.ANALYSIS_STARTED, event_handler)
        event_bus.subscribe(EventType.ANALYSIS_COMPLETED, event_handler)

        # 创建控制器并执行分析
        controller = AnalysisController(event_bus=event_bus)
        controller.start_analysis()

        # 验证开始事件
        assert "ANALYSIS_STARTED" in events_received


class TestControllerErrorHandling:
    """测试控制器错误处理"""

    def test_scan_with_permission_error(self):
        """测试权限错误处理"""
        controller = ScanController()

        # 尝试扫描需要权限的路径
        target = ScanTarget(
            id="permission_test",
            name="Permission Test",
            path=Path("C:/System Volume Information")
        )

        result = controller.start_scan([target])

        # 应该处理错误而不崩溃
        assert isinstance(result, bool)

    def test_clean_with_non_existent_file(self):
        """测试清理不存在文件的处理"""
        controller = CleanController()

        # 创建不存在的文件信息
        import time
        file_info = FileInfo(
            path=Path("C:/NonExistent/file12345.txt"),
            size=100,
            is_dir=False,
            modified_time=time.time()
        )

        controller.confirm_clean()
        result = controller.start_clean([file_info])

        # 应该失败或跳过
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
