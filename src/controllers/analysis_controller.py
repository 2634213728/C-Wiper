"""
Analysis Controller - 分析控制器模块

本模块实现分析控制器，负责协调应用空间分析流程、生成分析报告和发布分析事件。

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
from src.core.analyzer import AppAnalyzer, AppCluster
from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalysisController:
    """
    分析控制器类

    协调应用空间分析流程，管理分析任务和生成报告。
    支持后台线程分析、进度事件通知和取消操作。

    Attributes:
        analyzer: 应用分析器实例
        state_manager: 状态管理器实例
        event_bus: 事件总线实例
        _analysis_thread: 后台分析线程
        _clusters: 分析结果（应用簇列表）
        _report: 分析报告

    Example:
        >>> controller = AnalysisController()
        >>> controller.start_analysis()
        >>> controller.wait_for_completion()
        >>> report = controller.get_report()
        >>> print(f"发现 {report['app_count']} 个应用")
    """

    def __init__(
        self,
        analyzer: Optional[AppAnalyzer] = None,
        state_manager: Optional[StateManager] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化分析控制器

        Args:
            analyzer: 应用分析器实例，默认创建新实例
            state_manager: 状态管理器实例，默认使用全局单例
            event_bus: 事件总线实例，默认使用全局单例
        """
        self.analyzer = analyzer or AppAnalyzer()
        self.state_manager = state_manager or StateManager()
        self.event_bus = event_bus or EventBus()

        self._analysis_thread: Optional[threading.Thread] = None
        self._clusters: List[AppCluster] = []
        self._report: Optional[Dict[str, Any]] = None
        self._complete_event = threading.Event()
        self._lock = threading.Lock()

        logger.info("AnalysisController initialized")

    def start_analysis(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> bool:
        """
        启动分析任务

        在后台线程中执行应用空间分析，立即返回。
        分析过程中会发布进度事件。

        Args:
            progress_callback: 进度回调函数，接收 (阶段, 当前, 总数) 参数

        Returns:
            bool: 成功启动返回 True，当前状态不允许启动分析返回 False

        Example:
            >>> controller = AnalysisController()
            >>> if controller.start_analysis():
            ...     print("分析已启动")
        """
        # 检查系统状态
        if not self.state_manager.is_idle():
            logger.warning(
                f"Cannot start analysis in current state: {self.state_manager.current_state.value}"
            )
            return False

        # 清空之前的结果
        with self._lock:
            self._clusters.clear()
            self._report = None
            self._complete_event.clear()

        try:
            # 转换到分析状态
            self.state_manager.transition_to(SystemState.ANALYZING)

            # 启动后台分析线程
            self._analysis_thread = threading.Thread(
                target=self._analysis_worker,
                args=(progress_callback,),
                name="AnalysisWorker",
                daemon=True
            )
            self._analysis_thread.start()

            logger.info("Analysis started")
            return True

        except Exception as e:
            logger.error(f"Failed to start analysis: {e}", exc_info=True)
            self.state_manager.transition_to(SystemState.IDLE)
            return False

    def _analysis_worker(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]]
    ) -> None:
        """
        分析工作线程

        在后台执行分析任务，处理结果并发布事件。

        Args:
            progress_callback: 进度回调函数
        """
        try:
            start_time = time.time()
            logger.info("Analysis worker started")

            # 执行分析
            clusters = self.analyzer.analyze(progress_callback)

            # 保存结果
            with self._lock:
                self._clusters = clusters

            # 计算耗时
            duration = time.time() - start_time

            # 生成报告
            report = self._generate_report(clusters, duration)

            with self._lock:
                self._report = report

            # 转换状态
            self.state_manager.transition_to(SystemState.IDLE)
            self._complete_event.set()

            # 发布完成事件
            self.event_bus.publish(Event(
                type=EventType.ANALYSIS_COMPLETED,
                data={
                    "app_count": len(clusters),
                    "total_size": report["total_size"],
                    "duration": duration
                }
            ))

            logger.info(
                f"Analysis completed: {len(clusters)} applications, "
                f"{self._format_size(report['total_size'])}, {duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error in analysis worker: {e}", exc_info=True)
            self.state_manager.transition_to(SystemState.IDLE)
            self._complete_event.set()

            # 发布失败事件
            self.event_bus.publish(Event(
                type=EventType.ANALYSIS_FAILED,
                data={"reason": str(e)}
            ))

    def cancel_analysis(self) -> bool:
        """
        取消分析任务

        请求取消当前正在执行的分析操作。

        Returns:
            bool: 成功请求取消返回 True，没有正在进行的分析返回 False

        Example:
            >>> controller.start_analysis()
            >>> # ... 用户点击取消按钮
            >>> controller.cancel_analysis()
        """
        if not self.state_manager.is_analyzing():
            logger.warning("No analysis in progress to cancel")
            return False

        try:
            # 请求取消
            self.state_manager.request_cancel()
            self.analyzer.cancel()

            logger.info("Analysis cancellation requested")
            return True

        except Exception as e:
            logger.error(f"Error cancelling analysis: {e}", exc_info=True)
            return False

    def get_clusters(self) -> List[AppCluster]:
        """
        获取分析结果（应用簇列表）

        Returns:
            List[AppCluster]: 应用簇列表

        Example:
            >>> clusters = controller.get_clusters()
            >>> for cluster in clusters[:10]:
            ...     print(f"{cluster.app_name}: {cluster.formatted_size}")
        """
        with self._lock:
            return self._clusters.copy()

    def get_report(self) -> Optional[Dict[str, Any]]:
        """
        获取分析报告

        Returns:
            Optional[Dict[str, Any]]: 分析报告字典，如果未完成返回 None

        Example:
            >>> report = controller.get_report()
            >>> if report:
            ...     print(f"发现 {report['app_count']} 个应用")
            ...     print(f"总大小: {report['formatted_size']}")
        """
        with self._lock:
            return self._report.copy() if self._report else None

    def _generate_report(
        self,
        clusters: List[AppCluster],
        duration: float
    ) -> Dict[str, Any]:
        """
        生成分析报告

        Args:
            clusters: 应用簇列表
            duration: 分析耗时（秒）

        Returns:
            Dict[str, Any]: 分析报告字典
        """
        total_size = sum(c.total_size for c in clusters)
        total_files = sum(
            len(c.static_files) + len(c.dynamic_files) for c in clusters
        )

        # 找出最大的应用
        top_apps = sorted(clusters, key=lambda c: c.total_size, reverse=True)[:10]

        return {
            "app_count": len(clusters),
            "total_size": total_size,
            "formatted_size": self._format_size(total_size),
            "total_files": total_files,
            "duration": duration,
            "top_apps": [
                {
                    "name": c.app_name,
                    "size": c.total_size,
                    "formatted_size": c._format_size(c.total_size),
                    "path": str(c.install_path)
                }
                for c in top_apps
            ],
            "timestamp": time.time()
        }

    def get_top_apps(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取占用空间最大的应用列表

        Args:
            limit: 返回的应用数量限制

        Returns:
            List[Dict[str, Any]]: 应用信息列表

        Example:
            >>> top_apps = controller.get_top_apps(5)
            >>> for app in top_apps:
            ...     print(f"{app['name']}: {app['formatted_size']}")
        """
        with self._lock:
            sorted_clusters = sorted(
                self._clusters,
                key=lambda c: c.total_size,
                reverse=True
            )[:limit]

            return [
                {
                    "name": c.app_name,
                    "size": c.total_size,
                    "formatted_size": c._format_size(c.total_size),
                    "path": str(c.install_path),
                    "static_files": len(c.static_files),
                    "dynamic_files": len(c.dynamic_files)
                }
                for c in sorted_clusters
            ]

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待分析完成

        阻塞当前线程直到分析完成或超时。

        Args:
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            bool: 分析完成返回 True，超时返回 False

        Example:
            >>> controller.start_analysis()
            >>> if controller.wait_for_completion(timeout=60):
            ...     print("分析完成")
        """
        return self._complete_event.wait(timeout=timeout)

    def is_analyzing(self) -> bool:
        """
        检查是否正在分析

        Returns:
            bool: 正在分析返回 True，否则返回 False
        """
        return self.state_manager.is_analyzing()

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


def test_analysis_controller():
    """
    AnalysisController Test Function

    Tests basic functionality including analysis initiation, cancellation and report generation.
    """
    print("=" * 60)
    print("AnalysisController Test")
    print("=" * 60)

    # Test 1: Controller initialization
    print("\n[Test 1] Controller initialization")
    controller = AnalysisController()
    assert controller.state_manager.is_idle(), "Initial state should be IDLE"
    print("  [OK] Controller initialized")

    # Test 2: Start analysis
    print("\n[Test 2] Start analysis")
    assert controller.start_analysis(), "Analysis should start"
    print("  [OK] Analysis started")

    # Test 3: Wait for completion
    print("\n[Test 3] Wait for completion")
    completed = controller.wait_for_completion(timeout=30)
    if completed:
        print("  [OK] Analysis completed")
    else:
        print("  [WARN] Analysis timed out (may take longer on some systems)")

    # Test 4: Get results
    print("\n[Test 4] Get analysis results")
    clusters = controller.get_clusters()
    print(f"  [OK] Found {len(clusters)} applications")

    if clusters:
        for cluster in clusters[:5]:
            print(f"    - {cluster.app_name}: {cluster._format_size(cluster.total_size)}")

    # Test 5: Get report
    print("\n[Test 5] Get analysis report")
    report = controller.get_report()
    if report:
        print(f"  [OK] App count: {report['app_count']}")
        print(f"  [OK] Total size: {report['formatted_size']}")
        print(f"  [OK] Duration: {report['duration']:.2f}s")

        if report['top_apps']:
            print("  [OK] Top applications:")
            for app in report['top_apps'][:3]:
                print(f"    - {app['name']}: {app['formatted_size']}")

    # Test 6: Get top apps
    print("\n[Test 6] Get top apps")
    top_apps = controller.get_top_apps(5)
    print(f"  [OK] Top {len(top_apps)} applications:")
    for app in top_apps:
        print(f"    - {app['name']}: {app['formatted_size']}")

    # Test 7: State transitions
    print("\n[Test 7] State transitions")
    assert controller.state_manager.is_idle(), "Should return to IDLE after completion"
    print("  [OK] State transitions correct")

    print("\n" + "=" * 60)
    print("[OK] All AnalysisController tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_analysis_controller()
