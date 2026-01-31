import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing CoreScanner import...")
print("-" * 50)

try:
    from src.core.scanner import CoreScanner
    print("SUCCESS: CoreScanner imported successfully")

    # Try to instantiate
    scanner = CoreScanner()
    print("SUCCESS: CoreScanner instantiated")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
