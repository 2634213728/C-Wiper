"""
Unit Tests for Rule Engine Module

本模块包含 RuleEngine 的单元测试，涵盖规则加载、路径匹配、扩展名过滤等功能。

测试覆盖：
- 规则加载
- 路径匹配（通配符、正则）
- 扩展名过滤
- 大小范围过滤
- 风险等级分类

Author: C-Wiper Development Team
Version: v1.0
Date: 2026-01-31
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.core.rule_engine import (
    RuleEngine, Rule, RuleConditions, RuleMatch, RuleIndex, RiskLevel
)
from src.models.scan_result import FileInfo


class TestRiskLevel:
    """测试 RiskLevel 枚举"""

    def test_risk_level_values(self):
        """测试风险等级值"""
        assert RiskLevel.L1_SAFE.value == 0
        assert RiskLevel.L2_REVIEW.value == 1
        assert RiskLevel.L3_SYSTEM.value == 2

    def test_risk_level_string_representation(self):
        """测试风险等级字符串表示"""
        assert str(RiskLevel.L1_SAFE) == "L1_SAFE"
        assert str(RiskLevel.L2_REVIEW) == "L2_REVIEW"
        assert str(RiskLevel.L3_SYSTEM) == "L3_SYSTEM"

    def test_risk_level_from_string(self):
        """测试从字符串创建风险等级"""
        assert RiskLevel.from_string("L1_SAFE") == RiskLevel.L1_SAFE
        assert RiskLevel.from_string("L2_REVIEW") == RiskLevel.L2_REVIEW
        assert RiskLevel.from_string("L3_SYSTEM") == RiskLevel.L3_SYSTEM

    def test_risk_level_from_invalid_string(self):
        """测试无效字符串"""
        with pytest.raises(ValueError):
            RiskLevel.from_string("INVALID_LEVEL")


class TestRuleConditions:
    """测试 RuleConditions 类"""

    def test_conditions_creation(self):
        """测试条件创建"""
        conditions = RuleConditions(
            path_pattern="C:/Temp/*",
            file_extensions=[".tmp", ".log"],
            min_size=0,
            max_size=1024*1024,
            name_pattern=r"test\d+"
        )

        assert conditions.path_pattern == "C:/Temp/*"
        assert len(conditions.file_extensions) == 2
        assert conditions.min_size == 0
        assert conditions.max_size == 1024*1024
        assert conditions.name_pattern == r"test\d+"

    def test_match_file_extension(self, temp_dir):
        """测试文件扩展名匹配"""
        conditions = RuleConditions(file_extensions=[".tmp", ".log"])

        # 创建测试文件
        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        # 应该匹配
        assert conditions.matches(file_info) is True

        # 不应该匹配不同的扩展名
        test_file2 = temp_dir / "test.txt"
        test_file2.write_text("content")
        file_info2 = FileInfo(
            path=test_file2,
            size=test_file2.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )
        assert conditions.matches(file_info2) is False

    def test_match_size_range(self, temp_dir):
        """测试文件大小范围匹配"""
        conditions = RuleConditions(min_size=100, max_size=1000)

        # 创建符合大小范围的文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("x" * 500)

        import time
        file_info = FileInfo(
            path=test_file,
            size=500,
            is_dir=False,
            modified_time=time.time()
        )

        assert conditions.matches(file_info) is True

        # 测试超出范围
        file_info_too_small = FileInfo(
            path=test_file,
            size=50,
            is_dir=False,
            modified_time=time.time()
        )
        assert conditions.matches(file_info_too_small) is False

        file_info_too_large = FileInfo(
            path=test_file,
            size=2000,
            is_dir=False,
            modified_time=time.time()
        )
        assert conditions.matches(file_info_too_large) is False

    def test_match_path_pattern(self, temp_dir):
        """测试路径模式匹配（通配符）"""
        conditions = RuleConditions(path_pattern="C:/Temp/*.tmp")

        # 创建测试文件
        test_file = Path("C:/Temp/test.tmp")
        import time
        file_info = FileInfo(
            path=test_file,
            size=100,
            is_dir=False,
            modified_time=time.time()
        )

        assert conditions.matches(file_info) is True

        # 测试不匹配的路径
        test_file2 = Path("C:/Other/test.tmp")
        file_info2 = FileInfo(
            path=test_file2,
            size=100,
            is_dir=False,
            modified_time=time.time()
        )
        assert conditions.matches(file_info2) is False

    def test_match_name_pattern_regex(self, temp_dir):
        """测试文件名正则表达式匹配"""
        conditions = RuleConditions(name_pattern=r"test\d+")

        # 创建匹配的文件名
        test_file = temp_dir / "test123.txt"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        assert conditions.matches(file_info) is True

        # 不匹配的文件名
        test_file2 = temp_dir / "other.txt"
        test_file2.write_text("content")
        file_info2 = FileInfo(
            path=test_file2,
            size=test_file2.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )
        assert conditions.matches(file_info2) is False

    def test_invalid_regex_pattern(self):
        """测试无效的正则表达式"""
        with pytest.raises(ValueError):
            RuleConditions(name_pattern=r"[invalid(")

    def test_conditions_serialization(self):
        """测试条件序列化"""
        conditions = RuleConditions(
            path_pattern="C:/Temp/*",
            file_extensions=[".tmp"],
            min_size=0,
            max_size=1024
        )

        # 转换为字典
        conditions_dict = conditions.to_dict()
        assert conditions_dict["path_pattern"] == "C:/Temp/*"
        assert conditions_dict["file_extensions"] == [".tmp"]

        # 从字典创建
        conditions2 = RuleConditions.from_dict(conditions_dict)
        assert conditions2.path_pattern == conditions.path_pattern
        assert conditions2.file_extensions == conditions.file_extensions


class TestRule:
    """测试 Rule 类"""

    def test_rule_creation(self):
        """测试规则创建"""
        conditions = RuleConditions(file_extensions=[".tmp"])
        rule = Rule(
            id="test_rule",
            name="Test Rule",
            conditions=conditions,
            risk_level=RiskLevel.L1_SAFE,
            category="test"
        )

        assert rule.id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.risk_level == RiskLevel.L1_SAFE
        assert rule.category == "test"
        assert rule.enabled is True

    def test_rule_matches(self, temp_dir):
        """测试规则匹配"""
        conditions = RuleConditions(file_extensions=[".tmp"])
        rule = Rule(
            id="temp_rule",
            name="Temp Rule",
            conditions=conditions,
            risk_level=RiskLevel.L1_SAFE
        )

        # 创建匹配的文件
        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        assert rule.matches(file_info) is True

    def test_disabled_rule_does_not_match(self, temp_dir):
        """测试禁用的规则不匹配"""
        conditions = RuleConditions(file_extensions=[".tmp"])
        rule = Rule(
            id="temp_rule",
            name="Temp Rule",
            conditions=conditions,
            enabled=False  # 禁用规则
        )

        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        assert rule.matches(file_info) is False

    def test_rule_serialization(self):
        """测试规则序列化"""
        conditions = RuleConditions(file_extensions=[".tmp"])
        rule = Rule(
            id="test_rule",
            name="Test Rule",
            description="Test description",
            conditions=conditions,
            risk_level=RiskLevel.L1_SAFE,
            enabled=True,
            category="test"
        )

        # 转换为字典
        rule_dict = rule.to_dict()
        assert rule_dict["id"] == "test_rule"
        assert rule_dict["name"] == "Test Rule"
        assert rule_dict["risk_level"] == "L1_SAFE"

        # 从字典创建
        rule2 = Rule.from_dict(rule_dict)
        assert rule2.id == rule.id
        assert rule2.name == rule.name
        assert rule2.risk_level == rule.risk_level


class TestRuleMatch:
    """测试 RuleMatch 类"""

    def test_rule_match_creation(self, temp_dir):
        """测试规则匹配结果创建"""
        conditions = RuleConditions(file_extensions=[".tmp"])
        rule = Rule(
            id="test_rule",
            name="Test Rule",
            conditions=conditions,
            risk_level=RiskLevel.L1_SAFE
        )

        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        match = RuleMatch(
            rule=rule,
            file_info=file_info,
            matched=True,
            reason="Matched test rule"
        )

        assert match.rule == rule
        assert match.file_info == file_info
        assert match.matched is True
        assert match.reason == "Matched test rule"

    def test_rule_match_risk_level_property(self, temp_dir):
        """测试风险等级属性"""
        conditions = RuleConditions(file_extensions=[".tmp"])
        rule = Rule(
            id="test_rule",
            name="Test Rule",
            conditions=conditions,
            risk_level=RiskLevel.L1_SAFE
        )

        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        match = RuleMatch(
            rule=rule,
            file_info=file_info,
            matched=True
        )

        assert match.risk_level == RiskLevel.L1_SAFE

    def test_unmatched_rule_risk_level(self, temp_dir):
        """测试未匹配规则的默认风险等级"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        match = RuleMatch(
            rule=None,
            file_info=file_info,
            matched=False
        )

        # 未匹配应该默认为 L2_REVIEW
        assert match.risk_level == RiskLevel.L2_REVIEW


