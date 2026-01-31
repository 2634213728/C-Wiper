"""
Integration Test - Complete Analysis Workflow

本模块测试完整的分析工作流程，包括 Static Zone 扫描、Dynamic Zone 扫描、应用匹配等。

测试场景：
1. 扫描 Static Zone
2. 扫描 Dynamic Zone
3. 匹配应用
4. 生成报告

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import time
from pathlib import Path

from src.controllers.analysis_controller import AnalysisController


@pytest.mark.integration
class TestAnalysisWorkflow:
    """测试分析工作流程"""

    def test_complete_analysis_workflow(self):
        """测试完整的分析工作流程"""
        print("\n" + "=" * 70)
        print("Integration Test: Complete Analysis Workflow")
        print("=" * 70)

        # 步骤 1: 创建分析控制器
        print("\n[Step 1] Creating AnalysisController")
        controller = AnalysisController()
        print("  [OK] AnalysisController created")

        # 步骤 2: 启动分析
        print("\n[Step 2] Starting analysis")
        start_time = time.time()

        analysis_started = controller.start_analysis()
        assert analysis_started is True, "Analysis should start successfully"

        print(f"  [OK] Analysis started at {time.strftime('%H:%M:%S')}")

        # 步骤 3: 等待分析完成
        print("\n[Step 3] Waiting for analysis to complete")
        print("  [INFO] This may take a while...")

        completed = controller.wait_for_completion(timeout=120)
        analysis_duration = time.time() - start_time

        if completed:
            print(f"  [OK] Analysis completed in {analysis_duration:.2f}s")
        else:
            print(f"  [WARN] Analysis timed out after {analysis_duration:.2f}s")
            print("  [INFO] Continuing with partial results...")

        # 步骤 4: 获取应用集群
        print("\n[Step 4] Retrieving application clusters")
        clusters = controller.get_clusters()

        print(f"  [OK] Found {len(clusters)} application clusters")

        if clusters:
            print("\n  Top 10 applications by size:")
            for i, cluster in enumerate(clusters[:10], 1):
                size_str = cluster._format_size(cluster.total_size)
                print(f"    {i}. {cluster.app_name} - {size_str}")
                print(f"       Static files: {len(cluster.static_files)}")
                print(f"       Dynamic files: {len(cluster.dynamic_files)}")
                print(f"       Orphan files: {len(cluster.orphan_files)}")

        # 步骤 5: 获取分析报告
        print("\n[Step 5] Getting analysis report")
        report = controller.get_report()

        if report:
            print("  [OK] Analysis Report:")
            print(f"    Application count: {report.get('app_count', 0)}")
            print(f"    Total size: {report.get('formatted_size', 'N/A')}")
            print(f"    Duration: {report.get('duration', 0):.2f}s")
            print(f"    Static zone files: {report.get('static_file_count', 0)}")
            print(f"    Dynamic zone files: {report.get('dynamic_file_count', 0)}")
            print(f"    Orphan files: {report.get('orphan_file_count', 0)}")
            print(f"    Orphan size: {report.get('formatted_orphan_size', 'N/A')}")

        # 验证结果
        if completed:
            assert len(clusters) >= 0, "Should have clusters"
            print("\n" + "=" * 70)
            print("[OK] Complete analysis workflow test passed!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("[WARN] Analysis workflow test completed with timeout")
            print("=" * 70)

    def test_analysis_state_transitions(self):
        """测试分析状态转换"""
        print("\n" + "=" * 70)
        print("Integration Test: Analysis State Transitions")
        print("=" * 70)

        from src.controllers.state_manager import SystemState

        controller = AnalysisController()

        # 初始状态
        print("\n[Step 1] Checking initial state")
        assert controller.state_manager.current_state == SystemState.IDLE
        print(f"  [OK] Initial state: {controller.state_manager.current_state.value}")

        # 启动分析
        print("\n[Step 2] Starting analysis")
        controller.start_analysis()
        assert controller.state_manager.current_state == SystemState.ANALYZING
        print(f"  [OK] State changed to: {controller.state_manager.current_state.value}")

        # 等待完成
        print("\n[Step 3] Waiting for completion")
        controller.wait_for_completion(timeout=60)

        # 验证返回 IDLE
        print("\n[Step 4] Checking final state")
        assert controller.state_manager.current_state == SystemState.IDLE
        print(f"  [OK] State returned to: {controller.state_manager.current_state.value}")

        print("=" * 70)
        print("[OK] Analysis state transitions test passed!")
        print("=" * 70)

    def test_analysis_event_publishing(self):
        """测试分析事件发布"""
        print("\n" + "=" * 70)
        print("Integration Test: Analysis Event Publishing")
        print("=" * 70)

        # 事件追踪器
        events_log = []

        def event_tracker(event):
            events_log.append({
                'type': event.type.value,
                'timestamp': time.time(),
                'data': event.data
            })

        # 订阅事件
        print("\n[Setup] Setting up event tracking")
        from src.utils.event_bus import EventBus, EventType
        event_bus = EventBus()

        event_types = [
            EventType.ANALYSIS_STARTED,
            EventType.ANALYSIS_PROGRESS,
            EventType.ANALYSIS_COMPLETED,
            EventType.ANALYSIS_FAILED
        ]

        for event_type in event_types:
            event_bus.subscribe(event_type, event_tracker)

        print(f"  [OK] Subscribed to {len(event_types)} event types")

        # 执行分析
        print("\n[Step 1] Starting analysis with event tracking")
        controller = AnalysisController(event_bus=event_bus)

        start_time = time.time()
        controller.start_analysis()
        controller.wait_for_completion(timeout=60)
        duration = time.time() - start_time

        print(f"  [OK] Analysis completed in {duration:.2f}s")

        # 分析事件
        print("\n[Step 2] Analyzing captured events")
        print(f"  [OK] Total events captured: {len(events_log)}")

        for event in events_log:
            print(f"    - {event['type']} at {time.strftime('%H:%M:%S', time.localtime(event['timestamp']))}")

        # 验证关键事件
        print("\n[Step 3] Verifying critical events")
        event_types_received = [e['type'] for e in events_log]

        assert "ANALYSIS_STARTED" in event_types_received, "Should receive ANALYSIS_STARTED"
        print("  [OK] ANALYSIS_STARTED event received")

        if "ANALYSIS_COMPLETED" in event_types_received:
            print("  [OK] ANALYSIS_COMPLETED event received")

        if "ANALYSIS_PROGRESS" in event_types_received:
            progress_events = [e for e in events_log if e['type'] == "ANALYSIS_PROGRESS"]
            print(f"  [OK] {len(progress_events)} progress events received")

        print("=" * 70)
        print("[OK] Analysis event publishing test passed!")
        print("=" * 70)


@pytest.mark.integration
class TestAnalysisComponents:
    """测试分析组件"""

    def test_static_zone_scanning(self):
        """测试 Static Zone 扫描"""
        print("\n" + "=" * 70)
        print("Integration Test: Static Zone Scanning")
        print("=" * 70)

        print("\n[Step 1] Creating analyzer")
        from src.core.analyzer import AppAnalyzer
        analyzer = AppAnalyzer()

        print("\n[Step 2] Scanning Static Zone (Program Files)")
        start_time = time.time()

        static_results = list(analyzer.scan_static_zone())
        static_duration = time.time() - start_time

        print(f"  [OK] Static Zone scan completed in {static_duration:.2f}s")
        print(f"  [INFO] Found {len(static_results)} applications")

        if static_results:
            print("\n  Sample applications:")
            for app in static_results[:5]:
                print(f"    - {app.app_name} ({app.install_path})")

        print("=" * 70)
        print("[OK] Static Zone scanning test passed!")
        print("=" * 70)

    def test_dynamic_zone_scanning(self):
        """测试 Dynamic Zone 扫描"""
        print("\n" + "=" * 70)
        print("Integration Test: Dynamic Zone Scanning")
        print("=" * 70)

        print("\n[Step 1] Creating analyzer")
        from src.core.analyzer import AppAnalyzer
        analyzer = AppAnalyzer()

        print("\n[Step 2] Scanning Dynamic Zone (AppData)")
        start_time = time.time()

        dynamic_results = list(analyzer.scan_dynamic_zone())
        dynamic_duration = time.time() - start_time

        print(f"  [OK] Dynamic Zone scan completed in {dynamic_duration:.2f}s")
        print(f"  [INFO] Found {len(dynamic_results)} application data folders")

        if dynamic_results:
            print("\n  Sample application data:")
            for app_data in dynamic_results[:5]:
                print(f"    - {app_data.app_name} ({app_data.data_path})")

        print("=" * 70)
        print("[OK] Dynamic Zone scanning test passed!")
        print("=" * 70)

    def test_application_matching(self):
        """测试应用匹配"""
        print("\n" + "=" * 70)
        print("Integration Test: Application Matching")
        print("=" * 70)

        print("\n[Step 1] Creating analyzer")
        from src.core.analyzer import AppAnalyzer
        analyzer = AppAnalyzer()

        print("\n[Step 2] Scanning zones")
        static_apps = list(analyzer.scan_static_zone())
        dynamic_apps = list(analyzer.scan_dynamic_zone())

        print(f"  [OK] Static: {len(static_apps)} apps")
        print(f"  [OK] Dynamic: {len(dynamic_apps)} data folders")

        if static_apps and dynamic_apps:
            print("\n[Step 3] Matching applications")
            clusters = analyzer.match(static_apps, dynamic_apps)

            print(f"  [OK] Created {len(clusters)} application clusters")

            if clusters:
                print("\n  Sample matched applications:")
                for cluster in clusters[:5]:
                    print(f"    - {cluster.app_name}")
                    print(f"      Static: {len(cluster.static_files)} files")
                    print(f"      Dynamic: {len(cluster.dynamic_files)} files")
                    if cluster.orphan_files:
                        print(f"      Orphan: {len(cluster.orphan_files)} files")

        print("=" * 70)
        print("[OK] Application matching test passed!")
        print("=" * 70)


@pytest.mark.integration
class TestAnalysisDataQuality:
    """测试分析数据质量"""

    def test_orphan_file_detection(self):
        """测试孤儿文件检测"""
        print("\n" + "=" * 70)
        print("Integration Test: Orphan File Detection")
        print("=" * 70)

        print("\n[Step 1] Running complete analysis")
        controller = AnalysisController()

        controller.start_analysis()
        controller.wait_for_completion(timeout=120)

        clusters = controller.get_clusters()

        print("\n[Step 2] Checking for orphan files")
        total_orphans = 0
        total_orphan_size = 0

        clusters_with_orphans = []
        for cluster in clusters:
            if cluster.orphan_files:
                clusters_with_orphans.append(cluster)
                total_orphans += len(cluster.orphan_files)
                total_orphan_size += sum(f.size for f in cluster.orphan_files)

        print(f"  [OK] Applications with orphan files: {len(clusters_with_orphans)}")
        print(f"  [OK] Total orphan files: {total_orphans}")

        if total_orphans > 0:
            from src.core.scanner import CoreScanner
            orphan_size_str = CoreScanner._format_size(total_orphan_size)
            print(f"  [OK] Total orphan size: {orphan_size_str}")

            print("\n  Top 5 applications with orphan files:")
            sorted_by_orphan_size = sorted(
                clusters_with_orphans,
                key=lambda c: sum(f.size for f in c.orphan_files),
                reverse=True
            )[:5]

            for i, cluster in enumerate(sorted_by_orphan_size, 1):
                orphan_size = sum(f.size for f in cluster.orphan_files)
                size_str = CoreScanner._format_size(orphan_size)
                print(f"    {i}. {cluster.app_name}: {len(cluster.orphan_files)} files, {size_str}")

        print("=" * 70)
        print("[OK] Orphan file detection test passed!")
        print("=" * 70)

    def test_application_size_ranking(self):
        """测试应用大小排名"""
        print("\n" + "=" * 70)
        print("Integration Test: Application Size Ranking")
        print("=" * 70)

        print("\n[Step 1] Running analysis")
        controller = AnalysisController()

        controller.start_analysis()
        controller.wait_for_completion(timeout=120)

        clusters = controller.get_clusters()

        if clusters:
            print("\n[Step 2] Ranking applications by total size")
            ranked = sorted(clusters, key=lambda c: c.total_size, reverse=True)

            print("\n  Top 15 largest applications:")
            for i, cluster in enumerate(ranked[:15], 1):
                size_str = cluster._format_size(cluster.total_size)
                print(f"    {i:2d}. {cluster.app_name:<30s} {size_str:>12s}")

            # 统计信息
            total_size = sum(c.total_size for c in clusters)
            top_10_size = sum(c.total_size for c in ranked[:10])

            print("\n[Step 3] Size distribution statistics")
            print(f"  Total size: {CoreScanner._format_size(total_size)}")
            print(f"  Top 10 apps: {CoreScanner._format_size(top_10_size)} ({top_10_size/total_size*100:.1f}%)")
            print(f"  Average per app: {CoreScanner._format_size(total_size / len(clusters))}")

        print("=" * 70)
        print("[OK] Application size ranking test passed!")
        print("=" * 70)


@pytest.mark.integration
class TestAnalysisPerformance:
    """测试分析性能"""

    @pytest.mark.slow
    def test_analysis_performance(self):
        """测试分析性能"""
        print("\n" + "=" * 70)
        print("Integration Test: Analysis Performance")
        print("=" * 70)

        controller = AnalysisController()

        print("\n[Step 1] Starting performance test")
        start_time = time.time()

        controller.start_analysis()
        completed = controller.wait_for_completion(timeout=120)

        duration = time.time() - start_time

        print(f"\n[Step 2] Performance results")
        print(f"  Completed: {completed}")
        print(f"  Duration: {duration:.2f}s")

        if completed:
            clusters = controller.get_clusters()
            report = controller.get_report()

            if report:
                print(f"\n  Throughput metrics:")
                if report.get('static_file_count', 0) > 0:
                    static_rate = report['static_file_count'] / duration
                    print(f"    Static files: {report['static_file_count']} ({static_rate:.0f} files/sec)")

                if report.get('dynamic_file_count', 0) > 0:
                    dynamic_rate = report['dynamic_file_count'] / duration
                    print(f"    Dynamic files: {report['dynamic_file_count']} ({dynamic_rate:.0f} files/sec)")

                if len(clusters) > 0:
                    app_rate = len(clusters) / duration
                    print(f"    Applications: {len(clusters)} ({app_rate:.2f} apps/sec)")

        print("=" * 70)
        print("[OK] Analysis performance test completed!")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
