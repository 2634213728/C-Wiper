"""
Pytest Configuration and Shared Fixtures

本模块提供 pytest 配置和共享的测试 fixture，用于单元测试和集成测试。

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.scan_result import ScanTarget, ScanResult, FileInfo
from src.core.scanner import CoreScanner
from src.core.rule_engine import RuleEngine, Rule, RuleConditions, RiskLevel
from src.core.security import SecurityLayer
from src.controllers.state_manager import StateManager, SystemState
from src.utils.event_bus import EventBus, EventType


# ======================
# Path Fixtures
# ======================

@pytest.fixture
def temp_dir():
    """
    创建临时目录 fixture

    Yields:
        Path: 临时目录路径
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_files_dir(temp_dir):
    """
    创建包含测试文件的临时目录

    创建多种类型的测试文件，用于测试扫描和规则匹配。

    Yields:
        Path: 包含测试文件的临时目录路径
    """
    test_files = {
        "temp1.tmp": "Temporary file 1",
        "temp2.temp": "Temporary file 2",
        "app.log": "Application log",
        "cache.cache": "Cache file",
        "document.txt": "Normal document",
        "backup.bak": "Backup file",
        "data.json": '{"key": "value"}',
        "image.png": b'\x89PNG\r\n\x1a\n',  # PNG header
        "large_file.dat": "x" * (1024 * 100),  # 100 KB file
    }

    # 创建子目录和文件
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    test_files["subdir/nested.tmp"] = "Nested temp file"

    # 写入所有文件
    for filename, content in test_files.items():
        file_path = temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            file_path.write_text(content, encoding='utf-8')

    yield temp_dir


# ======================
# Model Fixtures
# ======================

@pytest.fixture
def scan_target(temp_dir):
    """
    创建扫描目标 fixture

    Args:
        temp_dir: 临时目录 fixture

    Returns:
        ScanTarget: 扫描目标对象
    """
    return ScanTarget(
        id="test_target",
        name="Test Target",
        path=temp_dir,
        description="Test target for unit testing"
    )


@pytest.fixture
def file_info(temp_dir):
    """
    创建文件信息 fixture

    Args:
        temp_dir: 临时目录 fixture

    Returns:
        FileInfo: 文件信息对象
    """
    test_file = temp_dir / "test.tmp"
    test_file.write_text("test content")

    stat = test_file.stat()
    return FileInfo(
        path=test_file,
        size=stat.st_size,
        is_dir=False,
        modified_time=stat.st_mtime,
        created_time=stat.st_ctime,
        file_extension=".tmp"
    )


@pytest.fixture
def scan_result(scan_target, test_files_dir):
    """
    创建扫描结果 fixture

    Args:
        scan_target: 扫描目标 fixture
        test_files_dir: 测试文件目录 fixture

    Returns:
        ScanResult: 扫描结果对象
    """
    files = []
    total_size = 0
    file_count = 0

    for item in test_files_dir.rglob('*'):
        if item.is_file():
            stat = item.stat()
            file_info = FileInfo(
                path=item,
                size=stat.st_size,
                is_dir=False,
                modified_time=stat.st_mtime,
                created_time=stat.st_ctime,
                file_extension=item.suffix
            )
            files.append(file_info)
            total_size += stat.st_size
            file_count += 1

    return ScanResult(
        target=scan_target,
        files=files,
        total_size=total_size,
        file_count=file_count,
        dir_count=1,
        from_cache=False
    )


# ======================
# Core Module Fixtures
# ======================

@pytest.fixture
def core_scanner():
    """
    创建核心扫描器 fixture

    Returns:
        CoreScanner: 核心扫描器实例
    """
    return CoreScanner()


@pytest.fixture
def rule_engine():
    """
    创建规则引擎 fixture

    Returns:
        RuleEngine: 规则引擎实例
    """
    engine = RuleEngine()
    engine.load_rules()
    return engine


@pytest.fixture
def rule_engine_with_custom_rules(temp_dir):
    """
    创建包含自定义规则的规则引擎

    Args:
        temp_dir: 临时目录 fixture

    Returns:
        RuleEngine: 包含自定义规则的规则引擎实例
    """
    engine = RuleEngine()

    # 添加自定义规则
    custom_rules = [
        Rule(
            id="test_temp",
            name="测试临时文件",
            description="用于测试的临时文件规则",
            conditions=RuleConditions(file_extensions=[".tmp"]),
            risk_level=RiskLevel.L1_SAFE,
            category="test"
        ),
        Rule(
            id="test_log",
            name="测试日志文件",
            description="用于测试的日志文件规则",
            conditions=RuleConditions(file_extensions=[".log"]),
            risk_level=RiskLevel.L2_REVIEW,
            category="test"
        )
    ]

    for rule in custom_rules:
        engine.add_rule(rule)

    return engine


