"""
Core Scanner - 核心扫描器模块

本模块实现高性能文件扫描器，支持生成器模式、缓存机制和进度事件通知。
所有文件扫描操作都通过此模块执行，确保性能和可扩展性。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Generator, List, Optional, Dict, Any, TYPE_CHECKING

# Type checking imports (only for type checkers, not at runtime)
if TYPE_CHECKING:
    from src.controllers.state_manager import StateManager
    from src.core.security import SecurityLayer
    from src.models.scan_result import ScanTarget, ScanResult, FileInfo
    from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileAttributes:
    """
    文件属性类

    封装文件的系统属性，用于更详细的文件信息记录。

    Attributes:
        is_hidden: 是否为隐藏文件
        is_readonly: 是否为只读文件
        is_system: 是否为系统文件
        is_archive: 是否为存档文件
    """

    def __init__(
        self,
        is_hidden: bool = False,
        is_readonly: bool = False,
        is_system: bool = False,
        is_archive: bool = False
    ):
        """
        初始化文件属性

        Args:
            is_hidden: 是否为隐藏文件
            is_readonly: 是否为只读文件
            is_system: 是否为系统文件
            is_archive: 是否为存档文件
        """
        self.is_hidden = is_hidden
        self.is_readonly = is_readonly
        self.is_system = is_system
        self.is_archive = is_archive

    def to_dict(self) -> Dict[str, bool]:
        """转换为字典格式"""
        return {
            "is_hidden": self.is_hidden,
            "is_readonly": self.is_readonly,
            "is_system": self.is_system,
            "is_archive": self.is_archive
        }

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> 'FileAttributes':
        """从字典创建实例"""
        return cls(
            is_hidden=data.get("is_hidden", False),
            is_readonly=data.get("is_readonly", False),
            is_system=data.get("is_system", False),
            is_archive=data.get("is_archive", False)
        )


class ScanError(Exception):
    """
    扫描错误类

    当扫描过程中发生错误时抛出此异常。

    Attributes:
        target: 扫描目标
        message: 错误消息
        path: 出错的路径（可选）
    """

    def __init__(self, target: ScanTarget, message: str, path: Optional[Path] = None):
        self.target = target
        self.message = message
        self.path = path
        super().__init__(f"Scan error for {target.id}: {message}")


class ScanCache:
    """
    扫描缓存类

    实现基于 JSON 的扫描结果缓存机制，避免重复扫描未变更的目录。

    Attributes:
        cache_file: 缓存文件路径
        cache: 内存中的缓存字典
        _lock: 线程锁，保护缓存操作

    Example:
        >>> cache = ScanCache(Path("scan_cache.json"))
        >>> cache.set(Path("C:/Temp"), 1024, time.time())
        >>> size, timestamp = cache.get(Path("C:/Temp"))
    """

    def __init__(self, cache_file: Path = Path("config/scan_cache.json")):
        """
        初始化扫描缓存

        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
        logger.debug(f"ScanCache initialized with {len(self.cache)} entries")

    def _load_cache(self) -> None:
        """从文件加载缓存"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded scan cache: {len(self.cache)} entries")
            else:
                # 确保目录存在
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                self.cache = {}
                logger.info("Cache file not found, starting with empty cache")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self.cache = {}

    def _save_cache(self) -> None:
        """保存缓存到文件"""
        try:
            # 确保目录存在
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved scan cache: {len(self.cache)} entries")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, path: Path) -> Optional[tuple[int, float]]:
        """
        从缓存获取路径的大小和时间戳

        Args:
            path: 文件或目录路径

        Returns:
            Optional[tuple[int, float]]: (大小, 时间戳) 元组，如果缓存不存在返回 None
        """
        path_str = str(path.resolve())
        if path_str in self.cache:
            entry = self.cache[path_str]
            return entry.get('size', 0), entry.get('timestamp', 0)
        return None

    def set(self, path: Path, size: int, timestamp: float) -> None:
        """
        设置缓存

        Args:
            path: 文件或目录路径
            size: 大小（字节）
            timestamp: 时间戳
        """
        path_str = str(path.resolve())
        self.cache[path_str] = {
            'size': size,
            'timestamp': timestamp
        }
        # 异步保存（避免频繁IO）
        if len(self.cache) % 100 == 0:
            self._save_cache()

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self._save_cache()
        logger.info("Scan cache cleared")

    def remove(self, path: Path) -> bool:
        """
        移除指定路径的缓存

        Args:
            path: 文件或目录路径

        Returns:
            bool: 成功移除返回 True，缓存不存在返回 False
        """
        path_str = str(path.resolve())
        if path_str in self.cache:
            del self.cache[path_str]
            self._save_cache()
            return True
        return False


class CoreScanner:
    """
    核心扫描器类

    实现高性能文件扫描功能，支持生成器模式、进度通知和缓存机制。
    使用 pathlib 进行跨平台文件操作，集成安全检查和事件通知。

    Attributes:
        state_manager: 状态管理器实例
        event_bus: 事件总线实例
        security: 安全层实例
        cache: 扫描缓存实例
        _cancelled: 取消标志

    Example:
        >>> scanner = CoreScanner()
        >>> targets = [ScanTarget(id="temp", name="临时文件", path=Path("C:/Temp"))]
        >>> for result in scanner.scan(targets):
        ...     print(f"扫描完成: {result.file_count} 个文件")
    """

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        event_bus: Optional[EventBus] = None,
        security: Optional[SecurityLayer] = None
    ):
        """
        初始化核心扫描器

        Args:
            state_manager: 状态管理器实例，默认使用全局单例
            event_bus: 事件总线实例，默认使用全局单例
            security: 安全层实例，默认使用 SecurityLayer
        """
        # Lazy imports to avoid circular dependency
        from src.controllers.state_manager import StateManager
        from src.utils.event_bus import EventBus
        from src.core.security import SecurityLayer

        self.state_manager = state_manager or StateManager()
        self.event_bus = event_bus or EventBus()
        self.security = security or SecurityLayer()
        self.cache = ScanCache()
        self._cancelled = False

        logger.info("CoreScanner initialized")

    def scan(
        self,
        targets: List[ScanTarget]
    ) -> Generator[ScanResult, None, None]:
        """
        扫描多个目标（生成器模式）

        逐个扫描目标，每完成一个目标就生成一个 ScanResult。
        支持取消操作，会定期检查取消标志。

        Args:
            targets: 扫描目标列表

        Yields:
            ScanResult: 扫描结果对象

        Example:
            >>> scanner = CoreScanner()
            >>> targets = [target1, target2, target3]
            >>> for result in scanner.scan(targets):
            ...     print(f"完成: {result.target.name} - {result.file_count} 个文件")
        """
        # Lazy imports
        from src.utils.event_bus import Event, EventType

        if not targets:
            logger.warning("No targets to scan")
            return

        total_targets = len(targets)
        logger.info(f"Starting scan of {total_targets} targets")

        # 发布扫描开始事件
        self.event_bus.publish(Event(
            type=EventType.SCAN_STARTED,
            data={
                "target_count": total_targets,
                "targets": [t.to_dict() for t in targets]
            }
        ))

        for index, target in enumerate(targets, 1):
            # 检查取消请求
            if self.state_manager.is_cancel_requested or self._cancelled:
                logger.info("Scan cancelled by user request")
                self.event_bus.publish(Event(
                    type=EventType.SCAN_FAILED,
                    data={"reason": "Cancelled by user", "completed": index - 1}
                ))
                break

            # 检查目标是否启用
            if not target.enabled:
                logger.debug(f"Target {target.id} is disabled, skipping")
                continue

            # 检查目标路径是否存在
            if not target.path.exists():
                logger.warning(f"Target path does not exist: {target.path}")
                error_result = ScanResult(
                    target=target,
                    files=[],
                    total_size=0,
                    file_count=0,
                    dir_count=0,
                    error_message=f"Path does not exist: {target.path}"
                )
                yield error_result
                continue

            try:
                # 扫描单个目标
                result = self.scan_single_target(target)
                yield result

                # 发布进度事件
                self.event_bus.publish(Event(
                    type=EventType.SCAN_PROGRESS,
                    data={
                        "current": index,
                        "total": total_targets,
                        "target_id": target.id,
                        "file_count": result.file_count,
                        "total_size": result.total_size
                    }
                ))

            except Exception as e:
                logger.error(f"Error scanning target {target.id}: {e}", exc_info=True)
                error_result = ScanResult(
                    target=target,
                    files=[],
                    total_size=0,
                    file_count=0,
                    dir_count=0,
                    error_message=str(e)
                )
                yield error_result

        # 发布扫描完成事件
        self.event_bus.publish(Event(
            type=EventType.SCAN_COMPLETED,
            data={"targets_scanned": index}
        ))
        logger.info(f"Scan completed: {index} targets")

    def scan_single_target(self, target: ScanTarget) -> ScanResult:
        """
        扫描单个目标

        Args:
            target: 扫描目标

        Returns:
            ScanResult: 扫描结果对象

        Raises:
            ScanError: 扫描过程中发生错误
        """
        # Lazy imports
        from src.models.scan_result import ScanResult

        start_time = time.time()
        files = []
        total_size = 0
        file_count = 0
        dir_count = 0

        logger.info(f"Scanning target: {target.id} ({target.path})")

        try:
            # 检查路径是否存在
            if not target.path.exists():
                raise FileNotFoundError(f"Path does not exist: {target.path}")

            if target.path.is_file():
                # 单个文件
                file_info = self._scan_file(target.path)
                if file_info:
                    files.append(file_info)
                    file_count = 1
                    total_size = file_info.size
            elif target.path.is_dir():
                # 目录
                for file_info in self._scan_directory(target.path):
                    files.append(file_info)
                    total_size += file_info.size
                    if file_info.is_dir:
                        dir_count += 1
                    else:
                        file_count += 1

            scan_duration = time.time() - start_time
            logger.info(
                f"Scan completed for {target.id}: "
                f"{file_count} files, {dir_count} dirs, "
                f"{self._format_size(total_size)}, {scan_duration:.2f}s"
            )

            return ScanResult(
                target=target,
                files=files,
                total_size=total_size,
                file_count=file_count,
                dir_count=dir_count,
                from_cache=False,
                scan_duration=scan_duration
            )

        except FileNotFoundError as e:
            logger.error(f"Path not found for target {target.id}: {e}")
            return ScanResult(
                target=target,
                files=[],
                total_size=0,
                file_count=0,
                dir_count=0,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to scan target {target.id}: {e}")
            return ScanResult(
                target=target,
                files=[],
                total_size=0,
                file_count=0,
                dir_count=0,
                error_message=str(e)
            )

    def _scan_directory(self, path: Path) -> Generator[FileInfo, None, None]:
        """
        扫描目录（生成器模式）

        使用 pathlib.rglob 递归扫描目录，生成文件信息。

        Args:
            path: 目录路径

        Yields:
            FileInfo: 文件信息对象

        Raises:
            PermissionError: 无权限访问目录
        """
        # Lazy imports
        from src.models.scan_result import FileInfo

        try:
            # 使用 rglob 递归遍历
            for item in path.rglob('*'):
                # 检查取消请求
                if self.state_manager.is_cancel_requested or self._cancelled:
                    logger.debug("Scan cancelled during directory traversal")
                    break

                try:
                    # 跳过符号链接（避免循环）
                    if item.is_symlink():
                        logger.debug(f"Skipping symlink: {item}")
                        continue

                    # 路径安全检查
                    is_safe, reason = self.security.is_safe_to_delete(item)
                    if not is_safe and "Protected path" in reason:
                        logger.debug(f"Skipping protected path: {item}")
                        continue

                    # 生成文件信息
                    file_info = self._scan_file(item)
                    if file_info:
                        yield file_info

                except PermissionError as e:
                    logger.warning(f"Permission denied: {item}")
                    continue
                except Exception as e:
                    logger.error(f"Error scanning {item}: {e}")
                    continue

        except PermissionError as e:
            logger.error(f"Permission denied for directory {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error scanning directory {path}: {e}")
            raise

    def _scan_file(self, path: Path) -> Optional[FileInfo]:
        """
        扫描单个文件

        Args:
            path: 文件路径

        Returns:
            Optional[FileInfo]: 文件信息对象，如果扫描失败返回 None
        """
        # Lazy imports
        from src.models.scan_result import FileInfo

        try:
            stat = path.stat()
            is_dir = path.is_dir()

            file_info = FileInfo(
                path=path,
                size=stat.st_size,
                is_dir=is_dir,
                modified_time=stat.st_mtime,
                created_time=stat.st_ctime,
                file_extension=path.suffix,
                is_hidden=self._is_hidden(path),
                is_readonly=not os.access(path, os.W_OK)
            )

            # 更新缓存
            if not is_dir:
                self.cache.set(path, stat.st_size, time.time())

            return file_info

        except Exception as e:
            logger.error(f"Error scanning file {path}: {e}")
            return None

    def _is_hidden(self, path: Path) -> bool:
        """
        检查文件是否为隐藏文件

        Args:
            path: 文件路径

        Returns:
            bool: 如果是隐藏文件返回 True
        """
        try:
            # Windows: 检查 FILE_ATTRIBUTE_HIDDEN
            if os.name == 'nt':
                import stat
                result = os.stat(str(path))
                hidden = bool(result.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
                return hidden
            else:
                # Unix: 检查文件名是否以点开头
                return path.name.startswith('.')
        except Exception:
            return False

    def cancel(self) -> None:
        """
        取消扫描

        设置取消标志，扫描器会在下次检查时停止扫描。
        """
        self._cancelled = True
        self.state_manager.request_cancel()
        logger.info("Scan cancellation requested")

    def reset_cancel(self) -> None:
        """
        重置取消标志

        允许重新开始扫描。
        """
        self._cancelled = False
        self.state_manager.reset_cancel_flag()
        logger.debug("Scan cancel flag reset")

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


def test_scanner():
    """
    CoreScanner Test Function

    Tests basic functionality including single target scanning, multiple targets and cancellation.
    """
    # Lazy imports
    from src.models.scan_result import ScanTarget

    import tempfile

    print("=" * 60)
    print("CoreScanner Test")
    print("=" * 60)

    # Test 1: Create test directory structure
    print("\n[Test 1] Creating test directory structure")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test files
        (test_dir / "file1.txt").write_text("Test content 1")
        (test_dir / "file2.log").write_text("Test content 2")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "file3.tmp").write_text("Test content 3")

        print(f"  [OK] Created test directory: {test_dir}")

        # Test 2: Single target scanning
        print("\n[Test 2] Single target scanning")
        scanner = CoreScanner()

        target = ScanTarget(
            id="test_target",
            name="Test Target",
            path=test_dir,
            requires_admin=False,
            description="Test target for scanner"
        )

        result = scanner.scan_single_target(target)
        print(f"  [OK] Scanned {result.file_count} files")
        print(f"  [OK] Total size: {result.format_total_size()}")
        print(f"  [OK] Scan duration: {result.scan_duration:.3f}s")

        assert result.file_count == 3, f"Expected 3 files, got {result.file_count}"
        assert result.is_success(), "Scan should be successful"

        # Test 3: Multiple targets with generator
        print("\n[Test 3] Multiple targets scanning")
        targets = [
            ScanTarget(id="target1", name="Target 1", path=test_dir),
            ScanTarget(id="target2", name="Target 2", path=test_dir / "subdir")
        ]

        results = list(scanner.scan(targets))
        print(f"  [OK] Scanned {len(results)} targets")
        assert len(results) == 2, "Should have 2 results"

        # Test 4: Scan cache
        print("\n[Test 4] Scan cache functionality")
        cache = ScanCache()

        test_path = test_dir / "file1.txt"
        cache.set(test_path, 100, time.time())

        cached = cache.get(test_path)
        assert cached is not None, "Cache should return value"
        assert cached[0] == 100, "Cached size should be 100"
        print("  [OK] Cache set and get work")

        cache.remove(test_path)
        assert cache.get(test_path) is None, "Cache should be empty after removal"
        print("  [OK] Cache removal works")

        # Test 5: Error handling
        print("\n[Test 5] Error handling for non-existent paths")
        invalid_target = ScanTarget(
            id="invalid",
            name="Invalid Target",
            path=Path("C:/NonExistentPath12345")
        )

        result = scanner.scan_single_target(invalid_target)
        assert not result.is_success(), "Scan should fail for non-existent path"
        print(f"  [OK] Error message: {result.error_message}")

    # Test 6: File attributes
    print("\n[Test 6] File attributes")
    attrs = FileAttributes(
        is_hidden=True,
        is_readonly=False,
        is_system=False,
        is_archive=True
    )
    attrs_dict = attrs.to_dict()
    assert attrs_dict["is_hidden"] == True, "Attribute serialization failed"
    print("  [OK] File attributes work correctly")

    print("\n" + "=" * 60)
    print("[OK] All CoreScanner tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_scanner()
