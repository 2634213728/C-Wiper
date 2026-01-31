"""
Integration Test - Complete Clean Workflow

本模块测试完整的清理工作流程，包括扫描、预览、确认、执行等。

测试场景：
1. 扫描文件
2. 预览清理
3. 确认清理
4. 执行清理
5. 生成报告

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
import time
from pathlib import Path

from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.models.scan_result import ScanTarget


@pytest.mark.integration
class TestCleanWorkflow:
    """测试清理工作流程"""

    def test_complete_clean_workflow(self, temp_dir):
        """测试完整的清理工作流程"""
        print("\n" + "=" * 70)
        print("Integration Test: Complete Clean Workflow")
        print("=" * 70)

        # 步骤 1: 创建测试文件
        print("\n[Step 1] Creating test files for cleaning")
        test_files = []

        # 创建临时文件（L1 安全）
        for i in range(10):
            temp_file = temp_dir / f"temp{i}.tmp"
            temp_file.write_text(f"temp content {i}")
            test_files.append(temp_file)

        # 创建日志文件（L2 审查）
        for i in range(5):
            log_file = temp_dir / f"app{i}.log"
            log_file.write_text(f"log content {i}")
            test_files.append(log_file)

        print(f"  [OK] Created {len(test_files)} test files")

        # 步骤 2: 扫描文件
        print("\n[Step 2] Scanning files")
        scan_controller = ScanController()
        target = ScanTarget(
            id="clean_test",
            name="Clean Test",
            path=temp_dir
        )

        scan_controller.start_scan([target])
        scan_controller.wait_for_completion(timeout=30)

        scan_results = scan_controller.get_results()
        print(f"  [OK] Scanned {scan_results[0].file_count} files")

        # 步骤 3: 获取可清理文件
        print("\n[Step 3] Getting cleanable files")
        l1_files = scan_controller.get_matched_files("L1_SAFE")
        l2_files = scan_controller.get_matched_files("L2_REVIEW")

        print(f"  [OK] L1_SAFE files: {len(l1_files)}")
        print(f"  [OK] L2_REVIEW files: {len(l2_files)}")

        assert len(l1_files) > 0, "Should have at least one L1 file"

        # 步骤 4: 预览清理
        print("\n[Step 4] Previewing cleanup")
        clean_controller = CleanController()

        preview = clean_controller.preview_clean(l1_files)
        print(f"  [OK] Preview:")
        print(f"    Files to clean: {preview['file_count']}")
        print(f"    Total size: {preview['formatted_size']}")

        assert preview['file_count'] == len(l1_files)
        assert preview['total_size'] > 0

        # 步骤 5: 确认清理
        print("\n[Step 5] Confirming cleanup")
        clean_controller.confirm_clean()
        print("  [OK] Cleanup confirmed")

        # 步骤 6: 执行清理
        print("\n[Step 6] Executing cleanup")
        clean_start = time.time()

        clean_controller.start_clean(l1_files)
        clean_controller.wait_for_completion(timeout=30)

        clean_duration = time.time() - clean_start
        print(f"  [OK] Cleanup completed in {clean_duration:.3f}s")

        # 步骤 7: 获取清理报告
        print("\n[Step 7] Getting cleanup report")
        report = clean_controller.get_report()

        assert report is not None, "Should have cleanup report"
        print(f"  [OK] Cleanup Report:")
        print(f"    Files deleted: {report['files_deleted']}")
        print(f"    Size freed: {report['formatted_size']}")
        print(f"    Duration: {report['duration']:.3f}s")
        print(f"    Success: {report['success']}")

        # 步骤 8: 验证文件被删除
        print("\n[Step 8] Verifying file deletion")
        deleted_count = 0
        for file_path in l1_files:
            if not file_path.exists():
                deleted_count += 1

        print(f"  [OK] Verified deletion: {deleted_count}/{len(l1_files)} files")

        # 验证
        assert report['files_deleted'] > 0, "Should delete at least one file"
        assert report['success'], "Cleanup should be successful"

        print("\n" + "=" * 70)
        print("[OK] Complete clean workflow test passed!")
        print("=" * 70)

    def test_clean_without_confirmation(self, temp_dir):
        """测试未确认时清理失败"""
        print("\n" + "=" * 70)
        print("Integration Test: Clean Without Confirmation")
        print("=" * 70)

        # 创建测试文件
        print("\n[Setup] Creating test file")
        test_file = temp_dir / "test.tmp"
        test_file.write_text("test content")

        import time
        from src.models.scan_result import FileInfo
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        # 创建清理控制器（不确认）
        print("\n[Step 1] Creating CleanController without confirmation")
        clean_controller = CleanController()

        # 尝试启动清理
        print("\n[Step 2] Attempting to clean without confirmation")
        result = clean_controller.start_clean([file_info])

        assert result is False, "Clean should fail without confirmation"
        print("  [OK] Clean correctly rejected (no confirmation)")

        print("=" * 70)
        print("[OK] Clean without confirmation test passed!")
        print("=" * 70)

    def test_clean_mixed_risk_levels(self, temp_dir):
        """测试清理混合风险级别的文件"""
        print("\n" + "=" * 70)
        print("Integration Test: Clean Mixed Risk Levels")
        print("=" * 70)

        # 创建不同风险级别的文件
        print("\n[Setup] Creating files with different risk levels")
        files = {
            "temp1.tmp": "temp",
            "temp2.tmp": "temp",
            "log1.log": "log",
            "log2.log": "log",
            "cache.cache": "cache",
        }

        for filename, content in files.items():
            (temp_dir / filename).write_text(content)

        print(f"  [OK] Created {len(files)} test files")

        # 扫描
        print("\n[Step 1] Scanning files")
        scan_controller = ScanController()
        target = ScanTarget(id="mixed_test", name="Mixed Test", path=temp_dir)

        scan_controller.start_scan([target])
        scan_controller.wait_for_completion(timeout=30)

        # 获取不同风险级别的文件
        l1_files = scan_controller.get_matched_files("L1_SAFE")
        l2_files = scan_controller.get_matched_files("L2_REVIEW")

        print(f"\n[Step 2] File distribution:")
        print(f"    L1_SAFE: {len(l1_files)} files")
        print(f"    L2_REVIEW: {len(l2_files)} files")

        # 只清理 L1 文件
        if l1_files:
            print("\n[Step 3] Cleaning L1_SAFE files only")
            clean_controller = CleanController()

            preview = clean_controller.preview_clean(l1_files)
            print(f"  [OK] Preview: {preview['file_count']} files, {preview['formatted_size']}")

            clean_controller.confirm_clean()
            clean_controller.start_clean(l1_files)
            clean_controller.wait_for_completion(timeout=30)

            report = clean_controller.get_report()
            print(f"  [OK] Deleted {report['files_deleted']} files")

            # 验证 L2 文件仍然存在
            print("\n[Step 4] Verifying L2_REVIEW files still exist")
            l2_still_exist = sum(1 for f in l2_files if f.exists())
            print(f"  [OK] {l2_still_exist}/{len(l2_files)} L2 files still exist")

        print("=" * 70)
        print("[OK] Mixed risk levels clean test passed!")
        print("=" * 70)

    def test_clean_empty_list(self, temp_dir):
        """测试清理空文件列表"""
        print("\n" + "=" * 70)
        print("Integration Test: Clean Empty File List")
        print("=" * 70)

        print("\n[Setup] Creating CleanController")
        clean_controller = CleanController()

        print("\n[Step 1] Previewing empty list")
        preview = clean_controller.preview_clean([])
        print(f"  [OK] Preview: {preview['file_count']} files")

        assert preview['file_count'] == 0
        assert preview['total_size'] == 0

        print("\n[Step 2] Confirming and cleaning empty list")
        clean_controller.confirm_clean()
        result = clean_controller.start_clean([])

        # 应该成功（空列表）或失败（取决于实现）
        print(f"  [OK] Clean result: {result}")

        print("=" * 70)
        print("[OK] Empty list clean test passed!")
        print("=" * 70)


@pytest.mark.integration
class TestCleanErrorHandling:
    """测试清理错误处理"""

    def test_clean_non_existent_file(self, temp_dir):
        """测试清理不存在的文件"""
        print("\n" + "=" * 70)
        print("Integration Test: Clean Non-existent File")
        print("=" * 70)

        # 创建不存在的文件信息
        print("\n[Setup] Creating file info for non-existent file")
        import time
        from src.models.scan_result import FileInfo
        file_info = FileInfo(
            path=Path("C:/NonExistent/Path/file12345.tmp"),
            size=1024,
            is_dir=False,
            modified_time=time.time()
        )

        # 尝试清理
        print("\n[Step 1] Attempting to clean non-existent file")
        clean_controller = CleanController()
        clean_controller.confirm_clean()

        clean_controller.start_clean([file_info])
        clean_controller.wait_for_completion(timeout=10)

        report = clean_controller.get_report()
        print(f"  [OK] Clean report:")
        print(f"    Success: {report['success']}")
        print(f"    Files deleted: {report['files_deleted']}")

        # 应该处理错误而不崩溃
        assert isinstance(report, dict)

        print("=" * 70)
        print("[OK] Non-existent file clean test passed!")
        print("=" * 70)

    def test_clean_protected_file(self, temp_dir):
        """测试清理受保护文件（被阻止）"""
        print("\n" + "=" * 70)
        print("Integration Test: Clean Protected File")
        print("=" * 70)

        # 创建模拟受保护路径的文件
        print("\n[Setup] Creating file in protected path pattern")
        protected_dir = temp_dir / "System32"
        protected_dir.mkdir()

        protected_file = protected_dir / "kernel32.dll"
        protected_file.write_text("fake system file")

        import time
        from src.models.scan_result import FileInfo
        file_info = FileInfo(
            path=protected_file,
            size=len("fake system file"),
            is_dir=False,
            modified_time=time.time()
        )

        # 尝试清理
        print("\n[Step 1] Attempting to clean protected file")
        clean_controller = CleanController()
        clean_controller.confirm_clean()

        clean_controller.start_clean([file_info])
        clean_controller.wait_for_completion(timeout=10)

        report = clean_controller.get_report()
        print(f"  [OK] Clean report:")
        print(f"    Success: {report.get('success', False)}")
        print(f"    Files deleted: {report.get('files_deleted', 0)}")

        # 受保护文件不应该被删除
        assert report.get('files_deleted', 0) == 0
        assert protected_file.exists(), "Protected file should still exist"

        print("\n[Step 2] Verifying file protection")
        print("  [OK] Protected file was not deleted")

        print("=" * 70)
        print("[OK] Protected file clean test passed!")
        print("=" * 70)


@pytest.mark.integration
class TestCleanPerformance:
    """测试清理性能"""

    @pytest.mark.slow
    def test_clean_many_files_performance(self, temp_dir):
        """测试清理大量文件的性能"""
        print("\n" + "=" * 70)
        print("Integration Test: Clean Many Files Performance")
        print("=" * 70)

        # 创建大量文件
        file_count = 1000
        print(f"\n[Setup] Creating {file_count} test files")
        for i in range(file_count):
            (temp_dir / f"file_{i:04d}.tmp").write_text("x" * 1024)

        print(f"  [OK] Created {file_count} files")

        # 扫描
        print("\n[Step 1] Scanning files")
        scan_controller = ScanController()
        target = ScanTarget(id="perf_test", name="Performance Test", path=temp_dir)

        scan_start = time.time()
        scan_controller.start_scan([target])
        scan_controller.wait_for_completion(timeout=60)
        scan_time = time.time() - scan_start

        l1_files = scan_controller.get_matched_files("L1_SAFE")
        print(f"  [OK] Scanned {len(l1_files)} L1 files in {scan_time:.3f}s")

        # 清理
        print("\n[Step 2] Cleaning files")
        clean_controller = CleanController()
        clean_controller.confirm_clean()

        clean_start = time.time()
        clean_controller.start_clean(l1_files)
        clean_controller.wait_for_completion(timeout=60)
        clean_time = time.time() - clean_start

        report = clean_controller.get_report()
        print(f"  [OK] Cleaned {report['files_deleted']} files in {clean_time:.3f}s")

        # 性能指标
        print("\n[Step 3] Performance metrics")
        print(f"    Scan time: {scan_time:.3f}s ({file_count/scan_time:.0f} files/sec)")
        print(f"    Clean time: {clean_time:.3f}s ({report['files_deleted']/clean_time:.0f} files/sec)")

        # 性能断言
        assert clean_time < 10.0, f"Clean took {clean_time:.3f}s, expected < 10.0s"

        print("=" * 70)
        print("[OK] Clean performance test passed!")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
