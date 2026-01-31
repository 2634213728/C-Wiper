#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试检查脚本"""

import subprocess
import sys

def run_tests():
    """运行测试并显示结果"""
    print("=" * 70)
    print("C-Wiper 测试状态检查")
    print("=" * 70)

    # 运行pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )

    # 打印输出
    print(result.stdout)

    # 提取关键信息
    lines = result.stdout.split('\n')
    for line in lines[-20:]:
        if 'passed' in line or 'failed' in line or 'error' in line:
            print("\n" + "=" * 70)
            print("测试结果摘要")
            print("=" * 70)
            print(line)
            break

    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
