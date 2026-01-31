import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing C-Wiper core modules (non-controller)...")
print("-" * 50)

try:
    # Test security module (no dependencies)
    from src.core.security import SecurityLayer
    print("OK: SecurityLayer")

    # Test rule engine (no dependencies on scanner)
    from src.core.rule_engine import RuleEngine, RiskLevel
    print("OK: RuleEngine")

    # Test models (no dependencies)
    from src.models.scan_result import ScanTarget, FileInfo
    print("OK: Models")

    # Test utils (no dependencies on core)
    from src.utils.event_bus import EventBus, EventType
    print("OK: EventBus")

    print("-" * 50)
    print("SUCCESS: Independent modules loaded!")
    print("=" * 50)
    print("\nNote: Scanner and Controllers have circular dependencies")
    print("These will be tested when running the full app.")
    print("=" * 50)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
