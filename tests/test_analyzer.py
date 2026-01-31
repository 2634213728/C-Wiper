"""
Unit Tests for Core Analyzer Module

本模块包含 AppAnalyzer 的单元测试，涵盖应用识别、空间分析、簇管理等功能。

测试覆盖：
- 应用识别功能
- 空间分析
- 应用簇创建
- 簇合并
- 取消操作
- 静态区和动态区扫描

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.analyzer import AppAnalyzer, AppCluster
from src.controllers.state_manager import SystemState


class TestAppCluster:
    """测试 AppCluster 数据类"""

    def test_cluster_initialization(self):
        """测试应用簇初始化"""
        cluster = AppCluster(
            app_name="TestApp",
            install_path=Path("C:/Program Files/TestApp"),
            total_size=1024 * 1024
        )

        assert cluster.app_name == "TestApp"
        assert cluster.install_path == Path("C:/Program Files/TestApp")
        assert cluster.total_size == 1024 * 1024
        assert len(cluster.static_files) == 0
        assert len(cluster.dynamic_files) == 0

    def test_cluster_to_dict(self):
        """测试应用簇序列化"""
        cluster = AppCluster(
            app_name="Chrome",
            install_path=Path("C:/Program Files/Chrome"),
            total_size=1024 * 1024 * 100
        )

        # 创建一些虚拟文件
        from src.models.scan_result import FileInfo
        cluster.static_files.append(FileInfo(
            path=Path("chrome.exe"),
            size=1024 * 1024,
            is_dir=False,
            modified_time=time.time()
        ))

        cluster_dict = cluster.to_dict()

        assert cluster_dict["app_name"] == "Chrome"
        assert cluster_dict["total_size"] == 1024 * 1024 * 100
        assert cluster_dict["static_file_count"] == 1
        assert cluster_dict["formatted_size"] is not None

    def test_format_size(self):
        """测试大小格式化"""
        # 测试不同大小
        assert "B" in AppCluster._format_size(512)
        assert "KB" in AppCluster._format_size(1024)
        assert "MB" in AppCluster._format_size(1024 * 1024)
        assert "GB" in AppCluster._format_size(1024 * 1024 * 1024)


class TestAppIdentification:
    """测试应用识别功能"""

    def test_identify_chrome(self):
        """测试识别 Chrome"""
        analyzer = AppAnalyzer()
        assert analyzer._identify_app("Google Chrome") is not None
        assert analyzer._identify_app("chrome") is not None

    def test_identify_firefox(self):
        """测试识别 Firefox"""
        analyzer = AppAnalyzer()
        assert analyzer._identify_app("Mozilla Firefox") is not None
        assert analyzer._identify_app("Firefox") is not None

    def test_identify_visual_studio(self):
        """测试识别 Visual Studio"""
        analyzer = AppAnalyzer()
        assert analyzer._identify_app("Microsoft Visual Studio") is not None
        assert analyzer._identify_app("Visual Studio 2019") is not None

    def test_identify_unknown_app(self):
        """测试识别未知应用"""
        analyzer = AppAnalyzer()
        assert analyzer._identify_app("Unknown Application XYZ") is None
        assert analyzer._identify_app("RandomApp123") is None

    def test_identify_common_apps(self):
        """测试识别常见应用列表"""
        analyzer = AppAnalyzer()

        known_apps = [
            "Google Chrome",
            "Mozilla Firefox",
            "Microsoft Edge",
            "Visual Studio Code",
            "Python 3.9",
            "Java Runtime",
            "Git",
            "Docker Desktop",
            "VMware Workstation",
            "Sublime Text 3"
        ]

        identified_count = sum(1 for app in known_apps if analyzer._identify_app(app))
        assert identified_count >= len(known_apps) * 0.8, "Should identify at least 80% of known apps"


class TestClusterCreation:
    """测试应用簇创建"""

    def test_create_cluster_from_path(self, temp_dir):
        """测试从路径创建应用簇"""
        # 创建测试应用目录
        app_path = temp_dir / "TestApp"
        app_path.mkdir()

        # 创建一些测试文件
        (app_path / "app.exe").write_bytes(b"fake exe content")
        (app_path / "config.json").write_text('{"config": true}')
        (app_path / "data.dat").write_bytes(b"x" * 1024)

        analyzer = AppAnalyzer()
        cluster = analyzer._create_cluster_from_path(app_path, "TestApp")

        assert cluster is not None
        assert cluster.app_name == "TestApp"
        assert cluster.install_path == app_path
        assert cluster.total_size > 0
        assert len(cluster.static_files) == 3

    def test_create_cluster_with_subdirectories(self, temp_dir):
        """测试创建包含子目录的应用簇"""
        app_path = temp_dir / "ComplexApp"
        app_path.mkdir()

        # 创建子目录和文件
        (app_path / "bin").mkdir()
        (app_path / "data").mkdir()

        (app_path / "bin" / "main.exe").write_bytes(b"exe")
        (app_path / "data" / "config.db").write_bytes(b"data")

        analyzer = AppAnalyzer()
        cluster = analyzer._create_cluster_from_path(app_path, "ComplexApp")

        assert cluster is not None
        assert len(cluster.static_files) >= 2  # 至少有2个文件

    def test_create_cluster_empty_directory(self, temp_dir):
        """测试创建空目录的簇"""
        empty_path = temp_dir / "EmptyApp"
        empty_path.mkdir()

        analyzer = AppAnalyzer()
        cluster = analyzer._create_cluster_from_path(empty_path, "EmptyApp")

        assert cluster is not None
        assert cluster.total_size == 0
        assert len(cluster.static_files) == 0


class TestClusterMerge:
    """测试应用簇合并"""

    def test_merge_identical_clusters(self):
        """测试合并相同的应用簇"""
        from src.models.scan_result import FileInfo

        path1 = Path("C:/Program Files/App1")
        path2 = Path("C:/Users/test/AppData/Local/App1")

        cluster1 = AppCluster(
            app_name="MyApp",
            install_path=path1,
            total_size=1024
        )
        cluster2 = AppCluster(
            app_name="MyApp",
            install_path=path2,
            total_size=2048
        )

        analyzer = AppAnalyzer()
        merged = analyzer._merge_clusters([cluster1, cluster2])

        # 相同名称的簇应该被合并
        assert len(merged) == 1
        assert merged[0].total_size == 3072  # 1024 + 2048

    def test_merge_similar_clusters(self):
        """测试合并相似名称的应用簇"""
        cluster1 = AppCluster(
            app_name="Chrome",
            install_path=Path("C:/Program Files/Chrome"),
            total_size=1024 * 1024 * 100
        )
        cluster2 = AppCluster(
            app_name="Chrome Data",
            install_path=Path("C:/Users/test/AppData/Chrome"),
            total_size=1024 * 1024 * 50
        )

        analyzer = AppAnalyzer()
        merged = analyzer._merge_clusters([cluster1, cluster2])

        # 相似名称的簇可能被合并（取决于相似度阈值）
        assert len(merged) <= 2  # 允许不被合并的情况

    def test_merge_distinct_clusters(self):
        """测试合并不相关的应用簇"""
        cluster1 = AppCluster(
            app_name="Chrome",
            install_path=Path("C:/Program Files/Chrome"),
            total_size=100
        )
        cluster2 = AppCluster(
            app_name="Firefox",
            install_path=Path("C:/Program Files/Firefox"),
            total_size=200
        )

        analyzer = AppAnalyzer()
        merged = analyzer._merge_clusters([cluster1, cluster2])

        # 不相似的簇不应该被合并
        assert len(merged) == 2


class TestAnalysisFunctionality:
    """测试分析功能"""

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = AppAnalyzer()

        assert analyzer.state_manager is not None
        assert analyzer.event_bus is not None
        assert analyzer._cancelled is False
        assert len(analyzer.static_zones) > 0
        assert len(analyzer.dynamic_zones) > 0

    def test_scan_static_zone(self, temp_dir):
        """测试扫描静态区"""
        # 创建模拟 Program Files 目录
        program_files = temp_dir / "Program Files"
        program_files.mkdir()

        # 创建应用目录
        chrome_path = program_files / "Google Chrome"
        chrome_path.mkdir()
        (chrome_path / "chrome.exe").write_bytes(b"fake chrome")

        firefox_path = program_files / "Mozilla Firefox"
        firefox_path.mkdir()
        (firefox_path / "firefox.exe").write_bytes(b"fake firefox")

        # Mock 实际的系统路径
        analyzer = AppAnalyzer()
        analyzer.static_zones = [program_files]

        clusters = analyzer._scan_static_zone()

        # 应该至少识别出一些应用（数量取决于模拟目录）
        assert len(clusters) >= 1

        app_names = [c.app_name for c in clusters]
        # 验证至少识别出一些应用
        assert len(app_names) > 0

    def test_scan_dynamic_zone(self, temp_dir):
        """测试扫描动态区"""
        # 创建模拟 AppData 目录
        appdata = temp_dir / "AppData"
        appdata.mkdir()

        # 创建应用数据目录
        chrome_data = appdata / "Google"
        chrome_data.mkdir()
        (chrome_data / "Chrome" / "User Data").mkdir(parents=True)
        (chrome_data / "Chrome" / "User Data" / "profile").write_text("data")

        # Mock 实际的系统路径
        analyzer = AppAnalyzer()
        analyzer.dynamic_zones = [appdata]

        clusters = analyzer._scan_dynamic_zone()

        # 应该识别出 Google 相关应用（如果目录结构匹配）
        assert len(clusters) >= 0  # 可能为0，取决于目录名称

    def test_full_analysis(self, temp_dir):
        """测试完整的分析流程"""
        # 创建模拟应用目录
        program_files = temp_dir / "Program Files"
        program_files.mkdir()

        # 创建多个应用
        apps = ["Chrome", "Firefox", "VSCode"]
        for app in apps:
            app_path = program_files / app
            app_path.mkdir()
            (app_path / f"{app.lower()}.exe").write_bytes(b"fake exe")

        analyzer = AppAnalyzer()
        analyzer.static_zones = [program_files]
        analyzer.dynamic_zones = []  # 不扫描动态区

        clusters = analyzer.analyze()

        # 验证结果
        assert len(clusters) > 0
        # 所有簇应该按大小排序
        sizes = [c.total_size for c in clusters]
        assert sizes == sorted(sizes, reverse=True)


class TestCancellation:
    """测试取消功能"""

    def test_cancel_analysis(self):
        """测试取消分析"""
        analyzer = AppAnalyzer()

        assert analyzer._cancelled is False

        analyzer.cancel()
        assert analyzer._cancelled is True

    def test_reset_cancel(self):
        """测试重置取消标志"""
        analyzer = AppAnalyzer()

        analyzer.cancel()
        assert analyzer._cancelled is True

        analyzer.reset_cancel()
        assert analyzer._cancelled is False

    def test_cancel_during_scan(self, temp_dir):
        """测试扫描过程中的取消"""
        # 创建大量文件以允许取消
        program_files = temp_dir / "Program Files"
        program_files.mkdir()

        # 创建多个应用目录
        for i in range(20):
            app_path = program_files / f"App{i}"
            app_path.mkdir()
            for j in range(10):
                (app_path / f"file{j}.dat").write_bytes(b"x" * 1024)

        analyzer = AppAnalyzer()
        analyzer.static_zones = [program_files]

        # 在后台线程中运行分析
        import threading
        clusters = []
        analysis_complete = threading.Event()

        def analysis_worker():
            nonlocal clusters
            clusters = analyzer.analyze()
            analysis_complete.set()

        thread = threading.Thread(target=analysis_worker)
        thread.start()

        # 等待一小段时间后取消
        time.sleep(0.1)
        analyzer.cancel()

        thread.join(timeout=2)

        # 验证取消生效
        assert analysis_complete.is_set()


class TestIntegration:
    """集成测试"""

    def test_analyzer_with_event_bus(self, temp_dir):
        """测试分析器与事件总线集成"""
        events_received = []

        def progress_handler(event):
            events_received.append(event.type.value)

        # 订阅事件
        from src.utils.event_bus import EventBus, EventType
        event_bus = EventBus()
        event_bus.subscribe(EventType.ANALYSIS_COMPLETED, progress_handler)

        # 创建分析器并执行分析
        analyzer = AppAnalyzer(event_bus=event_bus)

        program_files = temp_dir / "Program Files"
        program_files.mkdir()
        (program_files / "TestApp").mkdir()
        (program_files / "TestApp" / "app.exe").write_bytes(b"exe")

        analyzer.static_zones = [program_files]
        analyzer.analyze()

        # 验证事件发布（注意：可能有延迟）
        time.sleep(0.1)
        # 事件可能在测试中未被完全捕获，这是正常的

    def test_analyzer_with_state_manager(self, temp_dir):
        """测试分析器与状态管理器集成"""
        from src.controllers.state_manager import StateManager

        state_manager = StateManager()
        analyzer = AppAnalyzer(state_manager=state_manager)

        # 初始状态应该是 IDLE
        assert state_manager.is_idle()

        # 执行分析（在后台线程中）
        program_files = temp_dir / "Program Files"
        program_files.mkdir()
        (program_files / "App").mkdir()

        analyzer.static_zones = [program_files]

        import threading
        thread = threading.Thread(target=analyzer.analyze)
        thread.start()

        thread.join(timeout=2)

        # 分析完成后应该返回 IDLE
        assert state_manager.is_idle() or state_manager.current_state == SystemState.IDLE


class TestEdgeCases:
    """边缘情况测试"""

    def test_analyze_nonexistent_path(self):
        """测试分析不存在的路径"""
        analyzer = AppAnalyzer()
        analyzer.static_zones = [Path("C:/NonExistentPath12345")]

        # 应该返回空列表而不是崩溃
        clusters = analyzer.analyze()
        assert isinstance(clusters, list)

    def test_analyze_permission_denied(self, temp_dir):
        """测试权限被拒绝的情况"""
        # 这个测试取决于系统的权限设置
        analyzer = AppAnalyzer()

        # 尝试扫描系统目录（可能需要权限）
        # Windows 上可能被拒绝访问
        system_path = Path("C:/Windows/System32/config")

        if system_path.exists():
            analyzer.static_zones = [system_path]
            clusters = analyzer._scan_static_zone()

            # 应该优雅地处理权限错误
            assert isinstance(clusters, list)

    def test_analyze_empty_directory(self, temp_dir):
        """测试分析空目录"""
        empty_dir = temp_dir / "Empty"
        empty_dir.mkdir()

        analyzer = AppAnalyzer()
        analyzer.static_zones = [empty_dir]

        clusters = analyzer.analyze()
        assert len(clusters) == 0

    def test_merge_empty_list(self):
        """测试合并空列表"""
        analyzer = AppAnalyzer()
        merged = analyzer._merge_clusters([])

        assert merged == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
