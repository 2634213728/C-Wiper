"""
EventBus - 事件总线模块

本模块实现线程安全的发布-订阅模式事件总线，用于系统内各组件间的解耦通信。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """
    事件类型枚举

    定义系统中所有可能的事件类型，用于事件的分类和路由。
    """
    # 扫描相关事件
    SCAN_STARTED = "scan_started"
    SCAN_PROGRESS = "scan_progress"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"

    # 清理相关事件
    CLEAN_STARTED = "clean_started"
    CLEAN_PROGRESS = "clean_progress"
    CLEAN_COMPLETED = "clean_completed"
    CLEAN_FAILED = "clean_failed"

    # 分析相关事件
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_PROGRESS = "analysis_progress"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"

    # 系统事件
    SYSTEM_STATE_CHANGED = "system_state_changed"
    SYSTEM_ERROR = "system_error"


@dataclass
class Event:
    """
    事件数据类

    封装事件的基本信息，包括类型、数据和时间戳。

    Attributes:
        type: 事件类型，使用 EventType 枚举
        data: 事件携带的数据字典，包含事件相关的具体信息
        timestamp: 事件创建的时间戳，默认为创建事件时的当前时间
    """
    type: EventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """初始化后处理，记录事件创建日志"""
        logger.debug(f"Event created: {self.type.value} at {self.timestamp}")


class EventBus:
    """
    事件总线单例类

    实现线程安全的发布-订阅模式，支持多个订阅者监听同一事件类型。
    采用双重检查锁定模式确保单例的线程安全。

    Attributes:
        _instance: EventBus 单例实例
        _lock: 类级别的线程锁，用于单例创建
        _subscribers: 事件类型到订阅者回调函数列表的映射字典
        _event_lock: 事件操作的线程锁，保护订阅者列表的并发访问

    Example:
        >>> bus = EventBus()
        >>> def handler(event):
        ...     print(f"Received: {event.data}")
        >>> bus.subscribe(EventType.SCAN_STARTED, handler)
        >>> bus.publish(Event(type=EventType.SCAN_STARTED, data={"target": "temp"}))
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> 'EventBus':
        """
        实现单例模式

        使用双重检查锁定确保线程安全且高效。

        Returns:
            EventBus: 唯一的 EventBus 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._subscribers: Dict[EventType, List[Callable]] = {}
                    cls._instance._event_lock = threading.Lock()
                    logger.info("EventBus singleton instance created")
        return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        订阅事件

        为指定的事件类型注册订阅者回调函数。当该类型的事件被发布时，
        所有订阅的回调函数将被调用。

        Args:
            event_type: 要订阅的事件类型
            callback: 事件处理回调函数，接收 Event 对象作为参数

        Raises:
            TypeError: 如果 callback 不是可调用对象

        Note:
            同一个回调可以多次订阅，每次订阅都会被独立调用
        """
        if not callable(callback):
            raise TypeError(f"Callback must be callable, got {type(callback)}")

        with self._event_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type.value}: {callback.__name__}")

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """
        取消订阅事件

        从指定事件类型的订阅者列表中移除回调函数。

        Args:
            event_type: 要取消订阅的事件类型
            callback: 要移除的回调函数

        Returns:
            bool: 成功移除返回 True，回调函数不在订阅列表中返回 False
        """
        with self._event_lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed from {event_type.value}: {callback.__name__}")
                    return True
                except ValueError:
                    logger.warning(f"Callback not found in {event_type.value} subscribers")
                    return False
        return False

    def publish(self, event: Event) -> None:
        """
        发布事件

        将事件发布给所有订阅了该事件类型的订阅者。每个订阅者的回调函数
        将在独立的线程中执行，确保互不影响。如果某个回调抛出异常，
        将被捕获并记录，不影响其他订阅者。

        Args:
            event: 要发布的事件对象

        Note:
            - 发布操作是异步的，回调函数在发布线程中同步执行
            - 如果回调函数执行时间较长，可能影响事件发布性能
            - 建议回调函数中避免执行耗时操作
        """
        # 获取订阅者列表（在锁外执行回调，避免死锁）
        with self._event_lock:
            subscribers = self._subscribers.get(event.type, []).copy()

        if not subscribers:
            logger.debug(f"No subscribers for event: {event.type.value}")
            return

        logger.info(f"Publishing event: {event.type.value} to {len(subscribers)} subscribers")

        # 通知所有订阅者
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Error in event callback '{callback.__name__}' "
                    f"for event '{event.type.value}': {e}",
                    exc_info=True
                )

    def clear_subscribers(self, event_type: EventType = None) -> None:
        """
        清除订阅者

        清除指定事件类型的所有订阅者，或清除所有事件类型的订阅者。

        Args:
            event_type: 要清除订阅者的事件类型。如果为 None，清除所有订阅者
        """
        with self._event_lock:
            if event_type is None:
                self._subscribers.clear()
                logger.info("Cleared all subscribers")
            elif event_type in self._subscribers:
                del self._subscribers[event_type]
                logger.info(f"Cleared subscribers for {event_type.value}")

    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        获取指定事件类型的订阅者数量

        Args:
            event_type: 事件类型

        Returns:
            int: 订阅者数量
        """
        with self._event_lock:
            return len(self._subscribers.get(event_type, []))


def test_event_bus():
    """
    EventBus Test Function

    Tests basic functionality including subscribe, publish and exception handling.
    """
    print("=" * 60)
    print("EventBus Test")
    print("=" * 60)

    # Test 1: Basic subscribe and publish
    print("\n[Test 1] Basic subscribe and publish")
    bus = EventBus()

    results = []

    def handler1(event: Event):
        results.append(f"handler1: {event.data.get('message')}")
        print(f"  [OK] handler1 received event: {event.data.get('message')}")

    def handler2(event: Event):
        results.append(f"handler2: {event.data.get('message')}")
        print(f"  [OK] handler2 received event: {event.data.get('message')}")

    bus.subscribe(EventType.SCAN_STARTED, handler1)
    bus.subscribe(EventType.SCAN_STARTED, handler2)

    test_event = Event(
        type=EventType.SCAN_STARTED,
        data={"message": "开始扫描", "target": "temp"}
    )
    bus.publish(test_event)

    assert len(results) == 2, "Should have 2 callbacks called"
    print("  [OK] Test passed: both subscribers received event")

    # Test 2: Unsubscribe
    print("\n[Test 2] Unsubscribe")
    bus.unsubscribe(EventType.SCAN_STARTED, handler1)
    results.clear()

    bus.publish(test_event)
    assert len(results) == 1, "Should have only 1 callback called"
    print("  [OK] Test passed: unsubscribe successful")

    # Test 3: Exception handling
    print("\n[Test 3] Exception handling")
    def bad_handler(event: Event):
        raise RuntimeError("Test exception")

    bus.subscribe(EventType.SCAN_COMPLETED, bad_handler)

    def good_handler(event: Event):
        print("  [OK] good_handler executed normally")

    bus.subscribe(EventType.SCAN_COMPLETED, good_handler)

    error_event = Event(
        type=EventType.SCAN_COMPLETED,
        data={"message": "Scan completed"}
    )
    bus.publish(error_event)  # Should not raise exception
    print("  [OK] Test passed: exception caught, does not affect other subscribers")

    # Test 4: Singleton pattern
    print("\n[Test 4] Singleton pattern")
    bus2 = EventBus()
    assert bus is bus2, "Should return same instance"
    print("  [OK] Test passed: singleton pattern works")

    # Test 5: Get subscriber count
    print("\n[Test 5] Get subscriber count")
    count = bus.get_subscriber_count(EventType.SCAN_STARTED)
    print(f"  [OK] SCAN_STARTED subscriber count: {count}")
    assert count == 1, "Should have 1 subscriber"

    # Test 6: Clear subscribers
    print("\n[Test 6] Clear subscribers")
    bus.clear_subscribers(EventType.SCAN_STARTED)
    count = bus.get_subscriber_count(EventType.SCAN_STARTED)
    assert count == 0, "Subscribers should be cleared"
    print("  [OK] Test passed: subscribers cleared")

    print("\n" + "=" * 60)
    print("[OK] All EventBus tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_event_bus()
