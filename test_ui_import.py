import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing C-Wiper UI module imports...")
print("-" * 50)

try:
    from src.ui.main_window import MainWindow
    print("OK: MainWindow")

    from src.ui.dashboard import Dashboard
    print("OK: Dashboard")

    from src.ui.cleaner_view import CleanerView
    print("OK: CleanerView")

    from src.ui.analyzer_view import AnalyzerView
    print("OK: AnalyzerView")

    from src.ui.dialogs import ConfirmCleanDialog, ProgressDialog, ResultDialog, ErrorDialog
    print("OK: Dialogs")

    print("-" * 50)
    print("SUCCESS: All UI modules loaded!")
    print("-" * 50)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