class TestRuleIndex:
    """测试 RuleIndex 类"""

    def test_rule_index_creation(self):
        """测试规则索引创建"""
        rules = [
            Rule(
                id=f"rule{i}",
                name=f"Rule {i}",
                conditions=RuleConditions(file_extensions=[".tmp"]),
                risk_level=RiskLevel.L1_SAFE if i % 2 == 0 else RiskLevel.L2_REVIEW,
                category=f"cat{i % 3}"
            )
            for i in range(10)
        ]

        index = RuleIndex(rules)

        assert len(index.enabled_rules) == 10
        assert len(index.rules_by_risk[RiskLevel.L1_SAFE]) == 5
        assert len(index.rules_by_risk[RiskLevel.L2_REVIEW]) == 5

    def test_get_rules_by_category(self):
        """测试按分类获取规则"""
        rules = [
            Rule(
                id=f"rule{i}",
                name=f"Rule {i}",
                conditions=RuleConditions(file_extensions=[".tmp"]),
                category="temp" if i < 5 else "cache"
            )
            for i in range(10)
        ]

        index = RuleIndex(rules)

        temp_rules = index.get_rules_by_category("temp")
        cache_rules = index.get_rules_by_category("cache")

        assert len(temp_rules) == 5
        assert len(cache_rules) == 5

    def test_get_all_categories(self):
        """测试获取所有分类"""
        rules = [
            Rule(
                id=f"rule{i}",
                name=f"Rule {i}",
                conditions=RuleConditions(file_extensions=[".tmp"]),
                category=f"cat{i % 3}"
            )
            for i in range(10)
        ]

        index = RuleIndex(rules)
        categories = index.get_all_categories()

        assert len(categories) == 3
        assert "cat0" in categories
        assert "cat1" in categories
        assert "cat2" in categories


