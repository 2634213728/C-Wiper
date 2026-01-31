"""
StateManager - 状态管理器模块

本模块实现线程安全的系统状态管理器，用于控制系统状态转换和取消请求。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import queue
import threading
from enum import Enum
from typing import Optional


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemState(Enum):
    """
    系统状态枚举

    定义系统所有可能的状态，用于状态机的状态转换验证。

    Attributes:
        IDLE: 空闲状态，系统未进行任何操作
        SCANNING: 扫描状态，正在执行文件扫描
        CLEANING: 清理状态，正在执行文件清理
        ANALYZING: 分析状态，正在执行应用空间分析
    """
    IDLE = "idle"
    SCANNING = "scanning"
    CLEANING = "cleaning"
    ANALYZING = "analyzing"

    def __str__(self) -> str:
        """返回状态的字符串表示"""
        return self.value


class StateTransitionError(Exception):
    """
    状态转换错误异常

    当尝试执行非法的状态转换时抛出此异常。

    Attributes:
        from_state: 源状态
        to_state: 目标状态
        message: 错误消息
    """
    def __init__(self, from_state: SystemState, to_state: SystemState):
        self.from_state = from_state
        self.to_state = to_state
        self.message = (
            f"Invalid state transition: {from_state.value} -> {to_state.value}. "
            f"Please check valid transitions."
        )
        super().__init__(self.message)


class StateManager:
    """
    状态管理器单例类

    实现线程安全的系统状态管理，支持状态转换验证和取消请求机制。
    采用有限状态机模式，确保系统状态转换的合法性。

    Attributes:
        _instance: StateManager 单例实例
        _lock: 类级别的线程锁，用于单例创建
        _state: 当前系统状态
        _state_lock: 状态操作的线程锁（可重入锁）
        _cancel_flag: 取消请求标志，用于请求取消当前操作
        _result_queue: 结果队列，用于存储操作结果

    Example:
        >>> manager = StateManager()
        >>> manager.transition_to(SystemState.SCANNING)
        >>> if manager.is_cancel_requested:
        ...     manager.transition_to(SystemState.IDLE)
    """

    _instance = None
    _lock = threading.Lock()

    # 定义合法的状态转换
    VALID_TRANSITIONS = {
        SystemState.IDLE: [SystemState.SCANNING, SystemState.ANALYZING, SystemState.CLEANING],
        SystemState.SCANNING: [SystemState.IDLE, SystemState.CLEANING],
        SystemState.ANALYZING: [SystemState.IDLE],
        SystemState.CLEANING: [SystemState.IDLE],
    }

    def __new__(cls) -> 'StateManager':
        """
        实现单例模式

        使用双重检查锁定确保线程安全且高效。

        Returns:
            StateManager: 唯一的 StateManager 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._state = SystemState.IDLE
                    cls._instance._state_lock = threading.RLock()
                    cls._instance._cancel_flag = False
                    cls._instance._result_queue = queue.Queue()
                    logger.info("StateManager singleton instance created")
                    logger.info(f"Initial state: {cls._instance._state.value}")
        return cls._instance

    def transition_to(self, new_state: SystemState) -> bool:
        """
        转换到新状态

        执行状态转换前会验证转换的合法性。如果转换非法，将抛出异常。
        成功转换后会重置取消请求标志。

        Args:
            new_state: 要转换到的目标状态

        Returns:
            bool: 转换成功返回 True

        Raises:
            StateTransitionError: 当状态转换非法时抛出

        Example:
            >>> manager = StateManager()
            >>> manager.transition_to(SystemState.SCANNING)  # IDLE -> SCANNING
            True
            >>> manager.transition_to(SystemState.ANALYZING)  # SCANNING -> ANALYZING (非法)
            StateTransitionError: Invalid state transition: scanning -> analyzing
        """
        with self._state_lock:
            # 验证状态转换的合法性
            valid_next_states = self.VALID_TRANSITIONS.get(self._state, [])

            if new_state not in valid_next_states:
                error_msg = (
                    f"Invalid state transition: {self._state.value} -> {new_state.value}. "
                    f"Valid transitions from {self._state.value}: "
                    f"{[s.value for s in valid_next_states]}"
                )
                logger.error(error_msg)
                raise StateTransitionError(self._state, new_state)

            old_state = self._state
            self._state = new_state
            self._cancel_flag = False  # 重置取消标志

            logger.info(f"State transition: {old_state.value} -> {new_state.value}")
            return True

    def request_cancel(self) -> None:
        """
        请求取消当前操作

        设置取消请求标志，通知正在执行的操作应该停止。
        操作执行者应该定期检查 is_cancel_requested 属性。

        Note:
            此方法不会立即停止操作，只是设置标志。
            操作执行者需要主动检查并响应取消请求。

        Example:
            >>> manager = StateManager()
            >>> manager.request_cancel()
            >>> # 在长时间操作中检查
            >>> if manager.is_cancel_requested:
            ...     # 清理并退出
        """
        with self._state_lock:
            self._cancel_flag = True
            logger.info(f"Cancel requested in state: {self._state.value}")

    def reset_cancel_flag(self) -> None:
        """
        重置取消请求标志

        将取消标志设置为 False，通常用于状态转换后清理。

        Note:
            一般情况下不需要手动调用，transition_to 会自动重置
        """
        with self._state_lock:
            self._cancel_flag = False
            logger.debug("Cancel flag reset")

    @property
    def current_state(self) -> SystemState:
        """
        获取当前系统状态

        Returns:
            SystemState: 当前系统状态
        """
        with self._state_lock:
            return self._state

    @property
    def is_cancel_requested(self) -> bool:
        """
        检查是否请求取消

        Returns:
            bool: 如果设置了取消请求标志返回 True，否则返回 False

        Example:
            >>> manager = StateManager()
            >>> if manager.is_cancel_requested:
            ...     print("操作被取消")
        """
        with self._state_lock:
            return self._cancel_flag

    def put_result(self, result: any) -> None:
        """
        将操作结果放入结果队列

        Args:
            result: 操作结果对象
        """
        try:
            self._result_queue.put(result, block=False)
            logger.debug(f"Result put in queue: {type(result).__name__}")
        except queue.Full:
            logger.warning("Result queue is full, result discarded")

    def get_result(self, timeout: Optional[float] = None) -> any:
        """
        从结果队列获取操作结果

        Args:
            timeout: 超时时间（秒），None 表示阻塞等待

        Returns:
            操作结果对象

        Raises:
            queue.Empty: 如果超时且队列为空
        """
        try:
            result = self._result_queue.get(block=True, timeout=timeout)
            logger.debug(f"Result retrieved from queue: {type(result).__name__}")
            return result
        except queue.Empty:
            logger.warning(f"Result queue is empty (timeout={timeout})")
            raise

    def is_idle(self) -> bool:
        """
        检查系统是否处于空闲状态

        Returns:
            bool: 空闲状态返回 True，否则返回 False
        """
        return self.current_state == SystemState.IDLE

    def is_scanning(self) -> bool:
        """
        检查系统是否正在扫描

        Returns:
            bool: 扫描状态返回 True，否则返回 False
        """
        return self.current_state == SystemState.SCANNING

    def is_cleaning(self) -> bool:
        """
        检查系统是否正在清理

        Returns:
            bool: 清理状态返回 True，否则返回 False
        """
        return self.current_state == SystemState.CLEANING

    def is_analyzing(self) -> bool:
        """
        检查系统是否正在分析

        Returns:
            bool: 分析状态返回 True，否则返回 False
        """
        return self.current_state == SystemState.ANALYZING

    def get_valid_transitions(self, from_state: Optional[SystemState] = None) -> list:
        """
        获取从指定状态可以转换到的状态列表

        Args:
            from_state: 源状态，如果为 None 则使用当前状态

        Returns:
            list: 可转换到的状态列表
        """
        if from_state is None:
            from_state = self.current_state

        return self.VALID_TRANSITIONS.get(from_state, [])


