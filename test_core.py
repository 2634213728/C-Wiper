import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing C-Wiper core modules...")
print("-" * 50)

try:
    from src.core.security import SecurityLayer
    print("OK: SecurityLayer")

    from src.core.rule_engine import RuleEngine
    print("OK: RuleEngine")

    from src.core.scanner import CoreScanner
    print("OK: CoreScanner")

    from src.core.cleaner import CleanerExecutor
    print("OK: CleanerExecutor")

    print("-" * 50)
    print("SUCCESS: All core modules loaded!")
    print("-" * 50)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