class TestRuleEngine:
    """测试 RuleEngine 类"""

    def test_engine_initialization(self, temp_dir):
        """测试引擎初始化"""
        config_path = temp_dir / "test_rules.json"
        engine = RuleEngine(config_path)

        assert engine.config_path == config_path
        assert len(engine.rules) == 0

    def test_load_default_rules(self):
        """测试加载默认规则"""
        engine = RuleEngine()
        engine.load_rules()

        # 应该加载默认规则
        assert len(engine.rules) > 0
        assert len(engine.get_enabled_rules()) > 0

    def test_load_rules_from_file(self, temp_dir):
        """测试从文件加载规则"""
        import json

        config_path = temp_dir / "test_rules.json"
        rules_data = {
            "version": "1.0",
            "rules": [
                {
                    "id": "test_rule",
                    "name": "Test Rule",
                    "description": "Test description",
                    "conditions": {
                        "file_extensions": [".tmp"]
                    },
                    "risk_level": "L1_SAFE",
                    "enabled": True,
                    "category": "test"
                }
            ]
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f)

        engine = RuleEngine(config_path)
        engine.load_rules()

        assert len(engine.rules) == 1
        assert engine.rules[0].id == "test_rule"

    def test_match_file(self, temp_dir):
        """测试文件匹配"""
        engine = RuleEngine()
        engine.load_rules()

        # 创建临时文件
        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        match = engine.match_file(file_info)

        # 应该匹配到某个规则
        assert isinstance(match, RuleMatch)

    def test_get_rules_by_risk(self):
        """测试按风险等级获取规则"""
        engine = RuleEngine()
        engine.load_rules()

        l1_rules = engine.get_rules_by_risk(RiskLevel.L1_SAFE)
        l2_rules = engine.get_rules_by_risk(RiskLevel.L2_REVIEW)

        assert isinstance(l1_rules, list)
        assert isinstance(l2_rules, list)

    def test_add_rule(self):
        """测试添加规则"""
        engine = RuleEngine()
        engine.load_rules()

        initial_count = len(engine.rules)

        new_rule = Rule(
            id="new_rule",
            name="New Rule",
            conditions=RuleConditions(file_extensions=[".new"]),
            risk_level=RiskLevel.L1_SAFE
        )

        engine.add_rule(new_rule)

        assert len(engine.rules) == initial_count + 1

    def test_remove_rule(self):
        """测试移除规则"""
        engine = RuleEngine()
        engine.load_rules()

        # 添加一个测试规则
        test_rule = Rule(
            id="test_remove",
            name="Test Remove",
            conditions=RuleConditions(file_extensions=[".test"]),
            risk_level=RiskLevel.L1_SAFE
        )
        engine.add_rule(test_rule)

        initial_count = len(engine.rules)

        # 移除规则
        removed = engine.remove_rule("test_remove")

        assert removed is True
        assert len(engine.rules) == initial_count - 1

    def test_save_rules(self, temp_dir):
        """测试保存规则"""
        config_path = temp_dir / "save_test_rules.json"
        engine = RuleEngine(config_path)
        engine.load_rules()

        # 保存规则
        engine.save_rules()

        # 验证文件存在
        assert config_path.exists()

        # 验证可以重新加载
        engine2 = RuleEngine(config_path)
        engine2.load_rules()

        assert len(engine2.rules) == len(engine.rules)

    def test_evaluate_risk(self, temp_dir):
        """测试风险评估"""
        engine = RuleEngine()
        engine.load_rules()

        # 创建匹配的文件
        test_file = temp_dir / "test.tmp"
        test_file.write_text("content")

        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        match = engine.match_file(file_info)
        risk = engine.evaluate_risk(match)

        assert isinstance(risk, RiskLevel)


