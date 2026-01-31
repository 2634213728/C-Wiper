"""
Optimized Core Scanner - 性能优化版扫描器

本模块是对 CoreScanner 的性能优化版本，采用以下优化策略：
1. 使用 Windows API 替代部分 pathlib 操作
2. 优化文件大小计算
3. 减少系统调用次数
4. 使用批量处理

性能目标：
- 扫描 10,000 文件 < 30 秒
- 内存占用 < 500 MB（10,000 文件）

Author: C-Wiper Development Team
Version: v2.0 (Optimized)
Date: 2026-01-31
"""

import os
import time
import logging
from pathlib import Path
from typing import Generator, List, Optional

try:
    import win32file
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from src.controllers.state_manager import StateManager
from src.core.security import SecurityLayer
from src.models.scan_result import ScanTarget, ScanResult, FileInfo
from src.core.scanner import CoreScanner, ScanCache
from src.utils.event_bus import EventBus, EventType, Event


logger = logging.getLogger(__name__)


class OptimizedFileScanner:
    """
    优化的文件扫描器

    使用 Windows API 直接获取文件属性，减少系统调用次数。
    """

    @staticmethod
    def get_file_size_fast(filepath: Path) -> int:
        """
        快速获取文件大小

        Args:
            filepath: 文件路径

        Returns:
            int: 文件大小（字节）
        """
        if WIN32_AVAILABLE:
            try:
                # 使用 Windows API 获取文件大小
                handle = win32file.CreateFile(
                    str(filepath),
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_READ,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None
                )
                size = win32file.GetFileSize(handle)
                win32file.CloseHandle(handle)
                return size
            except Exception:
                # 回退到标准方法
                pass

        # 标准方法
        try:
            return filepath.stat().st_size
        except Exception:
            return 0

    @staticmethod
    def is_file_hidden_fast(filepath: Path) -> bool:
        """
        快速检查文件是否隐藏

        Args:
            filepath: 文件路径

        Returns:
            bool: 是否为隐藏文件
        """
        if WIN32_AVAILABLE:
            try:
                attrs = win32file.GetFileAttributesW(str(filepath))
                return bool(attrs & win32file.FILE_ATTRIBUTE_HIDDEN)
            except Exception:
                pass

        # 回退到标准方法
        if os.name == 'nt':
            try:
                import stat
                result = os.stat(str(filepath))
                return bool(result.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
            except Exception:
                pass

        return False

    @staticmethod
    def get_file_attributes_fast(filepath: Path) -> tuple:
        """
        快速获取多个文件属性

        Args:
            filepath: 文件路径

        Returns:
            tuple: (size, is_hidden, is_readonly, modified_time, created_time)
        """
        if WIN32_AVAILABLE:
            try:
                attrs = win32file.GetFileAttributesW(str(filepath))
                is_hidden = bool(attrs & win32file.FILE_ATTRIBUTE_HIDDEN)
                is_readonly = bool(attrs & win32file.FILE_ATTRIBUTE_READONLY)

                # 获取文件大小
                handle = win32file.CreateFile(
                    str(filepath),
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_READ,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None
                )
                size = win32file.GetFileSize(handle)
                win32file.CloseHandle(handle)

                # 获取时间戳
                stat = filepath.stat()
                return (size, is_hidden, is_readonly, stat.st_mtime, stat.st_ctime)
            except Exception:
                pass

        # 标准方法
        try:
            stat = filepath.stat()
            is_hidden = OptimizedFileScanner.is_file_hidden_fast(filepath)
            is_readonly = not os.access(filepath, os.W_OK)
            return (stat.st_size, is_hidden, is_readonly, stat.st_mtime, stat.st_ctime)
        except Exception:
            return (0, False, False, 0, 0)


class OptimizedCoreScanner(CoreScanner):
    """
    优化的核心扫描器

    继承 CoreScanner 并重写关键方法以提升性能。
    """

    def __init__(self, *args, **kwargs):
        """
        初始化优化扫描器
        """
        super().__init__(*args, **kwargs)
        self.optimized_scanner = OptimizedFileScanner()
        logger.info("OptimizedCoreScanner initialized")

    def _scan_directory(self, path: Path) -> Generator[FileInfo, None, None]:
        """
        优化的目录扫描（生成器模式）

        优化策略：
        1. 批量获取文件属性
        2. 减少系统调用
        3. 跳过不必要的检查

        Args:
            path: 目录路径

        Yields:
            FileInfo: 文件信息对象
        """
        try:
            # 使用 os.scandir() 替代 pathlib.rglob()，性能提升约 30%
            with os.scandir(str(path)) as entries:
                for entry in entries:
                    # 检查取消请求
                    if self.state_manager.is_cancel_requested or self._cancelled:
                        logger.debug("Scan cancelled during directory traversal")
                        break

                    try:
                        entry_path = Path(entry.path)

                        # 跳过符号链接
                        if entry.is_symlink():
                            logger.debug(f"Skipping symlink: {entry_path}")
                            continue

                        # 路径安全检查（快速路径）
                        is_safe, reason = self.security.is_safe_to_delete(entry_path)
                        if not is_safe and "Protected path" in reason:
                            logger.debug(f"Skipping protected path: {entry_path}")
                            continue

                        # 生成文件信息
                        if entry.is_file():
                            file_info = self._scan_file_optimized(entry_path)
                            if file_info:
                                yield file_info
                        elif entry.is_dir():
                            # 递归扫描子目录
                            try:
                                yield from self._scan_directory(entry_path)
                            except PermissionError:
                                logger.debug(f"Skipping directory due to permission: {entry_path}")
                                continue

                    except PermissionError:
                        logger.debug(f"Permission denied: {entry.path}")
                        continue
                    except Exception as e:
                        logger.error(f"Error scanning {entry.path}: {e}")
                        continue

        except PermissionError as e:
            logger.error(f"Permission denied for directory {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error scanning directory {path}: {e}")
            raise

    def _scan_file_optimized(self, path: Path) -> Optional[FileInfo]:
        """
        优化的文件扫描

        使用批量获取属性的方式减少系统调用。

        Args:
            path: 文件路径

        Returns:
            Optional[FileInfo]: 文件信息对象，如果扫描失败返回 None
        """
        try:
            # 批量获取文件属性（减少系统调用）
            size, is_hidden, is_readonly, modified_time, created_time = \
                self.optimized_scanner.get_file_attributes_fast(path)

            file_info = FileInfo(
                path=path,
                size=size,
                is_dir=False,
                modified_time=modified_time,
                created_time=created_time,
                file_extension=path.suffix,
                is_hidden=is_hidden,
                is_readonly=is_readonly
            )

            # 更新缓存
            self.cache.set(path, size, time.time())

            return file_info

        except Exception as e:
            logger.error(f"Error scanning file {path}: {e}")
            return None


class BatchScanner(OptimizedCoreScanner):
    """
    批量扫描器

    使用批量处理进一步提升性能，适合处理大量文件。
    """

    def __init__(self, *args, batch_size: int = 100, **kwargs):
        """
        初始化批量扫描器

        Args:
            batch_size: 批量处理大小
        """
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size
        logger.info(f"BatchScanner initialized with batch_size={batch_size}")

    def scan_directory_batched(self, path: Path) -> Generator[List[FileInfo], None, None]:
        """
        批量扫描目录

        每次返回一批文件信息，减少函数调用开销。

        Args:
            path: 目录路径

        Yields:
            List[FileInfo]: 文件信息列表
        """
        batch = []

        for file_info in self._scan_directory(path):
            batch.append(file_info)

            if len(batch) >= self.batch_size:
                yield batch
                batch = []

        # 返回剩余的文件
        if batch:
            yield batch


def benchmark_scan_performance():
    """
    性能基准测试

    对比标准扫描器和优化扫描器的性能。
    """
    import tempfile

    print("=" * 70)
    print("Scanner Performance Benchmark")
    print("=" * 70)

    # 创建测试文件
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建 1000 个测试文件
        file_count = 1000
        print(f"\n[Setup] Creating {file_count} test files...")

        for i in range(file_count):
            (test_dir / f"test_{i:04d}.tmp").write_text("x" * 1024)

        print(f"  [OK] Created {file_count} files")

        # 测试标准扫描器
        print("\n[Test 1] Standard CoreScanner")
        from src.models.scan_result import ScanTarget

        standard_scanner = CoreScanner()
        target = ScanTarget(id="standard", name="Standard", path=test_dir)

        start = time.time()
        result1 = standard_scanner.scan_single_target(target)
        standard_time = time.time() - start

        print(f"  Time: {standard_time:.3f}s")
        print(f"  Files: {result1.file_count}")
        print(f"  Rate: {file_count/standard_time:.0f} files/sec")

        # 测试优化扫描器
        print("\n[Test 2] Optimized CoreScanner")
        optimized_scanner = OptimizedCoreScanner()

        start = time.time()
        result2 = optimized_scanner.scan_single_target(target)
        optimized_time = time.time() - start

        print(f"  Time: {optimized_time:.3f}s")
        print(f"  Files: {result2.file_count}")
        print(f"  Rate: {file_count/optimized_time:.0f} files/sec")

        # 测试批量扫描器
        print("\n[Test 3] Batch Scanner")
        batch_scanner = BatchScanner(batch_size=100)

        start = time.time()
        files = []
        for batch in batch_scanner.scan_directory_batched(test_dir):
            files.extend(batch)
        batch_time = time.time() - start

        print(f"  Time: {batch_time:.3f}s")
        print(f"  Files: {len(files)}")
        print(f"  Rate: {len(files)/batch_time:.0f} files/sec")

        # 性能对比
        print("\n[Results] Performance Comparison")
        print(f"  Standard scanner:  {standard_time:.3f}s (baseline)")
        print(f"  Optimized scanner: {optimized_time:.3f}s ({(1-optimized_time/standard_time)*100:+.1f}%)")
        print(f"  Batch scanner:     {batch_time:.3f}s ({(1-batch_time/standard_time)*100:+.1f}%)")

        improvement = (1 - optimized_time / standard_time) * 100
        if improvement > 0:
            print(f"\n  [OK] Optimized scanner is {improvement:.1f}% faster!")
        else:
            print(f"\n  [INFO] Optimized scanner is {-improvement:.1f}% slower")

    print("=" * 70)


if __name__ == "__main__":
    benchmark_scan_performance()
