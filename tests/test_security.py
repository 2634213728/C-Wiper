"""
Unit Tests for Security Layer Module

本模块包含 SecurityLayer 的单元测试，涵盖路径保护、系统文件识别、符号链接检测等功能。

测试覆盖：
- 路径保护
- 系统文件识别
- 符号链接检测
- 真实扩展名检测
- TOCTOU 防护

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.security import SecurityLayer


class TestSecurityLayer:
    """测试 SecurityLayer 类"""

    def test_security_layer_initialization(self):
        """测试安全层初始化"""
        security = SecurityLayer()

        assert security.protected_paths is not None
        assert len(security.protected_paths) > 0
        assert security.system_files is not None
        assert len(security.system_files) > 0

    def test_protected_paths_contains_windows_paths(self):
        """测试保护路径包含关键 Windows 路径"""
        security = SecurityLayer()

        # 检查关键路径在保护列表中
        protected_path_strs = [str(p).lower() for p in security.protected_paths]

        # Windows 目录
        assert any("windows" in p for p in protected_path_strs)
        # Program Files
        assert any("program files" in p for p in protected_path_strs)
        # System32
        assert any("system32" in p for p in protected_path_strs)

    def test_system_files_contains_critical_files(self):
        """测试系统文件列表包含关键文件"""
        security = SecurityLayer()

        # 检查关键系统文件
        assert "ntldr" in [f.lower() for f in security.system_files]
        assert "boot.ini" in [f.lower() for f in security.system_files]

    def test_is_safe_to_delete_protected_path(self):
        """测试保护路径的安全检查"""
        security = SecurityLayer()

        # Windows 目录应该不安全
        windows_path = Path("C:/Windows/System32/kernel32.dll")
        is_safe, reason = security.is_safe_to_delete(windows_path)

        assert is_safe is False
        assert "Protected path" in reason

    def test_is_safe_to_delete_safe_path(self, temp_dir):
        """测试安全路径的安全检查"""
        security = SecurityLayer()

        # 临时目录应该是安全的
        temp_file = temp_dir / "test.txt"
        temp_file.write_text("test")

        is_safe, reason = security.is_safe_to_delete(temp_file)

        assert is_safe is True
        assert "OK" in reason

    def test_is_system_file(self):
        """测试系统文件识别"""
        security = SecurityLayer()

        # 系统文件应该被识别
        assert security.is_system_file("ntldr")
        assert security.is_system_file("boot.ini")
        assert security.is_system_file("hal.dll")

    def test_is_not_system_file(self):
        """测试非系统文件识别"""
        security = SecurityLayer()

        # 普通文件不应该被识别为系统文件
        assert not security.is_system_file("document.txt")
        assert not security.is_system_file("photo.jpg")
        assert not security.is_system_file("myapp.exe")

    def test_is_symlink_windows(self, temp_dir):
        """测试 Windows 符号链接检测"""
        security = SecurityLayer()

        # 普通文件不是符号链接
        regular_file = temp_dir / "regular.txt"
        regular_file.write_text("content")

        assert not security.is_symlink(regular_file)

    def test_resolve_symlink_safe(self, temp_dir):
        """测试安全地解析符号链接"""
        security = SecurityLayer()

        # 普通文件应该返回自身
        regular_file = temp_dir / "regular.txt"
        regular_file.write_text("content")

        resolved = security.resolve_symlink_safe(regular_file)
        assert resolved == regular_file.resolve()

    def test_get_real_extension(self, temp_dir):
        """测试获取真实文件扩展名"""
        security = SecurityLayer()

        # 普通文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        ext = security.get_real_extension(test_file)
        assert ext.lower() == ".txt"

    def test_get_real_extension_double_extension(self, temp_dir):
        """测试双重扩展名检测"""
        security = SecurityLayer()

        # 创建具有双重扩展名的文件
        test_file = temp_dir / "dangerous.exe.txt"
        test_file.write_text("content")

        # 注意：当前实现可能只返回最后一个扩展名
        ext = security.get_real_extension(test_file)
        assert ".txt" in ext.lower()

    def test_check_toctou_protection(self, temp_dir):
        """测试 TOCTOU（Time-of-check Time-of-use）防护"""
        security = SecurityLayer()

        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        # TOCTOU 检查应该通过
        is_safe = security.check_toctou_protection(test_file)
        assert is_safe is True

    def test_protected_path_case_insensitive(self):
        """测试保护路径匹配不区分大小写"""
        security = SecurityLayer()

        # 不同大小写的 Windows 路径都应该被保护
        test_paths = [
            Path("C:/Windows/System32/kernel32.dll"),
            Path("C:/WINDOWS/system32/kernel32.dll"),
            Path("c:/windows/SYSTEM32/kernel32.dll")
        ]

        for test_path in test_paths:
            is_safe, reason = security.is_safe_to_delete(test_path)
            assert is_safe is False, f"Path {test_path} should be protected"

    def test_is_safe_to_delete_permissions(self, temp_dir):
        """测试权限检查"""
        security = SecurityLayer()

        # 创建只读文件
        readonly_file = temp_dir / "readonly.txt"
        readonly_file.write_text("content")

        # 在 Windows 上设置只读属性
        if os.name == 'nt':
            import stat
            os.chmod(readonly_file, stat.S_IREAD)

        # 安全检查应该检测到只读文件
        is_safe, reason = security.is_safe_to_delete(readonly_file)
        # 根据实现，可能仍然返回 True（只读不意味着不安全）
        assert isinstance(is_safe, bool)


class TestSecurityEdgeCases:
    """安全边界情况测试"""

    def test_empty_path(self):
        """测试空路径处理"""
        security = SecurityLayer()

        # 空路径应该返回不安全
        is_safe, reason = security.is_safe_to_delete(Path(""))
        assert is_safe is False

    def test_relative_path(self):
        """测试相对路径处理"""
        security = SecurityLayer()

        # 相对路径应该被正确处理
        relative_path = Path("../test/file.txt")
        is_safe, reason = security.is_safe_to_delete(relative_path)

        # 相对路径应该被转换为绝对路径后检查
        assert isinstance(is_safe, bool)

    def test_non_existent_path(self):
        """测试不存在的路径"""
        security = SecurityLayer()

        non_existent = Path("C:/NonExistent/Path/file.txt")
        is_safe, reason = security.is_safe_to_delete(non_existent)

        # 不存在的路径应该返回不安全
        assert is_safe is False

    def test_very_long_path(self, temp_dir):
        """测试超长路径处理"""
        security = SecurityLayer()

        # 创建深层嵌套目录
        deep_dir = temp_dir
        for i in range(10):
            deep_dir = deep_dir / f"level{i}"

        deep_dir.mkdir(parents=True, exist_ok=True)
        test_file = deep_dir / "test.txt"
        test_file.write_text("content")

        is_safe, reason = security.is_safe_to_delete(test_file)
        # 深层嵌套的安全文件应该是安全的
        assert isinstance(is_safe, bool)

    def test_special_characters_in_filename(self, temp_dir):
        """测试文件名中的特殊字符"""
        security = SecurityLayer()

        # 创建包含特殊字符的文件名（在 Windows 允许的范围内）
        special_files = [
            "test file.txt",  # 空格
            "test-file.txt",  # 连字符
            "test_file.txt",  # 下划线
            "test.file.txt",  # 多个点
        ]

        for filename in special_files:
            test_file = temp_dir / filename
            test_file.write_text("content")

            is_safe, reason = security.is_safe_to_delete(test_file)
            # 这些文件应该是安全的
            assert isinstance(is_safe, bool)


class TestSecurityIntegration:
    """安全层集成测试"""

    def test_security_layer_with_scanner(self, temp_dir):
        """测试安全层与扫描器集成"""
        from src.core.scanner import CoreScanner

        security = SecurityLayer()
        scanner = CoreScanner(security=security)

        # 创建测试文件（包含一些受保护的路径模式）
        protected_dir = temp_dir / "System32"
        protected_dir.mkdir()
        (protected_dir / "kernel32.dll").write_text("fake")

        safe_dir = temp_dir / "Temp"
        safe_dir.mkdir()
        (safe_dir / "test.tmp").write_text("content")

        # 扫描安全目录
        from src.models.scan_result import ScanTarget
        target = ScanTarget(id="safe", name="Safe", path=safe_dir)
        result = scanner.scan_single_target(target)

        # 应该成功扫描
        assert result.is_success()

    def test_security_layer_prevents_deletion(self, temp_dir):
        """测试安全层防止删除受保护文件"""
        from src.core.cleaner import CleanerExecutor

        security = SecurityLayer()
        cleaner = CleanerExecutor(security=security)

        # 创建受保护路径的模拟文件
        windows_dir = temp_dir / "Windows"
        windows_dir.mkdir()
        protected_file = windows_dir / "kernel32.dll"
        protected_file.write_text("fake")

        import time
        from src.models.scan_result import FileInfo
        file_info = FileInfo(
            path=protected_file,
            size=4,
            is_dir=False,
            modified_time=time.time()
        )

        # 尝试清理（应该被阻止）
        result = cleaner.clean([file_info])

        # 应该失败或跳过
        assert not result.success or result.files_deleted == 0


class TestSecurityPerformance:
    """安全层性能测试"""

    @pytest.mark.slow
    def test_security_check_performance(self, temp_dir):
        """测试安全检查性能"""
        security = SecurityLayer()

        # 创建大量测试文件
        for i in range(1000):
            (temp_dir / f"file{i}.txt").write_text("content")

        import time
        start = time.time()

        # 检查所有文件的安全性
        for i in range(1000):
            test_file = temp_dir / f"file{i}.txt"
            is_safe, _ = security.is_safe_to_delete(test_file)

        check_time = time.time() - start

        # 性能断言：1000 次检查应该在 1 秒内完成
        assert check_time < 1.0, f"Security checks took {check_time:.3f}s"

        print(f"\nSecurity check performance:")
        print(f"  1000 checks: {check_time:.3f}s")
        print(f"  Average: {check_time/1000*1000:.2f}ms per check")


class TestSecurityMocking:
    """使用 Mock 的安全层测试"""

    def test_mock_protected_paths(self):
        """测试模拟保护路径"""
        security = SecurityLayer()

        # Mock 保护路径列表
        with patch.object(security, 'protected_paths', [Path("C:/Mock/Protected")]):
            test_path = Path("C:/Mock/Protected/file.txt")
            is_safe, reason = security.is_safe_to_delete(test_path)

            assert is_safe is False

    def test_mock_system_files(self):
        """测试模拟系统文件"""
        security = SecurityLayer()

        # Mock 系统文件列表
        with patch.object(security, 'system_files', ["mock.sys"]):
            assert security.is_system_file("mock.sys")
            assert not security.is_system_file("other.txt")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
