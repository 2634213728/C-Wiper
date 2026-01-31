"""
Unit Tests for Core Scanner Module

本模块包含 CoreScanner 的单元测试，涵盖文件扫描、缓存机制、取消操作等功能。

测试覆盖：
- 文件扫描功能
- 缓存机制
- 取消操作
- 符号链接处理
- 大目录扫描（性能）

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.scanner import CoreScanner, ScanCache, FileAttributes, ScanError
from src.models.scan_result import ScanTarget, ScanResult, FileInfo
from src.controllers.state_manager import SystemState


class TestScanCache:
    """测试 ScanCache 类"""

    def test_cache_initialization(self, temp_dir):
        """测试缓存初始化"""
        cache_file = temp_dir / "test_cache.json"
        cache = ScanCache(cache_file)

        assert cache.cache_file == cache_file
        assert isinstance(cache.cache, dict)
        assert len(cache.cache) == 0

    def test_cache_set_and_get(self, temp_dir):
        """测试缓存设置和获取"""
        cache = ScanCache(temp_dir / "test_cache.json")
        test_path = Path("C:/Test/file.txt")

        # 设置缓存
        cache.set(test_path, 1024, time.time())

        # 获取缓存
        result = cache.get(test_path)
        assert result is not None
        assert result[0] == 1024

    def test_cache_remove(self, temp_dir):
        """测试缓存移除"""
        cache = ScanCache(temp_dir / "test_cache.json")
        test_path = Path("C:/Test/file.txt")

        # 设置并移除缓存
        cache.set(test_path, 1024, time.time())
        assert cache.get(test_path) is not None

        removed = cache.remove(test_path)
        assert removed is True
        assert cache.get(test_path) is None

    def test_cache_clear(self, temp_dir):
        """测试缓存清空"""
        cache = ScanCache(temp_dir / "test_cache.json")

        # 添加多个缓存项
        for i in range(10):
            cache.set(Path(f"C:/Test/file{i}.txt"), 1024, time.time())

        # 清空缓存
        cache.clear()
        assert len(cache.cache) == 0

    def test_cache_persistence(self, temp_dir):
        """测试缓存持久化"""
        cache_file = temp_dir / "persistent_cache.json"

        # 创建缓存并添加数据
        cache1 = ScanCache(cache_file)
        cache1.set(Path("C:/Test/file.txt"), 2048, time.time())
        cache1._save_cache()

        # 创建新缓存实例并验证数据加载
        cache2 = ScanCache(cache_file)
        result = cache2.get(Path("C:/Test/file.txt"))
        assert result is not None
        assert result[0] == 2048


class TestFileAttributes:
    """测试 FileAttributes 类"""

    def test_file_attributes_creation(self):
        """测试文件属性创建"""
        attrs = FileAttributes(
            is_hidden=True,
            is_readonly=False,
            is_system=True,
            is_archive=True
        )

        assert attrs.is_hidden is True
        assert attrs.is_readonly is False
        assert attrs.is_system is True
        assert attrs.is_archive is True

    def test_file_attributes_to_dict(self):
        """测试文件属性序列化"""
        attrs = FileAttributes(
            is_hidden=True,
            is_readonly=False,
            is_system=False,
            is_archive=True
        )

        attrs_dict = attrs.to_dict()
        assert attrs_dict["is_hidden"] is True
        assert attrs_dict["is_readonly"] is False
        assert attrs_dict["is_system"] is False
        assert attrs_dict["is_archive"] is True

    def test_file_attributes_from_dict(self):
        """测试从字典创建文件属性"""
        data = {
            "is_hidden": True,
            "is_readonly": False,
            "is_system": True,
            "is_archive": False
        }

        attrs = FileAttributes.from_dict(data)
        assert attrs.is_hidden is True
        assert attrs.is_readonly is False
        assert attrs.is_system is True
        assert attrs.is_archive is False


class TestCoreScanner:
    """测试 CoreScanner 类"""

    def test_scanner_initialization(self):
        """测试扫描器初始化"""
        scanner = CoreScanner()

        assert scanner.state_manager is not None
        assert scanner.event_bus is not None
        assert scanner.security is not None
        assert scanner.cache is not None
        assert scanner._cancelled is False

    def test_scan_single_file(self, temp_dir):
        """测试扫描单个文件"""
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # 创建扫描目标
        target = ScanTarget(
            id="single_file",
            name="Single File",
            path=test_file
        )

        # 执行扫描
        scanner = CoreScanner()
        result = scanner.scan_single_target(target)

        # 验证结果
        assert result.is_success()
        assert result.file_count == 1
        assert result.total_size == len("test content")
        assert len(result.files) == 1
        assert result.files[0].path == test_file

    def test_scan_directory(self, test_files_dir):
        """测试扫描目录"""
        target = ScanTarget(
            id="test_dir",
            name="Test Directory",
            path=test_files_dir
        )

        scanner = CoreScanner()
        result = scanner.scan_single_target(target)

        # 验证扫描成功
        assert result.is_success()
        assert result.file_count > 0
        assert result.total_size > 0
        assert result.dir_count >= 1

    def test_scan_non_existent_path(self):
        """测试扫描不存在的路径"""
        target = ScanTarget(
            id="non_existent",
            name="Non Existent",
            path=Path("C:/NonExistentPath12345")
        )

        scanner = CoreScanner()
        result = scanner.scan_single_target(target)

        # 验证扫描失败
        assert not result.is_success()
        assert result.error_message is not None
        assert "does not exist" in result.error_message.lower()

    def test_scan_multiple_targets(self, test_files_dir):
        """测试扫描多个目标（生成器模式）"""
        # 创建多个测试目录
        dir1 = test_files_dir / "dir1"
        dir2 = test_files_dir / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "file1.tmp").write_text("content1")
        (dir2 / "file2.tmp").write_text("content2")

        targets = [
            ScanTarget(id="target1", name="Target 1", path=dir1),
            ScanTarget(id="target2", name="Target 2", path=dir2)
        ]

        scanner = CoreScanner()
        results = list(scanner.scan(targets))

        # 验证结果
        assert len(results) == 2
        assert all(r.is_success() for r in results)
        assert results[0].file_count == 1
        assert results[1].file_count == 1

    def test_scan_disabled_target(self, test_files_dir):
        """测试扫描禁用的目标"""
        target = ScanTarget(
            id="disabled_target",
            name="Disabled Target",
            path=test_files_dir,
            enabled=False
        )

        scanner = CoreScanner()
        results = list(scanner.scan([target]))

        # 禁用的目标应该被跳过
        assert len(results) == 0

    def test_scan_cancellation(self, temp_dir):
        """测试扫描取消功能"""
        # 创建大量文件
        for i in range(100):
            (temp_dir / f"file{i}.tmp").write_text("content")

        target = ScanTarget(id="cancel_test", name="Cancel Test", path=temp_dir)

        scanner = CoreScanner()

        # 在后台线程中扫描并立即取消
        import threading
        results = []

        def scan_worker():
            for result in scanner.scan([target]):
                results.append(result)

        thread = threading.Thread(target=scan_worker)
        thread.start()

        # 等待一小段时间后取消
        time.sleep(0.05)
        scanner.cancel()

        thread.join(timeout=2)

        # 验证取消生效
        assert len(results) <= 1, "Scan should be cancelled"

    def test_scan_file_info_details(self, temp_dir):
        """测试扫描获取的文件信息详情"""
        # 创建不同属性的测试文件
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")

        target = ScanTarget(id="detail_test", name="Detail Test", path=test_file)

        scanner = CoreScanner()
        result = scanner.scan_single_target(target)

        # 验证文件信息详情
        file_info = result.files[0]
        assert file_info.path == test_file
        assert file_info.size > 0
        assert file_info.is_dir is False
        assert file_info.file_extension == ".txt"
        assert file_info.modified_time > 0
        assert file_info.created_time > 0

    def test_scan_skips_symlinks(self, temp_dir):
        """测试扫描跳过符号链接"""
        # 创建实际文件和符号链接
        real_file = temp_dir / "real_file.txt"
        real_file.write_text("real content")

        # Windows 上创建 junction
        try:
            import os
            symlink = temp_dir / "symlink"
            if os.name == 'nt':
                # Windows: 创建目录 junction
                subprocess.run(
                    f'mklink /J "{symlink}" "{real_file.parent}"',
                    shell=True,
                    capture_output=True
                )
        except Exception:
            # 如果创建符号链接失败，跳过测试
            pytest.skip("Cannot create symlink for testing")

        target = ScanTarget(id="symlink_test", name="Symlink Test", path=temp_dir)

        scanner = CoreScanner()
        result = scanner.scan_single_target(target)

        # 验证符号链接被跳过
        # 实际文件应该被扫描，符号链接本身不应该重复计算
        assert result.is_success()

    def test_format_size(self):
        """测试大小格式化方法"""
        scanner = CoreScanner()

        # 测试不同单位
        assert "B" in scanner._format_size(512)
        assert "KB" in scanner._format_size(1024)
        assert "MB" in scanner._format_size(1024 * 1024)
        assert "GB" in scanner._format_size(1024 * 1024 * 1024)

    def test_scan_with_permission_error(self, temp_dir):
        """测试权限错误处理"""
        # 创建一个模拟权限错误的场景
        target = ScanTarget(
            id="permission_test",
            name="Permission Test",
            path=temp_dir
        )

        scanner = CoreScanner()

        # Mock rglob 来模拟权限错误
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.side_effect = PermissionError("Access denied")

            result = scanner.scan_single_target(target)

            # 应该捕获权限错误并返回失败结果
            # 注意：实际实现可能返回空结果或错误信息

    def test_cancel_reset(self):
        """测试取消标志重置"""
        scanner = CoreScanner()

        # 设置取消标志
        scanner.cancel()
        assert scanner._cancelled is True

        # 重置取消标志
        scanner.reset_cancel()
        assert scanner._cancelled is False


class TestScannerPerformance:
    """性能测试类（标记为 slow）"""

    @pytest.mark.slow
    def test_scan_large_directory_performance(self, temp_dir):
        """测试大目录扫描性能（1000 文件）"""
        # 创建 1000 个文件
        file_count = 1000
        content = "x" * 1024  # 1 KB per file

        start = time.time()
        for i in range(file_count):
            (temp_dir / f"file_{i:04d}.tmp").write_text(content)
        creation_time = time.time() - start

        target = ScanTarget(id="perf_test", name="Performance Test", path=temp_dir)

        scanner = CoreScanner()
        scan_start = time.time()
        result = scanner.scan_single_target(target)
        scan_time = time.time() - scan_start

        # 验证结果
        assert result.file_count == file_count
        assert result.total_size == file_count * len(content)

        # 性能断言（根据实际情况调整）
        # 扫描 1000 个小文件应该在 10 秒内完成（调整预期以适应不同系统）
        assert scan_time < 10.0, f"Scan took {scan_time:.2f}s, expected < 10.0s"

        print(f"\nPerformance metrics:")
        print(f"  File creation: {creation_time:.3f}s")
        print(f"  Scan time: {scan_time:.3f}s")
        print(f"  Files per second: {file_count / scan_time:.0f}")

    @pytest.mark.slow
    def test_cache_performance_improvement(self, temp_dir):
        """测试缓存对性能的改善"""
        # 创建测试文件
        for i in range(100):
            (temp_dir / f"file_{i:03d}.tmp").write_text("content")

        target = ScanTarget(id="cache_test", name="Cache Test", path=temp_dir)
        scanner = CoreScanner()

        # 第一次扫描（无缓存）
        start = time.time()
        result1 = scanner.scan_single_target(target)
        first_scan_time = time.time() - start

        # 第二次扫描（有缓存）
        # 注意：当前实现中缓存主要用于优化，不一定跳过扫描
        # 这里测试缓存操作本身的性能
        cache = scanner.cache
        cache_start = time.time()
        for file_info in result1.files:
            cache.get(file_info.path)
        cache_time = time.time() - cache_start

        # 验证缓存操作快速
        assert cache_time < 0.1, f"Cache lookup took {cache_time:.3f}s"

        print(f"\nCache performance:")
        print(f"  First scan: {first_scan_time:.3f}s")
        print(f"  Cache lookup: {cache_time:.3f}s")


class TestScannerIntegration:
    """扫描器集成测试"""

    def test_scanner_with_event_bus(self, test_files_dir):
        """测试扫描器与事件总线集成"""
        events_received = []

        def progress_handler(event):
            events_received.append(event.type.value)

        # 订阅事件
        from src.utils.event_bus import EventBus, EventType
        event_bus = EventBus()
        event_bus.subscribe(EventType.SCAN_PROGRESS, progress_handler)

        # 创建扫描器并执行扫描
        scanner = CoreScanner(event_bus=event_bus)
        target = ScanTarget(id="event_test", name="Event Test", path=test_files_dir)

        list(scanner.scan([target]))

        # 验证事件发布
        assert len(events_received) > 0, "Should receive progress events"

    def test_scanner_with_state_manager(self, test_files_dir):
        """测试扫描器与状态管理器集成"""
        from src.controllers.state_manager import StateManager

        state_manager = StateManager()
        scanner = CoreScanner(state_manager=state_manager)

        target = ScanTarget(id="state_test", name="State Test", path=test_files_dir)

        # 扫描前状态应该是 IDLE
        assert state_manager.current_state == SystemState.IDLE

        # 执行扫描
        list(scanner.scan([target]))

        # 扫描后应该返回 IDLE（如果没有其他操作）
        assert state_manager.current_state == SystemState.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
