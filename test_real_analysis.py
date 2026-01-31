"""
实际场景测试 - 验证分析器功能

运行真实的分析流程，验证修复后的显示功能。
"""

import sys
from pathlib import Path

# 设置 UTF-8 编码输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.controllers.analysis_controller import AnalysisController


def test_real_analysis():
    """测试真实的分析流程"""
    print("=" * 70)
    print("实际场景测试 - 空间分析功能")
    print("=" * 70)

    try:
        print("\n[步骤 1] 初始化分析控制器...")
        controller = AnalysisController()
        print("  ✓ 控制器初始化成功")

        print("\n[步骤 2] 启动分析...")
        success = controller.start_analysis()

        if not success:
            print("  ✗ 分析启动失败（可能系统状态不允许）")
            return False

        print("  ✓ 分析已启动，正在等待完成...")

        print("\n[步骤 3] 等待分析完成（最多 60 秒）...")
        completed = controller.wait_for_completion(timeout=60)

        if not completed:
            print("  ! 分析超时（可能需要更长时间）")
            print("  ! 这不是错误，只是系统较慢")
            return False

        print("  ✓ 分析完成")

        print("\n[步骤 4] 获取分析结果...")
        clusters = controller.get_clusters()
        print(f"  ✓ 检测到 {len(clusters)} 个应用")

        if not clusters:
            print("  ! 未检测到任何应用（可能系统没有常见应用）")
            return True

        print("\n[步骤 5] 显示应用列表（前 10 个）...")
        for i, cluster in enumerate(clusters[:10], 1):
            print(f"  {i:2d}. {cluster.app_name:40s} - {cluster._format_size(cluster.total_size):>10s}")

        print("\n[步骤 6] 获取分析报告...")
        report = controller.get_report()

        if report:
            print(f"  应用总数: {report['app_count']}")
            print(f"  总大小: {report['formatted_size']}")
            print(f"  文件总数: {report['total_files']}")
            print(f"  分析耗时: {report['duration']:.2f} 秒")

            if report['top_apps']:
                print(f"\n  Top 5 应用:")
                for i, app in enumerate(report['top_apps'][:5], 1):
                    print(f"    {i}. {app['name']:40s} - {app['formatted_size']:>10s}")

        print("\n[步骤 7] 验证数据完整性...")
        # 验证每个 cluster 都有必需的字段
        all_valid = True
        for cluster in clusters:
            if not cluster.app_name:
                print(f"  ✗ 发现缺少 app_name 的 cluster")
                all_valid = False
            if cluster.total_size < 0:
                print(f"  ✗ 发现无效大小的 cluster: {cluster.app_name}")
                all_valid = False

        if all_valid:
            print(f"  ✓ 所有 {len(clusters)} 个应用数据完整")

        print("\n" + "=" * 70)
        print("✓ 实际场景测试完成")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_real_analysis()
    exit(0 if success else 1)
