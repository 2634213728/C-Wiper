"""
Scan Controller - 扫描控制器模块

本模块实现扫描控制器，负责协调 CoreScanner 和 RuleEngine，
管理扫描流程、发布扫描事件和处理取消请求。

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
from src.core.rule_engine import RuleEngine, RuleMatch
from src.core.scanner import CoreScanner
from src.models.scan_result import ScanTarget, ScanResult, FileInfo
from src.utils.event_bus import EventBus, EventType, Event


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScanController:
    """
    扫描控制器类

    协调 CoreScanner 和 RuleEngine，管理完整的扫描流程。
    支持后台线程扫描、进度事件通知和取消操作。

    Attributes:
        scanner: 核心扫描器实例
        rule_engine: 规则引擎实例
        state_manager: 状态管理器实例
        event_bus: 事件总线实例
        _scan_thread: 后台扫描线程
        _results: 扫描结果列表
        _matched_files: 匹配规则的文件列表

    Example:
        >>> controller = ScanController()
        >>> targets = [ScanTarget(id="temp", name="临时文件", path=Path("C:/Temp"))]
        >>> controller.start_scan(targets)
        >>> # 等待扫描完成...
        >>> results = controller.get_results()
    """

    def __init__(
        self,
        scanner: Optional[CoreScanner] = None,
        rule_engine: Optional[RuleEngine] = None,
        state_manager: Optional[StateManager] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化扫描控制器

        Args:
            scanner: 核心扫描器实例，默认创建新实例
            rule_engine: 规则引擎实例，默认创建新实例
            state_manager: 状态管理器实例，默认使用全局单例
            event_bus: 事件总线实例，默认使用全局单例
        """
        self.scanner = scanner or CoreScanner()
        self.rule_engine = rule_engine or RuleEngine()
        self.state_manager = state_manager or StateManager()
        self.event_bus = event_bus or EventBus()

        self._scan_thread: Optional[threading.Thread] = None
        self._results: List[ScanResult] = []
        self._matched_files: Dict[str, List[FileInfo]] = {
            'L1_SAFE': [],
            'L2_REVIEW': [],
            'L3_SYSTEM': [],
            'UNMATCHED': []
        }
        self._scan_complete_event = threading.Event()
        self._lock = threading.Lock()

        # 加载规则
        try:
            self.rule_engine.load_rules()
            logger.info(f"Loaded {len(self.rule_engine.get_all_rules())} rules")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")

        logger.info("ScanController initialized")

    def start_scan(
        self,
        targets: List[ScanTarget],
        progress_callback: Optional[Callable[[int, int, ScanResult], None]] = None
    ) -> bool:
        """
        启动扫描任务

        在后台线程中执行扫描，立即返回。扫描过程中会发布进度事件。

        Args:
            targets: 扫描目标列表
            progress_callback: 进度回调函数，接收 (当前索引, 总数, 扫描结果) 参数

        Returns:
            bool: 成功启动返回 True，当前状态不允许启动扫描返回 False

        Raises:
            StateTransitionError: 状态转换非法时抛出

        Example:
            >>> controller = ScanController()
            >>> targets = [target1, target2]
            >>> if controller.start_scan(targets):
            ...     print("扫描已启动")
        """
        # 检查系统状态
        if not self.state_manager.is_idle():
            logger.warning(
                f"Cannot start scan in current state: {self.state_manager.current_state.value}"
            )
            return False

        if not targets:
            logger.warning("No targets to scan")
            return False

        # 清空之前的结果
        with self._lock:
            self._results.clear()
            for key in self._matched_files:
                self._matched_files[key].clear()
            self._scan_complete_event.clear()

        try:
            # 转换到扫描状态
            self.state_manager.transition_to(SystemState.SCANNING)

            # 启动后台扫描线程
            self._scan_thread = threading.Thread(
                target=self._scan_worker,
                args=(targets, progress_callback),
                name="ScanWorker",
                daemon=True
            )
            self._scan_thread.start()

            logger.info(f"Scan started for {len(targets)} targets")
            return True

        except Exception as e:
            logger.error(f"Failed to start scan: {e}", exc_info=True)
            self.state_manager.transition_to(SystemState.IDLE)
            return False

    def _scan_worker(
        self,
        targets: List[ScanTarget],
        progress_callback: Optional[Callable[[int, int, ScanResult], None]]
    ) -> None:
        """
        扫描工作线程

        在后台执行扫描任务，处理扫描结果并发布事件。

        Args:
            targets: 扫描目标列表
            progress_callback: 进度回调函数
        """
        try:
            start_time = time.time()
            total_files = 0
            total_size = 0

            logger.info(f"Scan worker started: {len(targets)} targets")

            # 执行扫描
            for index, result in enumerate(self.scanner.scan(targets)):
                # 检查取消请求
                if self.state_manager.is_cancel_requested:
                    logger.info("Scan cancelled by user request")
                    self.event_bus.publish(Event(
                        type=EventType.SCAN_FAILED,
                        data={"reason": "Cancelled by user", "completed": index}
                    ))
                    break

                # 处理扫描结果
                self._handle_scan_result(result)

                # 更新统计
                total_files += result.file_count
                total_size += result.total_size

                # 保存结果
                with self._lock:
                    self._results.append(result)

                # 调用进度回调
                if progress_callback:
                    try:
                        progress_callback(index + 1, len(targets), result)
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")

            # 扫描完成
            scan_duration = time.time() - start_time
            self.state_manager.transition_to(SystemState.IDLE)
            self._scan_complete_event.set()

            # 发布完成事件
            self.event_bus.publish(Event(
                type=EventType.SCAN_COMPLETED,
                data={
                    "duration": scan_duration,
                    "total_files": total_files,
                    "total_size": total_size,
                    "matched_files": {
                        key: len(files) for key, files in self._matched_files.items()
                    }
                }
            ))

            logger.info(
                f"Scan completed: {total_files} files, "
                f"{self._format_size(total_size)}, {scan_duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error in scan worker: {e}", exc_info=True)
            self.state_manager.transition_to(SystemState.IDLE)
            self._scan_complete_event.set()

            # 发布失败事件
            self.event_bus.publish(Event(
                type=EventType.SCAN_FAILED,
                data={"reason": str(e)}
            ))

    def _handle_scan_result(self, result: ScanResult) -> None:
        """
        处理扫描结果

        使用规则引擎匹配扫描到的文件，分类存储。

        Args:
            result: 扫描结果对象
        """
        if not result.is_success():
            logger.warning(f"Scan failed for {result.target.id}: {result.error_message}")
            return

        logger.debug(
            f"Processing scan result: {result.target.id} - "
            f"{result.file_count} files"
        )

        # 匹配规则
        for file_info in result.files:
            if file_info.is_dir:
                continue

            try:
                match = self.rule_engine.match_file(file_info)

                if match.matched:
                    risk_level = match.risk_level
                    # 将 risk_level 附加到 file_info 对象上，供 UI 筛选使用
                    file_info.risk_level = risk_level
                    self._matched_files[risk_level.name].append(file_info)
                    logger.debug(
                        f"File matched: {file_info.path.name} - "
                        f"Rule: {match.rule.name} - Risk: {risk_level.name}"
                    )
                else:
                    self._matched_files['UNMATCHED'].append(file_info)

            except Exception as e:
                logger.error(f"Error matching file {file_info.path}: {e}")
                self._matched_files['UNMATCHED'].append(file_info)

    def cancel_scan(self) -> bool:
        """
        取消扫描任务

        请求取消当前正在执行的扫描操作。

        Returns:
            bool: 成功请求取消返回 True，没有正在进行的扫描返回 False

        Example:
            >>> controller = ScanController()
            >>> controller.start_scan(targets)
            >>> # ... 用户点击取消按钮
            >>> controller.cancel_scan()
        """
        if not self.state_manager.is_scanning():
            logger.warning("No scan in progress to cancel")
            return False

        try:
            # 请求取消
            self.state_manager.request_cancel()
            self.scanner.cancel()

            logger.info("Scan cancellation requested")
            return True

        except Exception as e:
            logger.error(f"Error cancelling scan: {e}", exc_info=True)
            return False

    def get_results(self) -> List[ScanResult]:
        """
        获取扫描结果

        Returns:
            List[ScanResult]: 扫描结果列表

        Example:
            >>> results = controller.get_results()
            >>> for result in results:
            ...     print(f"{result.target.name}: {result.file_count} files")
        """
        with self._lock:
            return self._results.copy()

    def get_matched_files(self, risk_level: Optional[str] = None) -> List[FileInfo]:
        """
        获取匹配规则的文件列表

        Args:
            risk_level: 风险等级过滤（如 "L1_SAFE", "L2_REVIEW"）
                      None 表示返回所有匹配的文件

        Returns:
            List[FileInfo]: 匹配的文件列表

        Example:
            >>> l1_files = controller.get_matched_files("L1_SAFE")
            >>> all_files = controller.get_matched_files()
        """
        with self._lock:
            if risk_level:
                return self._matched_files.get(risk_level, []).copy()
            else:
                # 返回所有匹配的文件（不包括 UNMATCHED）
                all_matched = []
                for key, files in self._matched_files.items():
                    if key != 'UNMATCHED':
                        all_matched.extend(files)
                return all_matched

    def get_scan_summary(self) -> Dict[str, Any]:
        """
        获取扫描摘要信息

        Returns:
            Dict[str, Any]: 包含扫描摘要的字典

        Example:
            >>> summary = controller.get_scan_summary()
            >>> print(f"总文件数: {summary['total_files']}")
            >>> print(f"L1 安全: {summary['L1_SAFE']}")
        """
        with self._lock:
            total_files = sum(len(files) for files in self._matched_files.values())

            return {
                "total_files": total_files,
                "L1_SAFE": len(self._matched_files['L1_SAFE']),
                "L2_REVIEW": len(self._matched_files['L2_REVIEW']),
                "L3_SYSTEM": len(self._matched_files['L3_SYSTEM']),
                "UNMATCHED": len(self._matched_files['UNMATCHED']),
                "scan_count": len(self._results)
            }

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待扫描完成

        阻塞当前线程直到扫描完成或超时。

        Args:
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            bool: 扫描完成返回 True，超时返回 False

        Example:
            >>> controller.start_scan(targets)
            >>> if controller.wait_for_completion(timeout=60):
            ...     print("扫描完成")
            ... else:
            ...     print("扫描超时")
        """
        return self._scan_complete_event.wait(timeout=timeout)

    def is_scanning(self) -> bool:
        """
        检查是否正在扫描

        Returns:
            bool: 正在扫描返回 True，否则返回 False
        """
        return self.state_manager.is_scanning()

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


def test_scan_controller():
    """
    ScanController Test Function

    Tests basic functionality including scan initiation, cancellation and result retrieval.
    """
    import tempfile

    print("=" * 60)
    print("ScanController Test")
    print("=" * 60)

    # Test 1: Controller initialization
    print("\n[Test 1] Controller initialization")
    controller = ScanController()
    assert controller.state_manager.is_idle(), "Initial state should be IDLE"
    print("  [OK] Controller initialized")

    # Test 2: Scan with test targets
    print("\n[Test 2] Scan with test targets")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test files
        (test_dir / "file1.tmp").write_text("Temporary file 1")
        (test_dir / "file2.log").write_text("Log file")
        (test_dir / "file3.txt").write_text("Text file")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "file4.tmp").write_text("Temporary file 2")

        targets = [
            ScanTarget(
                id="test_target",
                name="Test Target",
                path=test_dir,
                description="Test target for controller"
            )
        ]

        # Start scan
        assert controller.start_scan(targets), "Scan should start"
        print("  [OK] Scan started")

        # Wait for completion
        assert controller.wait_for_completion(timeout=10), "Scan should complete"
        print("  [OK] Scan completed")

    # Test 3: Get results
    print("\n[Test 3] Get scan results")
    results = controller.get_results()
    assert len(results) > 0, "Should have scan results"
    print(f"  [OK] Got {len(results)} results")

    for result in results:
        print(f"    - {result.target.name}: {result.file_count} files")

    # Test 4: Get matched files
    print("\n[Test 4] Get matched files")
    summary = controller.get_scan_summary()
    print(f"  [OK] Total files: {summary['total_files']}")
    print(f"  [OK] L1_SAFE: {summary['L1_SAFE']}")
    print(f"  [OK] L2_REVIEW: {summary['L2_REVIEW']}")

    # Test 5: Cancellation
    print("\n[Test 5] Scan cancellation")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create many files to allow cancellation
        for i in range(100):
            (test_dir / f"file{i}.tmp").write_text(f"Content {i}")

        targets = [ScanTarget(id="cancel_test", name="Cancel Test", path=test_dir)]

        assert controller.start_scan(targets), "Scan should start"

        # Wait a bit then cancel
        time.sleep(0.1)
        assert controller.cancel_scan(), "Cancel should succeed"
        print("  [OK] Scan cancelled")

    # Test 6: State transitions
    print("\n[Test 6] State transitions")
    assert controller.state_manager.is_idle(), "Should return to IDLE after completion"
    print("  [OK] State transitions correct")

    print("\n" + "=" * 60)
    print("[OK] All ScanController tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_scan_controller()
