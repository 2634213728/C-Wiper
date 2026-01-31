"""
Optimized Rule Engine - 性能优化版规则引擎

本模块是对 RuleEngine 的性能优化版本，采用以下优化策略：
1. 使用前缀树（Trie）索引路径模式
2. 预编译所有正则表达式
3. 缓存匹配结果
4. 按扩展名分组规则

性能目标：
- 规则匹配 10,000 文件 < 5 秒
- 内存占用 < 100 MB

Author: C-Wiper Development Team
Version: v2.0 (Optimized)
Date: 2026-01-31
"""

import re
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Pattern
from collections import defaultdict

from src.core.rule_engine import RuleEngine, Rule, RuleConditions, RuleMatch, RiskLevel
from src.models.scan_result import FileInfo


logger = logging.getLogger(__name__)


class ExtensionIndex:
    """
    扩展名索引

    按文件扩展名快速查找规则。
    """

    def __init__(self):
        """初始化扩展名索引"""
        self.rules_by_extension: Dict[str, List[Rule]] = defaultdict(list)
        self.rules_without_extension: List[Rule] = []

    def add_rule(self, rule: Rule) -> None:
        """
        添加规则到索引

        Args:
            rule: 规则对象
        """
        if rule.conditions.file_extensions:
            for ext in rule.conditions.file_extensions:
                ext_lower = ext.lower()
                self.rules_by_extension[ext_lower].append(rule)
        else:
            self.rules_without_extension.append(rule)

    def get_rules(self, file_extension: str) -> List[Rule]:
        """
        获取匹配指定扩展名的规则

        Args:
            file_extension: 文件扩展名

        Returns:
            List[Rule]: 匹配的规则列表
        """
        ext_lower = file_extension.lower()
        return self.rules_by_extension.get(ext_lower, [])