def test_state_manager():
    """
    StateManager Test Function

    Tests basic functionality including state transitions, cancel requests and thread safety.
    """
    import time

    print("=" * 60)
    print("StateManager Test")
    print("=" * 60)

    # Test 1: Basic state transitions
    print("\n[Test 1] Basic state transitions")
    manager = StateManager()

    assert manager.is_idle(), "Initial state should be IDLE"
    print(f"  [OK] Initial state: {manager.current_state.value}")

    manager.transition_to(SystemState.SCANNING)
    assert manager.is_scanning(), "State should be SCANNING"
    print(f"  [OK] Transitioned to: {manager.current_state.value}")

    # Test 2: Invalid state transition detection
    print("\n[Test 2] Invalid state transition detection")
    try:
        manager.transition_to(SystemState.ANALYZING)  # SCANNING -> ANALYZING (invalid)
        assert False, "Should raise StateTransitionError"
    except StateTransitionError as e:
        print(f"  [OK] Caught invalid transition: {e.message}")

    # Test 3: Valid state transition sequence
    print("\n[Test 3] Valid state transition sequence")
    manager.transition_to(SystemState.IDLE)  # SCANNING -> IDLE
    print(f"  [OK] Transitioned to: {manager.current_state.value}")

    manager.transition_to(SystemState.ANALYZING)  # IDLE -> ANALYZING
    print(f"  [OK] Transitioned to: {manager.current_state.value}")

    manager.transition_to(SystemState.IDLE)  # ANALYZING -> IDLE
    print(f"  [OK] Transitioned to: {manager.current_state.value}")

    # Test 4: Cancel request mechanism
    print("\n[Test 4] Cancel request mechanism")
    manager.transition_to(SystemState.SCANNING)

    assert not manager.is_cancel_requested, "Initial cancel flag should be False"
    print("  [OK] Initial cancel flag: False")

    manager.request_cancel()
    assert manager.is_cancel_requested, "Cancel flag should be True"
    print("  [OK] After cancel request: True")

    manager.transition_to(SystemState.IDLE)
    assert not manager.is_cancel_requested, "Cancel flag should be reset after transition"
    print("  [OK] Reset after transition: False")

    # Test 5: Singleton pattern
    print("\n[Test 5] Singleton pattern")
    manager2 = StateManager()
    assert manager is manager2, "Should return same instance"
    print("  [OK] Test passed: singleton pattern works")

    # Test 6: Thread safety
    print("\n[Test 6] Thread safety test")

    def worker():
        try:
            for _ in range(10):
                manager.transition_to(SystemState.SCANNING)
                time.sleep(0.001)
                manager.transition_to(SystemState.IDLE)
                time.sleep(0.001)
        except StateTransitionError as e:
            print(f"  [WARN] Thread conflict: {e.message}")

    threads = []
    for i in range(3):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("  [OK] Multi-thread test completed (no crashes)")

    # Test 7: Get valid transitions
    print("\n[Test 7] Get valid transitions")
    manager.transition_to(SystemState.IDLE)
    valid = manager.get_valid_transitions()
    print(f"  [OK] From IDLE can transition to: {[s.value for s in valid]}")
    assert SystemState.SCANNING in valid, "Should be able to transition to SCANNING"
    assert SystemState.ANALYZING in valid, "Should be able to transition to ANALYZING"

    # Test 8: State check methods
    print("\n[Test 8] State check methods")
    manager.transition_to(SystemState.CLEANING)
    assert manager.is_cleaning(), "Should be in CLEANING state"
    assert not manager.is_idle(), "Should not be in IDLE state"
    print("  [OK] State check methods work correctly")

    print("\n" + "=" * 60)
    print("[OK] All StateManager tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_state_manager()
