"""
Clean Controller - 清理控制器模块

本模块实现清理控制器，负责协调清理流程、实现双重确认机制
和生成清理报告。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from src.controllers.state_manager import StateManager, SystemState
from src.core.cleaner import CleanerExecutor, CleanResult
from src.core.security import SecurityLayer
from src.models.scan_result import FileInfo
from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanController:
    """
    清理控制器类

    协调清理流程，实现双重确认机制，管理清理任务和生成报告。
    支持预览清理、后台执行和取消操作。

    Attributes:
        cleaner: 清理执行器实例
        security: 安全层实例
        state_manager: 状态管理器实例
        event_bus: 事件总线实例
        _clean_thread: 后台清理线程
        _result: 清理结果
        _confirmed: 用户确认标志
        _preview_files: 预览文件列表

    Example:
        >>> controller = CleanController()
        >>> files = [file1, file2, file3]
        >>> # 预览清理
        >>> preview = controller.preview_clean(files)
        >>> print(f"将删除 {preview['file_count']} 个文件")
        >>> # 用户确认后执行
        >>> controller.confirm_clean()
        >>> controller.start_clean(files)
        >>> controller.wait_for_completion()
    """

    # 回收站容量阈值（字节），默认 1GB
    RECYCLE_BIN_THRESHOLD = 1024 * 1024 * 1024

    def __init__(
        self,
        cleaner: Optional[CleanerExecutor] = None,
        security: Optional[SecurityLayer] = None,
        state_manager: Optional[StateManager] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化清理控制器

        Args:
            cleaner: 清理执行器实例，默认创建新实例
            security: 安全层实例，默认创建新实例
            state_manager: 状态管理器实例，默认使用全局单例
            event_bus: 事件总线实例，默认使用全局单例
        """
        self.cleaner = cleaner or CleanerExecutor()
        self.security = security or SecurityLayer()
        self.state_manager = state_manager or StateManager()
        self.event_bus = event_bus or EventBus()

        self._clean_thread: Optional[threading.Thread] = None
        self._result: Optional[CleanResult] = None
        self._confirmed = False
        self._preview_files: List[FileInfo] = []
        self._complete_event = threading.Event()
        self._lock = threading.Lock()

        logger.info("CleanController initialized")

    def preview_clean(self, files: List[FileInfo]) -> Dict[str, Any]:
        """
        预览清理操作

        分析要清理的文件列表，生成预览信息，不执行实际删除。

        Args:
            files: 文件信息列表

        Returns:
            Dict[str, Any]: 预览信息字典，包含：
                - file_count: 文件数量
                - total_size: 总大小
                - risky_files: 需要审查的文件数
                - safe_files: 安全文件数
                - system_files: 系统文件数（将被跳过）
                - recycle_bin_warning: 是否需要回收站警告

        Example:
            >>> preview = controller.preview_clean(files)
            >>> print(f"将删除 {preview['file_count']} 个文件")
            >>> print(f"释放空间: {preview['formatted_size']}")
        """
        with self._lock:
            self._preview_files = files.copy()
            self._confirmed = False

        file_count = len(files)
        total_size = sum(f.size for f in files)

        # 分类文件
        risky_count = 0
        safe_count = 0
        system_count = 0

        for file_info in files:
            # 检查是否为系统文件
            is_safe, reason = self.security.is_safe_to_delete(file_info.path)
            if not is_safe:
                if "system" in reason.lower() or "protected" in reason.lower():
                    system_count += 1
                continue

            # 根据扩展名判断风险级别（简化版）
            if file_info.file_extension in ['.tmp', '.cache', '.temp']:
                safe_count += 1
            else:
                risky_count += 1

        # 检查回收站容量
        recycle_bin_warning = total_size > self.RECYCLE_BIN_THRESHOLD

        preview_info = {
            "file_count": file_count,
            "total_size": total_size,
            "formatted_size": self._format_size(total_size),
            "safe_files": safe_count,
            "risky_files": risky_count,
            "system_files": system_count,
            "recycle_bin_warning": recycle_bin_warning,
            "recycle_bin_usage": f"{total_size / self.RECYCLE_BIN_THRESHOLD * 100:.1f}%"
        }

        logger.info(
            f"Preview: {file_count} files, {preview_info['formatted_size'],}, "
            f"{risky_count} risky, {system_count} system"
        )

        return preview_info

    def confirm_clean(self) -> bool:
        """
        确认清理操作（第一重确认）

        用户在预览后确认要进行清理。这是第一重确认。

        Returns:
            bool: 确认成功返回 True

        Example:
            >>> controller.confirm_clean()
            >>> # 用户已经确认，可以开始清理
        """
        with self._lock:
            self._confirmed = True
            logger.info("User confirmed cleanup operation")
        return True

    def start_clean(
        self,
        files: List[FileInfo],
        require_confirmation: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        启动清理任务

        在后台线程中执行清理，支持双重确认机制。

        Args:
            files: 要清理的文件列表
            require_confirmation: 是否需要用户确认（默认 True）
            progress_callback: 进度回调函数，接收 (当前索引, 总数) 参数

        Returns:
            bool: 成功启动返回 True，条件不满足返回 False

        Example:
            >>> files = controller.get_matched_files("L1_SAFE")
            >>> if controller.start_clean(files):
            ...     print("清理已启动")
        """
        # 检查系统状态
        if not self.state_manager.is_idle():
            logger.warning(
                f"Cannot start clean in current state: {self.state_manager.current_state.value}"
            )
            return False

        if not files:
            logger.warning("No files to clean")
            return False

        # 双重确认检查
        if require_confirmation:
            with self._lock:
                if not self._confirmed:
                    logger.warning("Cleanup not confirmed by user")
                    return False

        # 清空之前的结果
        self._complete_event.clear()
        self._result = None

        try:
            # 转换到清理状态
            self.state_manager.transition_to(SystemState.CLEANING)

            # 启动后台清理线程
            self._clean_thread = threading.Thread(
                target=self._clean_worker,
                args=(files, progress_callback),
                name="CleanWorker",
                daemon=True
            )
            self._clean_thread.start()

            logger.info(f"Clean started for {len(files)} files")
            return True

        except Exception as e:
            logger.error(f"Failed to start clean: {e}", exc_info=True)
            self.state_manager.transition_to(SystemState.IDLE)
            return False

    def _clean_worker(
        self,
        files: List[FileInfo],
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> None:
        """
        清理工作线程

        在后台执行清理任务，处理结果并发布事件。

        Args:
            files: 要清理的文件列表
            progress_callback: 进度回调函数
        """
        try:
            logger.info(f"Clean worker started: {len(files)} files")

            # 执行清理
            result = self.cleaner.clean(files, progress_callback)

            # 保存结果
            with self._lock:
                self._result = result

            # 转换状态
            self.state_manager.transition_to(SystemState.IDLE)
            self._complete_event.set()

            # 生成报告
            report = self._generate_report(result)

            logger.info(
                f"Clean completed: {result.files_deleted} files deleted, "
                f"{self._format_size(result.total_size)} freed, "
                f"{result.duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error in clean worker: {e}", exc_info=True)
            self.state_manager.transition_to(SystemState.IDLE)
            self._complete_event.set()

            # 生成失败报告
            self._result = CleanResult(success=False, errors=[str(e)])

    def cancel_clean(self) -> bool:
        """
        取消清理任务

        请求取消当前正在执行的清理操作。

        Returns:
            bool: 成功请求取消返回 True，没有正在进行的清理返回 False

        Example:
            >>> controller.start_clean(files)
            >>> # ... 用户点击取消按钮
            >>> controller.cancel_clean()
        """
        if not self.state_manager.is_cleaning():
            logger.warning("No clean in progress to cancel")
            return False

        try:
            # 请求取消
            self.state_manager.request_cancel()
            self.cleaner.cancel()

            logger.info("Clean cancellation requested")
            return True

        except Exception as e:
            logger.error(f"Error cancelling clean: {e}", exc_info=True)
            return False

    def get_result(self) -> Optional[CleanResult]:
        """
        获取清理结果

        Returns:
            Optional[CleanResult]: 清理结果对象，如果未完成返回 None

        Example:
            >>> result = controller.get_result()
            >>> if result and result.success:
            ...     print(f"成功删除 {result.files_deleted} 个文件")
        """
        with self._lock:
            return self._result

    def get_report(self) -> Optional[Dict[str, Any]]:
        """
        获取清理报告

        Returns:
            Optional[Dict[str, Any]]: 清理报告字典，如果未完成返回 None

        Example:
            >>> report = controller.get_report()
            >>> if report:
            ...     print(f"释放空间: {report['freed_space']}")
        """
        with self._lock:
            if self._result is None:
                return None
            return self._generate_report(self._result)

    def _generate_report(self, result: CleanResult) -> Dict[str, Any]:
        """
        生成清理报告

        Args:
            result: 清理结果对象

        Returns:
            Dict[str, Any]: 清理报告字典
        """
        return {
            "success": result.success,
            "files_deleted": result.files_deleted,
            "skipped": result.skipped,
            "freed_space": result.total_size,
            "formatted_size": self._format_size(result.total_size),
            "duration": result.duration,
            "error_count": len(result.errors),
            "errors": result.errors.copy(),
            "timestamp": time.time()
        }

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待清理完成

        阻塞当前线程直到清理完成或超时。

        Args:
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            bool: 清理完成返回 True，超时返回 False

        Example:
            >>> controller.start_clean(files)
            >>> if controller.wait_for_completion(timeout=60):
            ...     print("清理完成")
        """
        return self._complete_event.wait(timeout=timeout)

    def is_cleaning(self) -> bool:
        """
        检查是否正在清理

        Returns:
            bool: 正在清理返回 True，否则返回 False
        """
        return self.state_manager.is_cleaning()

    def is_confirmed(self) -> bool:
        """
        检查是否已确认

        Returns:
            bool: 已确认返回 True，否则返回 False
        """
        with self._lock:
            return self._confirmed

    def reset_confirmation(self) -> None:
        """
        重置确认状态

        在取消清理或完成后，允许重新开始清理流程。
        """
        with self._lock:
            self._confirmed = False
            self._preview_files.clear()
        logger.debug("Confirmation state reset")

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


def test_clean_controller():
    """
    CleanController Test Function

    Tests basic functionality including preview, confirmation and cleanup execution.
    """
    import tempfile

    print("=" * 60)
    print("CleanController Test")
    print("=" * 60)

    # Test 1: Controller initialization
    print("\n[Test 1] Controller initialization")
    controller = CleanController()
    assert controller.state_manager.is_idle(), "Initial state should be IDLE"
    print("  [OK] Controller initialized")

    # Test 2: Preview cleanup
    print("\n[Test 2] Preview cleanup")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test files
        test_files = []
        for i in range(10):
            file_path = test_dir / f"test_{i}.tmp"
            file_path.write_text(f"Test content {i} " * 100)
            test_files.append(FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            ))

        preview = controller.preview_clean(test_files)
        print(f"  [OK] Preview: {preview['file_count']} files")
        print(f"  [OK] Size: {preview['formatted_size']}")
        print(f"  [OK] Safe: {preview['safe_files']}, Risky: {preview['risky_files']}")

        assert preview['file_count'] == len(test_files), "File count mismatch"

    # Test 3: Confirmation mechanism
    print("\n[Test 3] Confirmation mechanism")
    assert not controller.is_confirmed(), "Should not be confirmed initially"
    controller.confirm_clean()
    assert controller.is_confirmed(), "Should be confirmed after confirm_clean()"
    print("  [OK] Confirmation mechanism works")

    # Test 4: Execute cleanup
    print("\n[Test 4] Execute cleanup")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test files
        test_files = []
        for i in range(5):
            file_path = test_dir / f"clean_{i}.tmp"
            file_path.write_text(f"Content {i}")
            test_files.append(FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            ))

        # Reset and confirm
        controller.reset_confirmation()
        controller.confirm_clean()

        # Start cleanup
        assert controller.start_clean(test_files), "Cleanup should start"
        print("  [OK] Cleanup started")

        # Wait for completion
        assert controller.wait_for_completion(timeout=10), "Cleanup should complete"
        print("  [OK] Cleanup completed")

        # Get result
        result = controller.get_result()
        assert result is not None, "Should have result"
        assert result.success, "Cleanup should succeed"
        print(f"  [OK] Deleted: {result.files_deleted} files")
        print(f"  [OK] Freed: {result.formatted_size}")

    # Test 5: Get report
    print("\n[Test 5] Get report")
    report = controller.get_report()
    assert report is not None, "Should have report"
    print(f"  [OK] Report: {report['files_deleted']} files, {report['formatted_size']}")

    # Test 6: Cancellation
    print("\n[Test 6] Cancellation")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create many files
        test_files = []
        for i in range(50):
            file_path = test_dir / f"cancel_{i}.tmp"
            file_path.write_text(f"Content {i}")
            test_files.append(FileInfo(
                path=file_path,
                size=file_path.stat().st_size,
                is_dir=False,
                modified_time=file_path.stat().st_mtime
            ))

        controller.reset_confirmation()
        controller.confirm_clean()

        assert controller.start_clean(test_files), "Cleanup should start"

        # Cancel immediately
        time.sleep(0.05)
        assert controller.cancel_clean(), "Cancel should succeed"
        print("  [OK] Cleanup cancelled")

    print("\n" + "=" * 60)
    print("[OK] All CleanController tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_clean_controller()