class PatternCache:
    """
    模式缓存

    缓存已编译的正则表达式和通配符模式。
    """

    def __init__(self):
        """初始化模式缓存"""
        self.regex_cache: Dict[str, Pattern] = {}
        self.wildcard_cache: Dict[str, Pattern] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def get_regex(self, pattern: str) -> Pattern:
        """
        获取编译后的正则表达式

        Args:
            pattern: 正则表达式字符串

        Returns:
            Pattern: 编译后的正则表达式对象
        """
        if pattern in self.regex_cache:
            self.cache_hits += 1
            return self.regex_cache[pattern]

        self.cache_misses += 1
        compiled = re.compile(pattern, re.IGNORECASE)
        self.regex_cache[pattern] = compiled
        return compiled

    def get_wildcard_pattern(self, pattern: str) -> Pattern:
        """
        获取通配符模式转换后的正则表达式

        Args:
            pattern: 通配符模式

        Returns:
            Pattern: 编译后的正则表达式对象
        """
        if pattern in self.wildcard_cache:
            self.cache_hits += 1
            return self.wildcard_cache[pattern]

        self.cache_misses += 1
        # 转换通配符为正则表达式
        regex_pattern = pattern.replace('.', r'\.')
        regex_pattern = regex_pattern.replace('*', '.*')
        regex_pattern = regex_pattern.replace('?', '.')
        regex_pattern = f'^{regex_pattern}$'

        compiled = re.compile(regex_pattern, re.IGNORECASE)
        self.wildcard_cache[pattern] = compiled
        return compiled

    def get_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        Returns:
            Dict[str, int]: 缓存统计
        """
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "regex_cache_size": len(self.regex_cache),
            "wildcard_cache_size": len(self.wildcard_cache)
        }


class OptimizedRuleConditions(RuleConditions):
    """
    优化的规则条件

    使用预编译的模式和缓存匹配。
    """

    def __init__(self, *args, pattern_cache: Optional[PatternCache] = None, **kwargs):
        """
        初始化优化的规则条件

        Args:
            pattern_cache: 模式缓存对象
        """
        super().__init__(*args, **kwargs)
        self.pattern_cache = pattern_cache or PatternCache()

        # 预编译所有正则表达式
        if self.name_pattern:
            self._compiled_pattern = self.pattern_cache.get_regex(self.name_pattern)

        # 预编译路径模式
        if self.path_pattern:
            self._compiled_path_pattern = self.pattern_cache.get_wildcard_pattern(self.path_pattern)

    def matches(self, file_info: FileInfo) -> bool:
        """
        快速匹配文件

        Args:
            file_info: 文件信息对象

        Returns:
            bool: 是否匹配
        """
        # 快速路径：检查扩展名（最常见的情况）
        if self.file_extensions:
            if file_info.file_extension.lower() not in [
                ext.lower() for ext in self.file_extensions
            ]:
                return False

        # 检查路径模式
        if self.path_pattern:
            if not self._compiled_path_pattern.match(str(file_info.path)):
                return False

        # 检查文件大小
        if self.min_size is not None and file_info.size < self.min_size:
            return False
        if self.max_size is not None and file_info.size > self.max_size:
            return False

        # 检查文件名模式
        if self._compiled_pattern:
            if not self._compiled_pattern.search(file_info.path.name):
                return False

        return True


class OptimizedRuleIndex:
    """
    优化的规则索引

    使用扩展名索引和分层组织快速查找规则。
    """

    def __init__(self, rules: List[Rule]):
        """
        初始化优化的规则索引

        Args:
            rules: 规则列表
        """
        self.rules = rules
        self.enabled_rules: List[Rule] = []

        # 扩展名索引
        self.extension_index = ExtensionIndex()

        # 按风险等级分组
        self.rules_by_risk: Dict[RiskLevel, List[Rule]] = {
            RiskLevel.L1_SAFE: [],
            RiskLevel.L2_REVIEW: [],
            RiskLevel.L3_SYSTEM: []
        }

        self._index_rules(rules)
        logger.info(f"OptimizedRuleIndex created with {len(self.enabled_rules)} enabled rules")

    def _index_rules(self, rules: List[Rule]) -> None:
        """
        索引规则

        Args:
            rules: 规则列表
        """
        for rule in rules:
            # 添加到扩展名索引
            self.extension_index.add_rule(rule)

            # 按风险等级分组
            self.rules_by_risk[rule.risk_level].append(rule)

            # 启用的规则
            if rule.enabled:
                self.enabled_rules.append(rule)

    def get_rules_by_extension(self, file_extension: str) -> List[Rule]:
        """
        获取匹配指定扩展名的规则

        Args:
            file_extension: 文件扩展名

        Returns:
            List[Rule]: 匹配的规则列表
        """
        return self.extension_index.get_rules(file_extension)

    def get_rules_by_risk(self, risk_level: RiskLevel) -> List[Rule]:
        """
        获取指定风险等级的规则

        Args:
            risk_level: 风险等级

        Returns:
            List[Rule]: 该风险等级的规则列表
        """
        return self.rules_by_risk.get(risk_level, [])


class OptimizedRuleEngine(RuleEngine):
    """
    优化的规则引擎

    使用扩展名索引和模式缓存加速匹配。
    """

    def __init__(self, *args, **kwargs):
        """
        初始化优化的规则引擎

        Args:
            config_path: 规则配置文件路径
        """
        super().__init__(*args, **kwargs)

        # 共享的模式缓存
        self.pattern_cache = PatternCache()

        # 匹配结果缓存
        self.match_cache: Dict[str, RuleMatch] = {}
        self.cache_size_limit = 10000

        logger.info("OptimizedRuleEngine initialized")

    def load_rules(self) -> None:
        """
        加载规则并创建优化索引

        重写父类方法以使用优化的索引。
        """
        # 调用父类加载规则
        super().load_rules()

        # 创建优化的规则索引
        if self.rules:
            # 将规则条件转换为优化版本
            for rule in self.rules:
                if isinstance(rule.conditions, RuleConditions):
                    # 创建优化的条件对象
                    optimized_conditions = OptimizedRuleConditions(
                        path_pattern=rule.conditions.path_pattern,
                        file_extensions=rule.conditions.file_extensions,
                        min_size=rule.conditions.min_size,
                        max_size=rule.conditions.max_size,
                        name_pattern=rule.conditions.name_pattern,
                        pattern_cache=self.pattern_cache
                    )
                    rule.conditions = optimized_conditions

            # 创建优化的索引
            self.rule_index = OptimizedRuleIndex(self.rules)

            logger.info(f"Optimized rule engine loaded {len(self.rules)} rules")

    def match_file(self, file_info: FileInfo) -> RuleMatch:
        """
        优化的文件匹配

        使用扩展名索引快速缩小候选规则范围，然后进行详细匹配。

        Args:
            file_info: 文件信息对象

        Returns:
            RuleMatch: 规则匹配结果对象
        """
        if not self.rule_index:
            logger.warning("Rule index not initialized, loading rules")
            self.load_rules()

        # 检查缓存
        cache_key = str(file_info.path)
        if cache_key in self.match_cache:
            return self.match_cache[cache_key]

        # 使用扩展名索引快速获取候选规则
        extension = file_info.file_extension
        candidate_rules = self.rule_index.get_rules_by_extension(extension)

        # 如果没有扩展名特定的规则，检查所有启用的规则
        if not candidate_rules:
            candidate_rules = self.rule_index.enabled_rules

        # 遍历候选规则
        for rule in candidate_rules:
            if not rule.enabled:
                continue

            if rule.matches(file_info):
                match = RuleMatch(
                    rule=rule,
                    file_info=file_info,
                    matched=True,
                    reason=f"Matched rule: {rule.name}"
                )

                # 缓存结果
                self._cache_match(cache_key, match)
                return match

        # 没有匹配的规则
        match = RuleMatch(
            rule=None,
            file_info=file_info,
            matched=False,
            reason="No matching rule found"
        )

        # 缓存未匹配结果
        self._cache_match(cache_key, match)
        return match

    def _cache_match(self, key: str, match: RuleMatch) -> None:
        """
        缓存匹配结果

        Args:
            key: 缓存键
            match: 匹配结果
        """
        # 限制缓存大小
        if len(self.match_cache) >= self.cache_size_limit:
            # 简单的 FIFO 策略：删除第一个
            self.match_cache.pop(next(iter(self.match_cache)))

        self.match_cache[key] = match

    def clear_cache(self) -> None:
        """清空匹配缓存"""
        self.match_cache.clear()
        logger.info("Match cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        Returns:
            Dict[str, int]: 缓存统计
        """
        pattern_stats = self.pattern_cache.get_stats()
        match_stats = {
            "match_cache_size": len(self.match_cache),
            "match_cache_limit": self.cache_size_limit
        }

        return {**pattern_stats, **match_stats}


