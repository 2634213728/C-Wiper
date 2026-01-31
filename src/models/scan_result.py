"""
Scan Result Models - 扫描结果数据模型

本模块定义扫描过程中使用的所有数据类，包括扫描目标、文件信息和扫描结果。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ScanTarget:
    """
    扫描目标数据类

    定义一个扫描目标，包含目标的基本信息和扫描配置。

    Attributes:
        id: 扫描目标的唯一标识符
        name: 扫描目标的显示名称
        path: 扫描目标的路径
        requires_admin: 是否需要管理员权限才能扫描，默认为 False
        description: 扫描目标的描述信息，可选
        enabled: 是否启用此扫描目标，默认为 True

    Example:
        >>> target = ScanTarget(
        ...     id="user_temp",
        ...     name="用户临时文件",
        ...     path=Path("%TEMP%"),
        ...     requires_admin=False
        ... )
    """
    id: str
    name: str
    path: Path
    requires_admin: bool = False
    description: Optional[str] = None
    enabled: bool = True

    def __post_init__(self):
        """初始化后处理，确保 path 为 Path 对象"""
        if not isinstance(self.path, Path):
            self.path = Path(self.path)
        logger.debug(f"ScanTarget created: {self.id} - {self.name}")

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "requires_admin": self.requires_admin,
            "description": self.description,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScanTarget':
        """
        从字典创建实例

        Args:
            data: 包含 ScanTarget 字段的字典

        Returns:
            ScanTarget: 新的 ScanTarget 实例
        """
        return cls(
            id=data["id"],
            name=data["name"],
            path=Path(data["path"]),
            requires_admin=data.get("requires_admin", False),
            description=data.get("description"),
            enabled=data.get("enabled", True)
        )


@dataclass
class FileInfo:
    """
    文件信息数据类

    封装单个文件的详细信息，用于扫描结果。

    Attributes:
        path: 文件路径
        size: 文件大小（字节）
        is_dir: 是否为目录
        modified_time: 文件修改时间（时间戳）
        created_time: 文件创建时间（时间戳），可选
        file_extension: 文件扩展名（包含点号，如 ".txt"）
        is_hidden: 是否为隐藏文件
        is_readonly: 是否为只读文件

    Example:
        >>> file_info = FileInfo(
        ...     path=Path("C:/Temp/file.txt"),
        ...     size=1024,
        ...     is_dir=False,
        ...     modified_time=1234567890.0
        ... )
    """
    path: Path
    size: int
    is_dir: bool
    modified_time: float
    created_time: Optional[float] = None
    file_extension: str = field(default="")
    is_hidden: bool = False
    is_readonly: bool = False

    def __post_init__(self):
        """初始化后处理，自动提取文件扩展名和属性"""
        if not isinstance(self.path, Path):
            self.path = Path(self.path)

        # 自动提取扩展名
        if not self.file_extension and self.path.suffix:
            self.file_extension = self.path.suffix

        # 自动检查文件属性（如果文件存在）
        if self.path.exists():
            import os
            try:
                stat = self.path.stat()
                # 检查是否为隐藏文件（Windows）
                if hasattr(os.stat, 'st_file_attributes'):
                    import stat as stat_module
                    self.is_hidden = bool(
                        stat.st_file_attributes & stat_module.FILE_ATTRIBUTE_HIDDEN
                    )
                    self.is_readonly = bool(
                        stat.st_file_attributes & stat_module.FILE_ATTRIBUTE_READONLY
                    )
                else:
                    # Unix 系统的隐藏文件（以点开头）
                    self.is_hidden = self.path.name.startswith('.')
            except Exception as e:
                logger.debug(f"Failed to get file attributes: {e}")

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典
        """
        return {
            "path": str(self.path),
            "size": self.size,
            "is_dir": self.is_dir,
            "modified_time": self.modified_time,
            "created_time": self.created_time,
            "file_extension": self.file_extension,
            "is_hidden": self.is_hidden,
            "is_readonly": self.is_readonly
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FileInfo':
        """
        从字典创建实例

        Args:
            data: 包含 FileInfo 字段的字典

        Returns:
            FileInfo: 新的 FileInfo 实例
        """
        return cls(
            path=Path(data["path"]),
            size=data["size"],
            is_dir=data["is_dir"],
            modified_time=data["modified_time"],
            created_time=data.get("created_time"),
            file_extension=data.get("file_extension", ""),
            is_hidden=data.get("is_hidden", False),
            is_readonly=data.get("is_readonly", False)
        )

    def get_modified_datetime(self) -> datetime:
        """
        获取文件修改时间的 datetime 对象

        Returns:
            datetime: 文件修改时间的 datetime 对象
        """
        return datetime.fromtimestamp(self.modified_time)

    def get_created_datetime(self) -> Optional[datetime]:
        """
        获取文件创建时间的 datetime 对象

        Returns:
            Optional[datetime]: 文件创建时间的 datetime 对象，如果没有则返回 None
        """
        if self.created_time:
            return datetime.fromtimestamp(self.created_time)
        return None

    def format_size(self) -> str:
        """
        格式化文件大小为人类可读格式

        Returns:
            str: 格式化后的大小字符串（如 "1.5 MB"）

        Example:
            >>> file_info = FileInfo(Path("test.txt"), 1536, False, 0.0)
            >>> file_info.format_size()
            '1.50 KB'
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.size < 1024.0:
                return f"{self.size:.2f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.2f} PB"


@dataclass
class ScanResult:
    """
    扫描结果数据类

    封装单个扫描目标的完整结果，包括文件列表、统计信息和缓存状态。

    Attributes:
        target: 扫描目标
        files: 扫描到的文件信息列表
        total_size: 总大小（字节）
        file_count: 文件数量
        dir_count: 目录数量
        from_cache: 结果是否来自缓存，默认为 False
        scan_duration: 扫描耗时（秒），可选
        error_message: 错误信息，如果扫描失败则包含错误描述

    Example:
        >>> result = ScanResult(
        ...     target=scan_target,
        ...     files=[file_info1, file_info2],
        ...     total_size=2048,
        ...     file_count=2,
        ...     dir_count=0
        ... )
    """
    target: ScanTarget
    files: List[FileInfo]
    total_size: int
    file_count: int
    dir_count: int = 0
    from_cache: bool = False
    scan_duration: Optional[float] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """初始化后处理，记录日志"""
        logger.debug(
            f"ScanResult created for {self.target.id}: "
            f"{self.file_count} files, {self.format_total_size()}"
        )

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典
        """
        return {
            "target": self.target.to_dict(),
            "files": [f.to_dict() for f in self.files],
            "total_size": self.total_size,
            "file_count": self.file_count,
            "dir_count": self.dir_count,
            "from_cache": self.from_cache,
            "scan_duration": self.scan_duration,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScanResult':
        """
        从字典创建实例

        Args:
            data: 包含 ScanResult 字段的字典

        Returns:
            ScanResult: 新的 ScanResult 实例
        """
        return cls(
            target=ScanTarget.from_dict(data["target"]),
            files=[FileInfo.from_dict(f) for f in data["files"]],
            total_size=data["total_size"],
            file_count=data["file_count"],
            dir_count=data.get("dir_count", 0),
            from_cache=data.get("from_cache", False),
            scan_duration=data.get("scan_duration"),
            error_message=data.get("error_message")
        )

    def format_total_size(self) -> str:
        """
        格式化总大小为人类可读格式

        Returns:
            str: 格式化后的大小字符串
        """
        size = self.total_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def is_success(self) -> bool:
        """
        检查扫描是否成功

        Returns:
            bool: 如果扫描成功返回 True，否则返回 False
        """
        return self.error_message is None

    def get_file_by_extension(self, extension: str) -> List[FileInfo]:
        """
        按扩展名筛选文件

        Args:
            extension: 文件扩展名（如 ".txt"）

        Returns:
            List[FileInfo]: 匹配的文件列表
        """
        extension = extension.lower()
        return [f for f in self.files if f.file_extension.lower() == extension]

    def get_files_larger_than(self, size_bytes: int) -> List[FileInfo]:
        """
        筛选大于指定大小的文件

        Args:
            size_bytes: 大小阈值（字节）

        Returns:
            List[FileInfo]: 匹配的文件列表
        """
        return [f for f in self.files if f.size > size_bytes]


def test_scan_result_models():
    """
    Scan Result Models Test Function

    Tests all data classes including creation, serialization and method calls.
    """
    import tempfile
    import time

    print("=" * 60)
    print("Scan Result Models Test")
    print("=" * 60)

    # Test 1: ScanTarget
    print("\n[Test 1] ScanTarget creation")
    target = ScanTarget(
        id="test_target",
        name="Test Target",
        path=Path("C:/Temp"),
        requires_admin=False,
        description="This is a test target"
    )
    print(f"  [OK] Created target: {target.id} - {target.name}")
    print(f"  [OK] Path: {target.path}")

    # Test serialization
    target_dict = target.to_dict()
    target2 = ScanTarget.from_dict(target_dict)
    assert target.id == target2.id, "Serialization failed"
    print("  [OK] Serialization test passed")

    # Test 2: FileInfo
    print("\n[Test 2] FileInfo creation")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content for size calculation")

        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=test_file.stat().st_mtime
        )
        print(f"  [OK] File path: {file_info.path}")
        print(f"  [OK] File size: {file_info.format_size()}")
        print(f"  [OK] Extension: {file_info.file_extension}")

        # Test time conversion
        mod_datetime = file_info.get_modified_datetime()
        print(f"  [OK] Modified time: {mod_datetime}")

    # Test 3: ScanResult
    print("\n[Test 3] ScanResult creation")
    files = [
        FileInfo(path=Path("file1.txt"), size=1024, is_dir=False, modified_time=time.time()),
        FileInfo(path=Path("file2.pdf"), size=2048, is_dir=False, modified_time=time.time()),
    ]

    result = ScanResult(
        target=target,
        files=files,
        total_size=3072,
        file_count=2,
        dir_count=0,
        from_cache=False,
        scan_duration=1.5
    )
    print(f"  [OK] Scan result: {result.file_count} files")
    print(f"  [OK] Total size: {result.format_total_size()}")
    print(f"  [OK] Scan duration: {result.scan_duration} seconds")

    # Test result methods
    assert result.is_success(), "Scan should be successful"
    print("  [OK] Scan status: Success")

    # Test 4: File filtering
    print("\n[Test 4] File filtering functions")
    txt_files = result.get_file_by_extension(".txt")
    print(f"  [OK] TXT file count: {len(txt_files)}")

    large_files = result.get_files_larger_than(1500)
    print(f"  [OK] Large file count (>1500 bytes): {len(large_files)}")

    # Test 5: Error handling
    print("\n[Test 5] Error handling")
    error_result = ScanResult(
        target=target,
        files=[],
        total_size=0,
        file_count=0,
        dir_count=0,
        error_message="Permission denied"
    )
    assert not error_result.is_success(), "Should be marked as failed"
    print(f"  [OK] Error message: {error_result.error_message}")

    # Test 6: Complete serialization
    print("\n[Test 6] Complete serialization")
    result_dict = result.to_dict()
    result2 = ScanResult.from_dict(result_dict)
    assert result.file_count == result2.file_count, "Complete serialization failed"
    print("  [OK] Complete serialization test passed")

    print("\n" + "=" * 60)
    print("[OK] All Scan Result Models tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_scan_result_models()