@pytest.fixture
def security_layer():
    """
    创建安全层 fixture

    Returns:
        SecurityLayer: 安全层实例
    """
    return SecurityLayer()


# ======================
# Controller Fixtures
# ======================

@pytest.fixture
def state_manager():
    """
    创建状态管理器 fixture

    Returns:
        StateManager: 状态管理器实例
    """
    return StateManager()


@pytest.fixture
def event_bus():
    """
    创建事件总线 fixture

    Returns:
        EventBus: 事件总线实例
    """
    return EventBus()


@pytest.fixture
def mock_event_bus():
    """
    创建模拟事件总线 fixture

    用于隔离事件系统的测试。

    Returns:
        Mock: 模拟的事件总线
    """
    bus = Mock(spec=EventBus)
    bus.publish = Mock()
    bus.subscribe = Mock()
    return bus


# ======================
# UI Fixtures
# ======================

@pytest.fixture
def mock_tkinter():
    """
    创建模拟 Tkinter fixture

    用于 UI 单元测试，避免实际创建窗口。

    Returns:
        Mock: 模拟的 Tkinter 模块
    """
    mock = MagicMock()
    mock.Tk = MagicMock()
    mock.Frame = MagicMock()
    mock.Label = MagicMock()
    mock.Button = MagicMock()
    mock.Entry = MagicMock()
    mock.Text = MagicMock()
    mock.Treeview = MagicMock()
    mock.Scrollbar = MagicMock()
    mock.Progressbar = MagicMock()
    mock.Canvas = MagicMock()
    mock.ttk = MagicMock()
    mock.messagebox = MagicMock()
    mock.filedialog = MagicMock()

    sys.modules['tkinter'] = mock
    sys.modules['tkinter.ttk'] = mock.ttk
    sys.modules['tkinter.messagebox'] = mock.messagebox
    sys.modules['tkinter.filedialog'] = mock.filedialog

    yield mock

    # 清理
    del sys.modules['tkinter']
    del sys.modules['tkinter.ttk']
    del sys.modules['tkinter.messagebox']
    del sys.modules['tkinter.filedialog']


# ======================
# Test Data Fixtures
# ======================

@pytest.fixture
def sample_rules_data():
    """
    创建示例规则数据

    Returns:
        dict: 规则配置字典
    """
    return {
        "version": "1.0",
        "rules": [
            {
                "id": "temp_files",
                "name": "临时文件",
                "description": "Windows 临时文件",
                "conditions": {
                    "file_extensions": [".tmp", ".temp"]
                },
                "risk_level": "L1_SAFE",
                "enabled": True,
                "category": "temp"
            },
            {
                "id": "log_files",
                "name": "日志文件",
                "description": "应用程序日志文件",
                "conditions": {
                    "file_extensions": [".log", ".log1"]
                },
                "risk_level": "L2_REVIEW",
                "enabled": True,
                "category": "logs"
            }
        ]
    }


@pytest.fixture
def performance_test_files(temp_dir):
    """
    创建性能测试用的大量文件

    创建指定数量的测试文件，用于性能测试。

    Args:
        temp_dir: 临时目录 fixture

    Returns:
        Path: 包含大量文件的临时目录
    """
    file_count = 1000
    content = "x" * 1024  # 1 KB per file

    for i in range(file_count):
        (temp_dir / f"file_{i:04d}.tmp").write_text(content)

    return temp_dir


# ======================
# Pytest Hooks
# ======================

def pytest_configure(config):
    """
    Pytest 配置钩子

    配置 pytest 的自定义标记和选项。
    """
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """
    修改测试项的钩子

    自动为测试添加标记。
    """
    for item in items:
        # 根据文件路径自动添加标记
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# ======================
# Helper Functions
# ======================

def create_test_file(path: Path, size: int = 1024) -> None:
    """
    创建指定大小的测试文件

    Args:
        path: 文件路径
        size: 文件大小（字节）
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x" * size)


def wait_for_condition(condition, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """
    等待条件满足

    Args:
        condition: 可调用对象，返回布尔值
        timeout: 超时时间（秒）
        interval: 检查间隔（秒）

    Returns:
        bool: 条件满足返回 True，超时返回 False
    """
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False