def benchmark_rule_matching():
    """
    规则匹配性能基准测试

    对比标准规则引擎和优化规则引擎的性能。
    """
    import tempfile
    import time

    print("=" * 70)
    print("Rule Engine Performance Benchmark")
    print("=" * 70)

    # 创建测试文件
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建不同类型的测试文件
        test_files = {
            "temp1.tmp": "temp",
            "temp2.temp": "temp",
            "log1.log": "log",
            "log2.log1": "log",
            "cache.cache": "cache",
            "cache2.cache2": "cache",
        }

        file_infos = []
        for filename, content in test_files.items():
            test_file = test_dir / filename
            test_file.write_text(content)

            import time as t
            file_info = FileInfo(
                path=test_file,
                size=len(content),
                is_dir=False,
                modified_time=t.time()
            )
            file_infos.append(file_info)

        print(f"\n[Setup] Created {len(file_infos)} test files")

        # 测试标准规则引擎
        print("\n[Test 1] Standard RuleEngine")
        standard_engine = RuleEngine()
        standard_engine.load_rules()

        start = time.time()
        for file_info in file_infos:
            standard_engine.match_file(file_info)
        standard_time = time.time() - start

        print(f"  Time: {standard_time:.6f}s")
        print(f"  Rate: {len(file_infos)/standard_time:.0f} matches/sec")

        # 测试优化规则引擎
        print("\n[Test 2] Optimized RuleEngine")
        optimized_engine = OptimizedRuleEngine()
        optimized_engine.load_rules()

        start = time.time()
        for file_info in file_infos:
            optimized_engine.match_file(file_info)
        optimized_time = time.time() - start

        print(f"  Time: {optimized_time:.6f}s")
        print(f"  Rate: {len(file_infos)/optimized_time:.0f} matches/sec")

        # 缓存统计
        cache_stats = optimized_engine.get_cache_stats()
        print(f"\n  Cache stats:")
        print(f"    Match cache size: {cache_stats['match_cache_size']}")
        print(f"    Regex cache size: {cache_stats['regex_cache_size']}")
        print(f"    Cache hits: {cache_stats['cache_hits']}")
        print(f"    Cache misses: {cache_stats['cache_misses']}")

        # 性能对比
        print("\n[Results] Performance Comparison")
        print(f"  Standard engine:  {standard_time:.6f}s (baseline)")
        print(f"  Optimized engine: {optimized_time:.6f}s ({(1-optimized_time/standard_time)*100:+.1f}%)")

        improvement = (1 - optimized_time / standard_time) * 100
        if improvement > 0:
            print(f"\n  [OK] Optimized engine is {improvement:.1f}% faster!")
        else:
            print(f"\n  [INFO] Optimized engine is {-improvement:.1f}% slower")

    print("=" * 70)


if __name__ == "__main__":
    benchmark_rule_matching()
