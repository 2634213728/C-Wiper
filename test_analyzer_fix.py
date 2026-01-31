"""
测试分析器视图修复

验证显示bug是否已修复：
- 测试数据正确加载到视图
- 测试所有应用都显示在列表中
- 测试应用选择功能正常工作
"""

import sys
import tempfile
from pathlib import Path

# 设置 UTF-8 编码输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.analyzer import AppCluster
from src.ui.analyzer_view import AnalyzerView
from src.controllers.analysis_controller import AnalysisController
from src.ui.main_window import MainWindow

def create_mock_clusters(count=5):
    """创建模拟的应用簇数据"""
    clusters = []
    app_names = [
        "Steam",
        "Google Chrome",
        "Visual Studio Code",
        "Python 3.11",
        "Docker Desktop"
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, name in enumerate(app_names[:count]):
            # 创建临时应用目录
            app_path = Path(tmpdir) / name.replace(" ", "_")
            app_path.mkdir()

            # 创建一些模拟文件
            (app_path / "app.exe").write_bytes(b"fake exe" * 100)
            (app_path / "data.json").write_text('{"data": "test"}')
            (app_path / "config.ini").write_text("[config]")

            # 创建 AppCluster 对象
            from src.models.scan_result import FileInfo
            import time

            files = [
                FileInfo(
                    path=app_path / "app.exe",
                    size=800,
                    is_dir=False,
                    modified_time=time.time()
                ),
                FileInfo(
                    path=app_path / "data.json",
                    size=20,
                    is_dir=False,
                    modified_time=time.time()
                ),
                FileInfo(
                    path=app_path / "config.ini",
                    size=10,
                    is_dir=False,
                    modified_time=time.time()
                )
            ]

            cluster = AppCluster(
                app_name=name,
                install_path=app_path,
                static_files=files,
                total_size=830 * (i + 1)  # 递增的大小
            )
            clusters.append(cluster)

    return clusters


def test_analyzer_view_with_mock_data():
    """测试分析器视图使用模拟数据"""
    print("=" * 70)
    print("测试分析器视图 - 修复验证")
    print("=" * 70)

    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("分析器视图修复测试")
        root.geometry("1200x800")

        print("\n[步骤 1] 创建主窗口和控制器...")
        from src.controllers.scan_controller import ScanController
        from src.controllers.clean_controller import CleanController

        scan_ctrl = ScanController()
        clean_ctrl = CleanController()
        analysis_ctrl = AnalysisController()

        main_window = MainWindow(root, scan_ctrl, clean_ctrl, analysis_ctrl)
        print("  ✓ 主窗口创建成功")

        print("\n[步骤 2] 创建分析器视图...")
        analyzer_view = AnalyzerView(root, main_window)
        analyzer_view.pack(fill=tk.BOTH, expand=True)
        print("  ✓ 分析器视图创建成功")

        print("\n[步骤 3] 创建模拟数据（5个应用）...")
        mock_clusters = create_mock_clusters(count=5)
        for cluster in mock_clusters:
            print(f"  - {cluster.app_name}: {cluster._format_size(cluster.total_size)}")
        print(f"  ✓ 创建了 {len(mock_clusters)} 个应用簇")

        print("\n[步骤 4] 加载数据到视图...")
        analyzer_view.load_analysis_results(mock_clusters)
        print("  ✓ 数据加载完成")

        print("\n[步骤 5] 验证显示结果...")
        # 检查 Treeview 中的项目数量
        tree_items = analyzer_view.app_tree.get_children()
        displayed_count = len(tree_items)

        print(f"  ✓ Treeview 中显示的项目数: {displayed_count}")

        if displayed_count == len(mock_clusters):
            print(f"  ✓✓✓ 成功！所有 {len(mock_clusters)} 个应用都正确显示")
        else:
            print(f"  ✗✗✗ 失败！期望 {len(mock_clusters)} 个，实际显示 {displayed_count} 个")
            return False

        # 验证 cluster_map
        print(f"\n[步骤 6] 验证 cluster_map 映射...")
        print(f"  ✓ cluster_map 包含 {len(analyzer_view.cluster_map)} 个映射")

        if len(analyzer_view.cluster_map) == len(mock_clusters):
            print(f"  ✓✓✓ 映射数量正确")
        else:
            print(f"  ✗✗✗ 映射数量错误！期望 {len(mock_clusters)} 个，实际 {len(analyzer_view.cluster_map)} 个")
            return False

        # 测试选择功能
        print(f"\n[步骤 7] 测试应用选择功能...")
        if tree_items:
            # 选择第一个应用
            first_item = tree_items[0]
            analyzer_view.app_tree.selection_set(first_item)

            # 验证 cluster 是否正确获取
            cluster = analyzer_view.cluster_map.get(first_item)
            if cluster:
                print(f"  ✓ 成功获取选中的应用: {cluster.app_name}")
                print(f"  ✓ 应用大小: {cluster._format_size(cluster.total_size)}")
                print(f"  ✓ 文件数: {len(cluster.static_files)}")
            else:
                print(f"  ✗ 无法获取选中的应用数据")
                return False

        print(f"\n[步骤 8] 验证统计信息...")
        stats_text = analyzer_view.stats_label.cget("text")
        print(f"  ✓ 统计信息: {stats_text}")

        if f"应用总数: {len(mock_clusters)}" in stats_text:
            print(f"  ✓✓✓ 统计信息正确")
        else:
            print(f"  ✗ 统计信息不正确")
            return False

        print("\n" + "=" * 70)
        print("✓✓✓ 所有测试通过！显示bug已修复")
        print("=" * 70)

        # 保持窗口打开 3 秒供视觉验证
        print("\n窗口将保持打开 3 秒供视觉验证...")
        root.after(3000, lambda: root.destroy())
        root.mainloop()

        return True

    except Exception as e:
        print(f"\n✗✗✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_functionality():
    """测试搜索功能"""
    print("\n" + "=" * 70)
    print("测试搜索功能")
    print("=" * 70)

    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口

        from src.controllers.scan_controller import ScanController
        from src.controllers.clean_controller import CleanController

        scan_ctrl = ScanController()
        clean_ctrl = CleanController()
        analysis_ctrl = AnalysisController()

        main_window = MainWindow(root, scan_ctrl, clean_ctrl, analysis_ctrl)
        analyzer_view = AnalyzerView(root, main_window)

        # 加载测试数据
        mock_clusters = create_mock_clusters(count=5)
        analyzer_view.load_analysis_results(mock_clusters)

        print("\n[测试 1] 搜索 'Steam'")
        analyzer_view.search_var.set("Steam")
        analyzer_view._on_search_changed()

        tree_items = analyzer_view.app_tree.get_children()
        print(f"  搜索结果数量: {len(tree_items)}")
        print(f"  cluster_map 大小: {len(analyzer_view.cluster_map)}")

        if len(tree_items) == 1 and len(analyzer_view.cluster_map) == 1:
            print("  ✓ 搜索功能正常")
        else:
            print("  ✗ 搜索功能异常")
            root.destroy()
            return False

        print("\n[测试 2] 清空搜索")
        analyzer_view.search_var.set("")
        analyzer_view._on_search_changed()

        tree_items = analyzer_view.app_tree.get_children()
        print(f"  恢复显示数量: {len(tree_items)}")
        print(f"  cluster_map 大小: {len(analyzer_view.cluster_map)}")

        if len(tree_items) == 5 and len(analyzer_view.cluster_map) == 5:
            print("  ✓ 清空搜索功能正常")
        else:
            print("  ✗ 清空搜索功能异常")
            root.destroy()
            return False

        root.destroy()
        print("\n✓ 搜索功能测试通过")
        return True

    except Exception as e:
        print(f"\n✗ 搜索功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "分析器视图 Bug 修复验证测试" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")

    # 测试 1: 基本显示功能
    test1_passed = test_analyzer_view_with_mock_data()

    # 测试 2: 搜索功能
    test2_passed = test_search_functionality()

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"  基本显示功能: {'✓ 通过' if test1_passed else '✗ 失败'}")
    print(f"  搜索功能:      {'✓ 通过' if test2_passed else '✗ 失败'}")
    print("=" * 70)

    if test1_passed and test2_passed:
        print("\n✓✓✓ 所有测试通过！Bug 已成功修复")
        print("\n修复说明:")
        print("  1. 添加了 cluster_map 字典来存储 item_id 到 AppCluster 的映射")
        print("  2. 修复了 _populate_app_list 方法，不再使用错误的 Treeview.set()")
        print("  3. 修复了 _on_app_selected 方法，从 cluster_map 获取数据")
        print("  4. 修复了 _on_search_changed 方法，保持映射同步")
        return 0
    else:
        print("\n✗✗✗ 部分测试失败，需要进一步调试")
        return 1


if __name__ == "__main__":
    exit(main())
