"""
C-Wiper 模块导入测试

测试所有模块是否可以正常导入和实例化。
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("C-Wiper Module Import Test")
    print("=" * 60)

    modules = [
        ("utils.event_bus", "EventBus, EventType, Event"),
        ("controllers.state_manager", "StateManager, SystemState"),
        ("core.security", "SecurityLayer"),
        ("models.scan_result", "ScanTarget, FileInfo, ScanResult"),
    ]

    passed = 0
    failed = 0

    for module_name, items in modules:
        try:
            module = __import__(module_name, fromlist=items)
            print(f"[OK] {module_name} - {items}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {module_name} - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
