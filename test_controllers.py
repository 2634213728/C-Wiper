import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing C-Wiper controllers...")
print("-" * 50)

try:
    from src.controllers.state_manager import StateManager
    print("OK: StateManager")

    from src.controllers.scan_controller import ScanController
    print("OK: ScanController")

    from src.controllers.clean_controller import CleanController
    print("OK: CleanController")

    from src.controllers.analysis_controller import AnalysisController
    print("OK: AnalysisController")

    print("-" * 50)
    print("SUCCESS: All controllers loaded!")
    print("-" * 50)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
