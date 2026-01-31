"""
C-Wiper 版本信息

作者: C-Wiper 开发团队
"""

__version__ = "1.0.0"
__author__ = "C-Wiper Team"
__build_date__ = "2026-01-31"
__license__ = "MIT"
__description__ = "C盘轻量化清理与分析工具"


def get_version_info():
    """
    获取完整版本信息

    Returns:
        dict: 包含版本信息的字典
    """
    return {
        "version": __version__,
        "author": __author__,
        "build_date": __build_date__,
        "license": __license__,
        "description": __description__
    }


if __name__ == "__main__":
    info = get_version_info()
    print(f"{__description__}")
    print(f"版本: {info['version']}")
    print(f"作者: {info['author']}")
    print(f"构建日期: {info['build_date']}")
    print(f"许可证: {info['license']}")