class TestRuleEngineIntegration:
    """规则引擎集成测试"""

    def test_full_rule_workflow(self, temp_dir):
        """测试完整的规则工作流程"""
        # 1. 创建引擎并加载规则
        engine = RuleEngine()
        engine.load_rules()

        # 2. 创建测试文件
        test_files = {
            "temp.tmp": "temp",
            "log.log": "log",
            "cache.cache": "cache"
        }

        file_infos = []
        for filename, content in test_files.items():
            test_file = temp_dir / filename
            test_file.write_text(content)

            import time
            file_info = FileInfo(
                path=test_file,
                size=len(content),
                is_dir=False,
                modified_time=time.time()
            )
            file_infos.append(file_info)

        # 3. 匹配文件
        matches = [engine.match_file(fi) for fi in file_infos]

        # 4. 验证结果
        matched_count = sum(1 for m in matches if m.matched)
        assert matched_count > 0, "Should match at least one file"

        # 5. 按风险等级统计
        l1_count = sum(1 for m in matches if m.matched and m.risk_level == RiskLevel.L1_SAFE)
        l2_count = sum(1 for m in matches if m.matched and m.risk_level == RiskLevel.L2_REVIEW)

        print(f"\nRule matching results:")
        print(f"  Total files: {len(file_infos)}")
        print(f"  Matched: {matched_count}")
        print(f"  L1_SAFE: {l1_count}")
        print(f"  L2_REVIEW: {l2_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
