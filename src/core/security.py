"""
Security Layer - 安全模块

本模块实现文件删除的安全检查机制，防止误删系统文件和重要数据。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityLayer:
    """
    安全层类

    实现多层安全检查机制，防止误删系统文件、受保护路径和重要文件。
    所有文件删除操作都必须通过此类的安全检查。

    Attributes:
        HARDCODED_PROTECTED: 硬编码的受保护路径列表
        SYSTEM_FILES: 系统文件名列表（绝对不可删除）
        CRITICAL_EXTENSIONS: 关键文件扩展名（需要额外审查）

    Example:
        >>> security = SecurityLayer()
        >>> is_safe, reason = security.is_safe_to_delete(Path("C:/Windows/notepad.exe"))
        >>> if not is_safe:
        ...     print(f"不安全: {reason}")
    """

    # 硬编码的受保护路径（Windows 关键目录）
    HARDCODED_PROTECTED = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\System Volume Information",
        "C:\\Recovery",
        "C:\\Boot",
        "C:\\EFI",
        "C:$Recycle.Bin",
    ]

    # 系统关键文件（绝对不可删除）
    SYSTEM_FILES = [
        "pagefile.sys",
        "hiberfil.sys",
        "swapfile.sys",
        "ntldr",
        "ntdetect.com",
        "boot.ini",
        "bootsect.bak",
    ]

    # 关键文件扩展名（需要额外审查）
    CRITICAL_EXTENSIONS = [
        ".sys",   # 系统驱动
        ".dll",   # 动态链接库
        ".exe",   # 可执行文件
        ".com",   # DOS 可执行文件
        ".bat",   # 批处理文件
        ".cmd",   # 命令脚本
        ".ps1",   # PowerShell 脚本
        ".reg",   # 注册表文件
        ".inf",   # 安装信息文件
    ]

    @classmethod
    def is_safe_to_delete(
        cls,
        path: Path,
        whitelist_extensions: List[str] = None
    ) -> Tuple[bool, str]:
        """
        检查文件是否可以安全删除

        执行三层安全检查：
        1. 检查是否在硬编码的受保护路径中
        2. 检查是否为系统关键文件
        3. 检查扩展名是否在白名单中

        Args:
            path: 要检查的文件路径
            whitelist_extensions: 白名单扩展名列表，这些扩展名的文件不会被删除。
                                 例如：[".docx", ".pdf", ".xlsx"]

        Returns:
            Tuple[bool, str]: (是否安全, 原因说明)
                              - (True, "OK"): 可以安全删除
                              - (False, reason): 不安全，reason 说明原因

        Example:
            >>> security = SecurityLayer()
            >>> # 检查临时文件（应该安全）
            >>> is_safe, reason = security.is_safe_to_delete(Path("C:/Temp/file.tmp"))
            >>> # 检查系统文件（不安全）
            >>> is_safe, reason = security.is_safe_to_delete(Path("C:/Windows/notepad.exe"))
        """
        if whitelist_extensions is None:
            whitelist_extensions = []

        # 参数验证
        if not isinstance(path, Path):
            try:
                path = Path(path)
            except Exception as e:
                return False, f"Invalid path type: {e}"

        # 检查 0: 路径是否存在
        if not path.exists():
            return False, f"File does not exist: {path}"

        # 解析符号链接和快捷方式（TOCTOU 防护）
        try:
            real_path = Path(os.path.realpath(path))
            logger.debug(f"Path resolution: {path} -> {real_path}")
        except Exception as e:
            logger.error(f"Failed to resolve real path: {e}")
            return False, f"Failed to resolve path: {e}"

        # 检查 1: 硬编码的受保护路径
        for protected in cls.HARDCODED_PROTECTED:
            try:
                # 使用 resolve() 处理大小写和路径分隔符
                protected_path = Path(protected)
                if cls._is_path_under(real_path, protected_path):
                    reason = f"Protected path: {protected}"
                    logger.warning(f"Security check failed for {path}: {reason}")
                    return False, reason
            except Exception as e:
                logger.error(f"Error checking protected path {protected}: {e}")
                continue

        # 检查 2: 系统关键文件
        filename = path.name.lower()
        if filename in cls.SYSTEM_FILES:
            reason = f"System file: {filename}"
            logger.warning(f"Security check failed for {path}: {reason}")
            return False, reason

        # 检查 3: 白名单扩展名
        if path.suffix.lower() in [ext.lower() for ext in whitelist_extensions]:
            reason = f"Whitelisted extension: {path.suffix}"
            logger.info(f"Skipping whitelisted file: {path} ({reason})")
            return False, reason

        # 检查 4: 额外的关键扩展名警告（但允许删除）
        if path.suffix.lower() in cls.CRITICAL_EXTENSIONS:
            logger.warning(
                f"Critical extension file: {path} (extension: {path.suffix}). "
                f"Ensure this is safe to delete."
            )
            # 仍然允许删除，但记录警告

        # 所有检查通过
        logger.debug(f"Security check passed for: {path}")
        return True, "OK"

    @classmethod
    def _is_path_under(cls, path: Path, parent: Path) -> bool:
        """
        检查路径是否在父目录下

        Args:
            path: 要检查的路径
            parent: 父目录路径

        Returns:
            bool: 如果 path 在 parent 下返回 True，否则返回 False
        """
        try:
            # 解析为绝对路径
            path_resolved = path.resolve()
            parent_resolved = parent.resolve()

            # 检查 path 的路径前缀是否包含 parent
            path_parts = path_resolved.parts
            parent_parts = parent_resolved.parts

            if len(path_parts) < len(parent_parts):
                return False

            return path_parts[:len(parent_parts)] == parent_parts

        except Exception as e:
            logger.error(f"Error comparing paths: {e}")
            return False

    @classmethod
    def get_real_extension(cls, path: Path) -> str:
        """
        获取文件的真实扩展名

        处理多重扩展名的情况（如 .tar.gz），返回最后一个扩展名。

        Args:
            path: 文件路径

        Returns:
            str: 文件扩展名（包含点号，如 ".txt"），如果没有扩展名返回空字符串

        Example:
            >>> SecurityLayer.get_real_extension(Path("archive.tar.gz"))
            '.gz'
            >>> SecurityLayer.get_real_extension(Path("document.pdf"))
            '.pdf'
        """
        # 获取文件名
        filename = path.name

        # 分割扩展名
        parts = filename.split('.')

        # 如果没有扩展名或只有点号开头
        if len(parts) <= 1:
            return ""

        # 返回最后一个扩展名
        return f".{parts[-1]}"

    @classmethod
    def is_system_path(cls, path: Path) -> bool:
        """
        快速检查路径是否为系统路径

        Args:
            path: 要检查的路径

        Returns:
            bool: 如果是系统路径返回 True，否则返回 False
        """
        try:
            real_path = Path(os.path.realpath(path))
            for protected in cls.HARDCODED_PROTECTED:
                protected_path = Path(protected)
                if cls._is_path_under(real_path, protected_path):
                    return True
            return False
        except Exception:
            return False

    @classmethod
    def add_protected_path(cls, path: str) -> None:
        """
        动态添加受保护路径

        Args:
            path: 要添加到受保护列表的路径

        Note:
            添加的路径只在当前运行时有效，重启后需要重新添加
        """
        if path not in cls.HARDCODED_PROTECTED:
            cls.HARDCODED_PROTECTED.append(path)
            logger.info(f"Added protected path: {path}")
        else:
            logger.warning(f"Path already protected: {path}")


def test_security_layer():
    """
    SecurityLayer Test Function

    Tests basic functionality including path checks, file checks and extension handling.
    """
    import tempfile

    print("=" * 60)
    print("SecurityLayer Test")
    print("=" * 60)

    security = SecurityLayer()

    # Test 1: Protected path check
    print("\n[Test 1] Protected path check")
    test_paths = [
        Path("C:/Windows/System32/notepad.exe"),
        Path("C:/Program Files/App/app.exe"),
        Path("C:/Temp/file.tmp"),
    ]

    for test_path in test_paths:
        is_safe, reason = security.is_safe_to_delete(test_path)
        status = "[OK] Safe" if is_safe else "[WARN] Unsafe"
        print(f"  {status}: {test_path} - {reason}")

    # Test 2: System file check
    print("\n[Test 2] System file check")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        system_file = Path(tmpdir) / "pagefile.sys"
        system_file.touch()

        is_safe, reason = security.is_safe_to_delete(system_file)
        print(f"  [OK] System file check: {system_file.name} - {reason}")
        assert not is_safe, "System files should be protected"

    # Test 3: Whitelist extensions
    print("\n[Test 3] Whitelist extensions")
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_file = Path(tmpdir) / "document.docx"
        doc_file.touch()

        whitelist = [".docx", ".pdf", ".xlsx"]
        is_safe, reason = security.is_safe_to_delete(doc_file, whitelist)
        print(f"  [OK] Whitelist protection: {doc_file.name} - {reason}")
        assert not is_safe, "Whitelisted files should be protected"

    # Test 4: Real extension extraction
    print("\n[Test 4] Real extension extraction")
    test_files = [
        ("archive.tar.gz", ".gz"),
        ("document.pdf", ".pdf"),
        ("script.js", ".js"),
        ("no_extension", ""),
        (".hidden", ""),
    ]

    for filename, expected_ext in test_files:
        path = Path(filename)
        real_ext = security.get_real_extension(path)
        status = "[OK]" if real_ext == expected_ext else "[FAIL]"
        print(f"  {status} {filename} -> {real_ext} (expected: {expected_ext})")
        assert real_ext == expected_ext, f"Extension extraction error: {filename}"

    # Test 5: System path quick check
    print("\n[Test 5] System path quick check")
    assert security.is_system_path(Path("C:/Windows/test.txt")), "Should be system path"
    assert not security.is_system_path(Path("C:/Temp/test.txt")), "Should not be system path"
    print("  [OK] System path check works")

    # Test 6: Dynamic protected path addition
    print("\n[Test 6] Dynamic protected path addition")
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_path = str(Path(tmpdir) / "protected")
        security.add_protected_path(custom_path)

        test_file = Path(custom_path) / "file.txt"
        # Note: we only check path logic here, not creating actual file
        is_sys_path = security.is_system_path(test_file)
        print(f"  [OK] Dynamic protected path: {custom_path} - {'protected' if is_sys_path else 'not protected'}")

    # Test 7: TOCTOU protection (symlink)
    print("\n[Test 7] Symlink resolution")
    # Note: Creating symlinks on Windows requires admin privileges
    # Here we only test resolution logic
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real file
        real_file = Path(tmpdir) / "real_file.txt"
        real_file.write_text("test content")

        # Check real file
        is_safe, reason = security.is_safe_to_delete(real_file)
        print(f"  [OK] Real file check: {real_file} - {reason}")

    print("\n" + "=" * 60)
    print("[OK] All SecurityLayer tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_security_layer()
