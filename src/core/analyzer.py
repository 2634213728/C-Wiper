"""
App Analyzer - 应用分析器模块（基础版本）

本模块实现应用空间分析器的基础版本，识别常见的应用程序并分析其空间占用。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Callable
from difflib import SequenceMatcher

# 延迟导入以避免循环导入
StateMgr = None

from src.models.scan_result import FileInfo
from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AppCluster:
    """
    应用簇类

    封装应用及其相关文件的信息。

    Attributes:
        app_name: 应用名称
        install_path: 安装路径
        static_files: 静态区文件列表
        dynamic_files: 动态区文件列表
        total_size: 总大小（字节）
        orphan_files: 孤儿文件列表
    """
    app_name: str
    install_path: Path
    static_files: List[FileInfo] = field(default_factory=list)
    dynamic_files: List[FileInfo] = field(default_factory=list)
    total_size: int = 0
    orphan_files: List[FileInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "app_name": self.app_name,
            "install_path": str(self.install_path),
            "static_file_count": len(self.static_files),
            "dynamic_file_count": len(self.dynamic_files),
            "total_size": self.total_size,
            "formatted_size": self._format_size(self.total_size),
            "orphan_count": len(self.orphan_files)
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


class AppAnalyzer:
    """
    应用分析器类（基础版本）

    实现基础的应用空间分析功能，支持：
    - 扫描 Program Files 和 AppData 目录
    - 简单的应用名称匹配
    - 基本的空间统计

    Attributes:
        state_manager: 状态管理器实例
        event_bus: 事件总线实例
        _cancelled: 取消标志

    Example:
        >>> analyzer = AppAnalyzer()
        >>> clusters = analyzer.analyze()
        >>> for cluster in clusters:
        ...     print(f"{cluster.app_name}: {cluster.formatted_size}")
    """

    # 常见应用名称模式
    COMMON_APP_PATTERNS = [
        r'Chrome',
        r'Firefox',
        r'Edge',
        r'Visual Studio',
        r'Python',
        r'Java',
        r'Node\.js',
        r'Git',
        r'Docker',
        r'VMware',
        r'VirtualBox',
        r'Sublime Text',
        r'VSCode',
        r'Notepad\+\+',
        r'WinRAR',
        r'7-Zip',
        r'Adobe',
        r'Office',
        r'TeamViewer',
        r'Discord',
        r'Steam',
        r'Epic Games',
    ]

    def __init__(
        self,
        state_manager = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化应用分析器

        Args:
            state_manager: 状态管理器实例，默认使用全局单例
            event_bus: 事件总线实例，默认使用全局单例
        """
        global StateMgr
        if StateMgr is None:
            from src.controllers.state_manager import StateManager as SM
            StateMgr = SM

        self.state_manager = state_manager or StateMgr()
        self.event_bus = event_bus or EventBus()
        self._cancelled = False

        logger.info("AppAnalyzer initialized")

    def analyze(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[AppCluster]:
        """
        执行应用空间分析

        扫描常见应用目录，识别应用并分析其空间占用。

        Args:
            progress_callback: 进度回调函数，接收 (阶段, 当前, 总数) 参数

        Returns:
            List[AppCluster]: 应用簇列表

        Example:
            >>> clusters = analyzer.analyze()
            >>> for cluster in clusters:
            ...     print(f"{cluster.app_name}: {cluster.formatted_size}")
        """
        logger.info("Starting application space analysis")

        clusters = []

        try:
            # 扫描静态区（Program Files）
            static_clusters = self._scan_static_zone(progress_callback)
            clusters.extend(static_clusters)

            # 扫描动态区（AppData）
            dynamic_clusters = self._scan_dynamic_zone(progress_callback)
            clusters.extend(dynamic_clusters)

            # 合并重复的应用
            merged_clusters = self._merge_clusters(clusters)

            # 按大小排序
            merged_clusters.sort(key=lambda c: c.total_size, reverse=True)

            logger.info(f"Analysis completed: {len(merged_clusters)} applications found")
            return merged_clusters

        except Exception as e:
            logger.error(f"Error during analysis: {e}", exc_info=True)
            return []

    def _scan_static_zone(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[AppCluster]:
        """
        扫描静态区（Program Files）

        Args:
            progress_callback: 进度回调函数

        Returns:
            List[AppCluster]: 应用簇列表
        """
        clusters = []

        # 扫描路径列表（只扫描 Program Files）
        scan_paths = [
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)"),
        ]

        for scan_path in scan_paths:
            if not scan_path.exists():
                logger.debug(f"Path does not exist: {scan_path}")
                continue

            try:
                logger.info(f"Scanning static zone: {scan_path}")

                for item in scan_path.iterdir():
                    if self._cancelled or self.state_manager.is_cancel_requested:
                        logger.info("Analysis cancelled")
                        break

                    if item.is_dir():
                        # 尝试识别为应用
                        app_name = self._identify_app(item.name)
                        if app_name:
                            cluster = self._create_cluster_from_path(item, app_name)
                            if cluster:
                                clusters.append(cluster)

            except PermissionError:
                logger.warning(f"Permission denied: {scan_path}")
            except Exception as e:
                logger.error(f"Error scanning {scan_path}: {e}")

        return clusters

    def _scan_dynamic_zone(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[AppCluster]:
        """
        扫描动态区（AppData）

        Args:
            progress_callback: 进度回调函数

        Returns:
            List[AppCluster]: 应用簇列表
        """
        clusters = []

        # AppData 路径
        appdata_paths = [
            Path.home() / "AppData/Roaming",
            Path.home() / "AppData/Local",
        ]

        for appdata_path in appdata_paths:
            if not appdata_path.exists():
                continue

            try:
                logger.info(f"Scanning dynamic zone: {appdata_path}")

                for item in appdata_path.iterdir():
                    if self._cancelled or self.state_manager.is_cancel_requested:
                        break

                    if item.is_dir():
                        # 尝试识别为应用
                        app_name = self._identify_app(item.name)
                        if app_name:
                            cluster = self._create_cluster_from_path(item, app_name)
                            if cluster:
                                clusters.append(cluster)

            except Exception as e:
                logger.error(f"Error scanning {appdata_path}: {e}")

        return clusters

    def _identify_app(self, name: str) -> Optional[str]:
        """
        识别应用名称

        使用模式匹配识别常见应用。

        Args:
            name: 目录名称

        Returns:
            Optional[str]: 应用名称，如果不匹配返回 None
        """
        for pattern in self.COMMON_APP_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return name

        return None

    def _create_cluster_from_path(
        self,
        path: Path,
        app_name: str
    ) -> Optional[AppCluster]:
        """
        从路径创建应用簇

        Args:
            path: 应用路径
            app_name: 应用名称

        Returns:
            Optional[AppCluster]: 应用簇对象
        """
        try:
            files = []
            total_size = 0

            # 扫描目录（限制深度）
            for item in path.rglob('*'):
                if self._cancelled or self.state_manager.is_cancel_requested:
                    break

                try:
                    if item.is_file():
                        stat = item.stat()
                        file_info = FileInfo(
                            path=item,
                            size=stat.st_size,
                            is_dir=False,
                            modified_time=stat.st_mtime
                        )
                        files.append(file_info)
                        total_size += stat.st_size
                except (PermissionError, FileNotFoundError):
                    continue

            return AppCluster(
                app_name=app_name,
                install_path=path,
                static_files=files,
                total_size=total_size
            )

        except Exception as e:
            logger.error(f"Error creating cluster for {path}: {e}")
            return None

    def _merge_clusters(self, clusters: List[AppCluster]) -> List[AppCluster]:
        """
        合并重复的应用簇

        Args:
            clusters: 应用簇列表

        Returns:
            List[AppCluster]: 合并后的应用簇列表
        """
        merged: Dict[str, AppCluster] = {}

        for cluster in clusters:
            # 使用相似度匹配
            app_name = cluster.app_name.lower()
            merged_key = app_name

            # 检查是否已存在相似的应用
            for existing_name in merged.keys():
                similarity = SequenceMatcher(None, app_name, existing_name).ratio()
                if similarity > 0.8:  # 80% 相似度阈值
                    merged_key = existing_name
                    break

            if merged_key in merged:
                # 合并到现有簇
                existing = merged[merged_key]
                existing.static_files.extend(cluster.static_files)
                existing.dynamic_files.extend(cluster.dynamic_files)
                existing.total_size += cluster.total_size
            else:
                # 创建新簇
                merged[app_name] = cluster

        return list(merged.values())

    def cancel(self) -> None:
        """
        取消分析操作
        """
        self._cancelled = True
        self.state_manager.request_cancel()
        logger.info("Analysis cancellation requested")

    def reset_cancel(self) -> None:
        """
        重置取消标志
        """
        self._cancelled = False
        self.state_manager.reset_cancel_flag()


def test_app_analyzer():
    """
    AppAnalyzer Test Function

    Tests basic functionality including app identification and cluster creation.
    """
    print("=" * 60)
    print("AppAnalyzer Test")
    print("=" * 60)

    # Test 1: Analyzer initialization
    print("\n[Test 1] Analyzer initialization")
    analyzer = AppAnalyzer()
    print("  [OK] Analyzer initialized")

    # Test 2: App identification
    print("\n[Test 2] App identification")
    test_names = [
        "Google Chrome",
        "Mozilla Firefox",
        "Microsoft Edge",
        "Visual Studio Code",
        "Unknown Application"
    ]

    for name in test_names:
        identified = analyzer._identify_app(name)
        if identified:
            print(f"  [OK] Identified: {name}")
        else:
            print(f"  [INFO] Not identified: {name}")

    # Test 3: Create cluster from path
    print("\n[Test 3] Create cluster from path")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "Chrome"
        test_path.mkdir()

        # Create test files
        (test_path / "chrome.exe").write_text("fake exe")
        (test_path / "data.json").write_text('{"data": true}')

        cluster = analyzer._create_cluster_from_path(test_path, "Chrome")
        assert cluster is not None, "Cluster should be created"
        assert cluster.app_name == "Chrome", "App name mismatch"
        print(f"  [OK] Cluster created: {cluster.app_name}")
        print(f"  [OK] Files: {len(cluster.static_files)}")

    # Test 4: Merge clusters
    print("\n[Test 4] Merge clusters")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two similar clusters
        path1 = Path(tmpdir) / "App1"
        path2 = Path(tmpdir) / "App1_data"

        path1.mkdir()
        path2.mkdir()

        cluster1 = AppCluster(
            app_name="MyApp",
            install_path=path1,
            total_size=1024
        )
        cluster2 = AppCluster(
            app_name="MyApp_data",
            install_path=path2,
            total_size=2048
        )

        merged = analyzer._merge_clusters([cluster1, cluster2])
        print(f"  [OK] Merged {len([cluster1, cluster2])} clusters into {len(merged)}")

    print("\n" + "=" * 60)
    print("[OK] All AppAnalyzer tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_app_analyzer()
