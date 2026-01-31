"""
Cleaner Executor - 清理执行器模块

本模块实现文件清理执行器，支持 send2trash 安全删除、进度事件通知和取消操作。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, TYPE_CHECKING

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None
    logging.warning("send2trash not installed, cleanup will be simulated")

# Type checking imports (only for type checkers, not at runtime)
if TYPE_CHECKING:
    from src.controllers.state_manager import StateManager
    from src.core.security import SecurityLayer
    from src.models.scan_result import FileInfo
    from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CleanResult:
    """
    清理结果类

    封装清理操作的结果信息。

    Attributes:
        success: 是否成功
        files_deleted: 已删除文件数
        total_size: 释放的总空间（字节）
        errors: 错误列表
        duration: 清理耗时（秒）
        skipped: 跳过的文件数（安全检查未通过）
    """
    success: bool = True
    files_deleted: int = 0
    total_size: int = 0
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0
    skipped: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "files_deleted": self.files_deleted,
            "total_size": self.total_size,
            "error_count": len(self.errors),
            "duration": self.duration,
            "skipped": self.skipped
        }

    @property
    def formatted_size(self) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.total_size < 1024.0:
                return f"{self.total_size:.2f} {unit}"
            self.total_size /= 1024.0
        return f"{self.total_size:.2f} PB"


class CleanerExecutor:
    """
    清理执行器类

    实现安全的文件清理功能，集成三层安全检查、进度通知和取消机制。

    Attributes:
        security: 安全层实例
        state_manager: 状态管理器实例
        event_bus: 事件总线实例
        _cancelled: 取消标志

    Example:
        >>> executor = CleanerExecutor()
        >>> files = [file_info1, file_info2]
        >>> result = executor.clean(files)
        >>> print(f"Deleted {result.files_deleted} files")
    """

    def __init__(
        self,
        security: Optional[SecurityLayer] = None,
        state_manager: Optional[StateManager] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化清理执行器

        Args:
            security: 安全层实例，默认创建新实例
            state_manager: 状态管理器实例，默认使用全局单例
            event_bus: 事件总线实例，默认使用全局单例
        """
        # Lazy imports to avoid circular dependency
        from src.controllers.state_manager import StateManager
        from src.core.security import SecurityLayer
        from src.utils.event_bus import EventBus

        self.security = security or SecurityLayer()
        self.state_manager = state_manager or StateManager()
        self.event_bus = event_bus or EventBus()
        self._cancelled = False

        if send2trash is None:
            logger.warning("send2trash not available, cleanup will be simulated")

        logger.info("CleanerExecutor initialized")

    def clean(
        self,
        files: List[FileInfo],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> CleanResult:
        """
        清理文件列表

        对文件列表执行安全清理，包括安全检查、删除操作和进度通知。

        Args:
            files: 要清理的文件信息列表
            progress_callback: 进度回调函数，接收 (当前索引, 总数) 参数

        Returns:
            CleanResult: 清理结果对象

        Example:
            >>> files = [file1, file2, file3]
            >>> result = executor.clean(files)
            >>> if result.success:
            ...     print(f"Deleted {result.files_deleted} files")
        """
        # Lazy imports
        from src.utils.event_bus import Event, EventType

        start_time = time.time()
        result = CleanResult()

        if not files:
            logger.warning("No files to clean")
            return result

        logger.info(f"Starting cleanup of {len(files)} files")

        # 发布清理开始事件
        self.event_bus.publish(Event(
            type=EventType.CLEAN_STARTED,
            data={"file_count": len(files)}
        ))

        total_files = len(files)

        for index, file_info in enumerate(files):
            # 检查取消请求
            if self._cancelled or self.state_manager.is_cancel_requested:
                logger.info("Cleanup cancelled by user request")
                result.success = False
                result.errors.append("Cancelled by user")
                break

            try:
                # 安全检查
                is_safe, reason = self.security.is_safe_to_delete(file_info.path)
                if not is_safe:
                    logger.warning(f"Skipping unsafe file {file_info.path}: {reason}")
                    result.skipped += 1
                    continue

                # 执行删除
                if self._delete_file(file_info.path):
                    result.files_deleted += 1
                    result.total_size += file_info.size
                    logger.debug(f"Deleted: {file_info.path}")
                else:
                    result.errors.append(f"Failed to delete: {file_info.path}")

            except Exception as e:
                error_msg = f"Error deleting {file_info.path}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

            # 进度通知
            if progress_callback:
                try:
                    progress_callback(index + 1, total_files)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")

            # 定期发布进度事件
            if (index + 1) % 10 == 0 or (index + 1) == total_files:
                self.event_bus.publish(Event(
                    type=EventType.CLEAN_PROGRESS,
                    data={
                        "current": index + 1,
                        "total": total_files,
                        "deleted": result.files_deleted,
                        "size": result.total_size
                    }
                ))

        # 计算耗时
        result.duration = time.time() - start_time

        # 发布完成事件
        if result.success and len(result.errors) == 0:
            self.event_bus.publish(Event(
                type=EventType.CLEAN_COMPLETED,
                data={
                    "files_deleted": result.files_deleted,
                    "total_size": result.total_size,
                    "duration": result.duration
                }
            ))
        else:
            self.event_bus.publish(Event(
                type=EventType.CLEAN_FAILED,
                data={
                    "files_deleted": result.files_deleted,
                    "error_count": len(result.errors),
                    "errors": result.errors[:5]  # 只发送前5个错误
                }
            ))

        logger.info(
            f"Cleanup completed: {result.files_deleted} files deleted, "
            f"{self._format_size(result.total_size)} freed, "
            f"{result.duration:.2f}s"
        )

        return result

    def _delete_file(self, path: Path) -> bool:
        """
        删除文件（使用 send2trash）

        Args:
            path: 文件路径

        Returns:
            bool: 成功删除返回 True，否则返回 False
        """
        try:
            if send2trash is None:
                # 模拟删除（测试用）
                logger.warning(f"Simulating delete: {path}")
                return True

            # 使用 send2trash 安全删除
            send2trash(str(path))
            return True

        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def cancel(self) -> None:
        """
        取消清理操作

        设置取消标志，清理器会在下次检查时停止。
        """
        self._cancelled = True
        self.state_manager.request_cancel()
        logger.info("Cleanup cancellation requested")

    def reset_cancel(self) -> None:
        """
        重置取消标志

        允许重新开始清理。
        """
        self._cancelled = False
        self.state_manager.reset_cancel_flag()
        logger.debug("Cleanup cancel flag reset")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """
        格式化文件大小为人类可读格式

        Args:
            size_bytes: 大小（字节）

        Returns:
            str: 格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def test_cleaner_executor():
    """
    CleanerExecutor Test Function

    Tests basic functionality including file deletion and progress reporting.
    """
    # Lazy imports
    from src.models.scan_result import FileInfo

    import tempfile
    from typing import Callable

    print("=" * 60)
    print("CleanerExecutor Test")
    print("=" * 60)

    # Test 1: Executor initialization
    print("\n[Test 1] Executor initialization")
    executor = CleanerExecutor()
    print("  [OK] Executor initialized")

    # Test 2: Clean test files
    print("\n[Test 2] Clean test files")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test files
        test_files = []
        for i in range(5):
            file_path = test_dir / f"test_{i}.tmp"
            file_path.write_text(f"Test content {i}")
            file_info = FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            )
            test_files.append(file_info)

        print(f"  [OK] Created {len(test_files)} test files")

        # Execute cleanup
        result = executor.clean(test_files)

        print(f"  [OK] Deleted: {result.files_deleted} files")
        print(f"  [OK] Size: {result.formatted_size}")
        print(f"  [OK] Duration: {result.duration:.3f}s")

        assert result.files_deleted == len(test_files), "Should delete all files"
        assert result.success, "Cleanup should succeed"

    # Test 3: CleanResult
    print("\n[Test 3] CleanResult dataclass")
    result = CleanResult(
        files_deleted=10,
        total_size=1024 * 1024,
        duration=1.5
    )
    result_dict = result.to_dict()
    assert result_dict["files_deleted"] == 10, "Serialization failed"
    print(f"  [OK] CleanResult works: {result.formatted_size}")

    # Test 4: Progress callback
    print("\n[Test 4] Progress callback")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        test_files = []
        for i in range(3):
            file_path = test_dir / f"progress_{i}.tmp"
            file_path.write_text(f"Content {i}")
            test_files.append(FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            ))

        progress_updates = []

        def progress_callback(current: int, total: int):
            progress_updates.append((current, total))
            print(f"    Progress: {current}/{total}")

        result = executor.clean(test_files, progress_callback)
        assert len(progress_updates) == len(test_files), "Should receive progress updates"
        print("  [OK] Progress callback works")

    print("\n" + "=" * 60)
    print("[OK] All CleanerExecutor tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_cleaner_executor()
