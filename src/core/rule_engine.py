"""
Rule Engine - 规则决策引擎模块

本模块实现文件匹配规则引擎，支持风险级别分类、路径模式匹配和规则管理。

作者: C-Wiper 开发团队
版本: v1.0
日期: 2026-01-31
"""

import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Pattern

from src.models.scan_result import FileInfo


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """
    风险等级枚举

    定义文件清理的风险级别，用于决策是否安全删除。

    Attributes:
        L1_SAFE: L1 安全级别 - 可安全删除的垃圾文件（临时文件、缓存等）
        L2_REVIEW: L2 审查级别 - 需要用户确认的文件（日志、备份等）
        L3_SYSTEM: L3 系统级别 - 系统文件，不可删除
    """
    L1_SAFE = 0
    L2_REVIEW = 1
    L3_SYSTEM = 2

    def __str__(self) -> str:
        """返回风险等级的字符串表示"""
        return self.name

    @classmethod
    def from_string(cls, value: str) -> 'RiskLevel':
        """
        从字符串创建 RiskLevel 枚举

        Args:
            value: 字符串值（如 "L1_SAFE", "L2_REVIEW"）

        Returns:
            RiskLevel: 对应的枚举值

        Raises:
            ValueError: 如果字符串不匹配任何枚举值
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid RiskLevel: {value}. Must be one of {[e.name for e in cls]}")


class RuleConditions:
    """
    规则条件类

    定义规则匹配的多个条件，包括路径模式、文件扩展名、大小范围等。

    Attributes:
        path_pattern: 路径模式（支持通配符 * 和 ?）
        file_extensions: 文件扩展名列表（如 [".tmp", ".log"]）
        min_size: 最小文件大小（字节），None 表示无限制
        max_size: 最大文件大小（字节），None 表示无限制
        name_pattern: 文件名模式（正则表达式）
    """

    def __init__(
        self,
        path_pattern: Optional[str] = None,
        file_extensions: Optional[List[str]] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        name_pattern: Optional[str] = None
    ):
        """
        初始化规则条件

        Args:
            path_pattern: 路径模式（如 "C:/Temp/*"）
            file_extensions: 文件扩展名列表
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            name_pattern: 文件名正则表达式
        """
        self.path_pattern = path_pattern
        self.file_extensions = file_extensions or []
        self.min_size = min_size
        self.max_size = max_size
        self.name_pattern = name_pattern

        # 预编译正则表达式
        self._compiled_pattern: Optional[Pattern] = None
        if name_pattern:
            try:
                self._compiled_pattern = re.compile(name_pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{name_pattern}': {e}")
                raise ValueError(f"Invalid regex pattern: {e}")

    def matches(self, file_info: FileInfo) -> bool:
        """
        检查文件是否匹配所有条件

        Args:
            file_info: 文件信息对象

        Returns:
            bool: 如果文件匹配所有条件返回 True，否则返回 False
        """
        # 检查路径模式
        if self.path_pattern and not self._match_path_pattern(file_info.path):
            return False

        # 检查文件扩展名
        if self.file_extensions and file_info.file_extension.lower() not in [
            ext.lower() for ext in self.file_extensions
        ]:
            return False

        # 检查文件大小
        if self.min_size is not None and file_info.size < self.min_size:
            return False
        if self.max_size is not None and file_info.size > self.max_size:
            return False

        # 检查文件名模式
        if self._compiled_pattern and not self._compiled_pattern.search(file_info.path.name):
            return False

        return True

    def _match_path_pattern(self, path: Path) -> bool:
        """
        检查路径是否匹配模式（支持通配符）

        Args:
            path: 文件路径

        Returns:
            bool: 如果路径匹配返回 True
        """
        if not self.path_pattern:
            return True

        # 将通配符模式转换为正则表达式
        regex_pattern = self.path_pattern.replace('.', r'\.')  # 转义点号
        regex_pattern = regex_pattern.replace('*', '.*')  # * 匹配任意字符
        regex_pattern = regex_pattern.replace('?', '.')  # ? 匹配单个字符
        regex_pattern = f'^{regex_pattern}$'  # 完全匹配

        try:
            regex = re.compile(regex_pattern, re.IGNORECASE)
            return bool(regex.match(str(path)))
        except re.error as e:
            logger.error(f"Invalid path pattern '{self.path_pattern}': {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "path_pattern": self.path_pattern,
            "file_extensions": self.file_extensions,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "name_pattern": self.name_pattern
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleConditions':
        """从字典创建实例"""
        return cls(
            path_pattern=data.get("path_pattern"),
            file_extensions=data.get("file_extensions"),
            min_size=data.get("min_size"),
            max_size=data.get("max_size"),
            name_pattern=data.get("name_pattern")
        )


class Rule:
    """
    扫描规则类

    定义一个文件匹配规则，包含规则ID、名称、条件和风险级别。

    Attributes:
        id: 规则唯一标识符
        name: 规则名称
        description: 规则描述
        conditions: 规则条件对象
        risk_level: 风险等级
        enabled: 是否启用此规则
        category: 规则分类（如 "temp", "log", "cache"）
    """

    def __init__(
        self,
        id: str,
        name: str,
        conditions: RuleConditions,
        risk_level: RiskLevel = RiskLevel.L2_REVIEW,
        enabled: bool = True,
        description: Optional[str] = None,
        category: Optional[str] = None
    ):
        """
        初始化规则

        Args:
            id: 规则ID
            name: 规则名称
            conditions: 规则条件
            risk_level: 风险等级
            enabled: 是否启用
            description: 规则描述
            category: 规则分类
        """
        self.id = id
        self.name = name
        self.conditions = conditions
        self.risk_level = risk_level
        self.enabled = enabled
        self.description = description
        self.category = category

        logger.debug(f"Rule created: {id} - {name} (Risk: {risk_level.name})")

    def matches(self, file_info: FileInfo) -> bool:
        """
        检查文件是否匹配此规则

        Args:
            file_info: 文件信息对象

        Returns:
            bool: 如果规则启用且文件匹配条件返回 True
        """
        if not self.enabled:
            return False
        return self.conditions.matches(file_info)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions.to_dict(),
            "risk_level": self.risk_level.name,
            "enabled": self.enabled,
            "category": self.category
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            conditions=RuleConditions.from_dict(data.get("conditions", {})),
            risk_level=RiskLevel.from_string(data.get("risk_level", "L2_REVIEW")),
            enabled=data.get("enabled", True),
            category=data.get("category")
        )


class RuleMatch:
    """
    规则匹配结果类

    封装规则匹配的结果，包括匹配的规则、文件和原因。

    Attributes:
        rule: 匹配的规则对象（如果不匹配则为 None）
        file_info: 文件信息对象
        matched: 是否匹配
        reason: 匹配或不匹配的原因
    """

    def __init__(
        self,
        rule: Optional[Rule],
        file_info: FileInfo,
        matched: bool,
        reason: str = ""
    ):
        """
        初始化规则匹配结果

        Args:
            rule: 匹配的规则
            file_info: 文件信息
            matched: 是否匹配
            reason: 匹配原因
        """
        self.rule = rule
        self.file_info = file_info
        self.matched = matched
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "rule": self.rule.to_dict() if self.rule else None,
            "file_path": str(self.file_info.path),
            "matched": self.matched,
            "reason": self.reason
        }

    @property
    def risk_level(self) -> RiskLevel:
        """获取匹配规则的风险等级"""
        return self.rule.risk_level if self.rule else RiskLevel.L2_REVIEW


class RuleIndex:
    """
    规则索引器类

    对规则进行索引和分类，提高规则匹配效率。

    Attributes:
        rules_by_category: 按分类分组的规则字典
        rules_by_risk: 按风险等级分组的规则字典
        enabled_rules: 启用的规则列表
    """

    def __init__(self, rules: List[Rule]):
        """
        初始化规则索引

        Args:
            rules: 规则列表
        """
        self.rules_by_category: Dict[str, List[Rule]] = {}
        self.rules_by_risk: Dict[RiskLevel, List[Rule]] = {
            RiskLevel.L1_SAFE: [],
            RiskLevel.L2_REVIEW: [],
            RiskLevel.L3_SYSTEM: []
        }
        self.enabled_rules: List[Rule] = []

        self._index_rules(rules)
        logger.info(f"RuleIndex created with {len(self.enabled_rules)} enabled rules")

    def _index_rules(self, rules: List[Rule]) -> None:
        """
        对规则进行索引

        Args:
            rules: 规则列表
        """
        for rule in rules:
            # 按分类索引
            category = rule.category or "uncategorized"
            if category not in self.rules_by_category:
                self.rules_by_category[category] = []
            self.rules_by_category[category].append(rule)

            # 按风险等级索引
            self.rules_by_risk[rule.risk_level].append(rule)

            # 启用的规则
            if rule.enabled:
                self.enabled_rules.append(rule)

    def get_rules_by_category(self, category: str) -> List[Rule]:
        """
        获取指定分类的规则

        Args:
            category: 分类名称

        Returns:
            List[Rule]: 该分类的规则列表
        """
        return self.rules_by_category.get(category, [])

    def get_rules_by_risk(self, risk_level: RiskLevel) -> List[Rule]:
        """
        获取指定风险等级的规则

        Args:
            risk_level: 风险等级

        Returns:
            List[Rule]: 该风险等级的规则列表
        """
        return self.rules_by_risk.get(risk_level, [])

    def get_all_categories(self) -> List[str]:
        """
        获取所有分类名称

        Returns:
            List[str]: 分类名称列表
        """
        return list(self.rules_by_category.keys())


class RuleEngine:
    """
    规则引擎类

    实现文件规则匹配引擎，支持规则加载、文件匹配和风险评估。

    Attributes:
        rules: 所有规则列表
        rule_index: 规则索引器
        config_path: 规则配置文件路径

    Example:
        >>> engine = RuleEngine(Path("config/rules.json"))
        >>> engine.load_rules()
        >>> match = engine.match_file(file_info)
        >>> if match.matched:
        ...     print(f"Matched rule: {match.rule.name}")
    """

    def __init__(self, config_path: Path = Path("config/rules.json")):
        """
        初始化规则引擎

        Args:
            config_path: 规则配置文件路径
        """
        self.config_path = config_path
        self.rules: List[Rule] = []
        self.rule_index: Optional[RuleIndex] = None

        logger.info(f"RuleEngine initialized with config: {config_path}")

    def load_rules(self) -> None:
        """
        从配置文件加载规则

        读取 JSON 格式的规则配置文件并创建规则对象。

        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: JSON 格式错误
            ValueError: 规则数据格式错误
        """
        if not self.config_path.exists():
            logger.warning(f"Rules config file not found: {self.config_path}")
            # 创建默认规则
            self._create_default_rules()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.rules.clear()
            for rule_data in config.get('rules', []):
                try:
                    rule = Rule.from_dict(rule_data)
                    self.rules.append(rule)
                except Exception as e:
                    logger.error(f"Failed to load rule {rule_data.get('id', 'unknown')}: {e}")

            self.rule_index = RuleIndex(self.rules)
            logger.info(f"Loaded {len(self.rules)} rules from {self.config_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rules config: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            raise

    def _create_default_rules(self) -> None:
        """
        创建默认规则集

        当配置文件不存在时，创建一组常用的清理规则。
        """
        default_rules = [
            Rule(
                id="temp_files",
                name="临时文件",
                description="Windows 临时文件",
                conditions=RuleConditions(
                    file_extensions=[".tmp", ".temp"]
                ),
                risk_level=RiskLevel.L1_SAFE,
                category="temp"
            ),
            Rule(
                id="log_files",
                name="日志文件",
                description="应用程序日志文件",
                conditions=RuleConditions(
                    file_extensions=[".log", ".log1", ".log2"]
                ),
                risk_level=RiskLevel.L2_REVIEW,
                category="logs"
            ),
            Rule(
                id="cache_files",
                name="缓存文件",
                description="浏览器和应用缓存",
                conditions=RuleConditions(
                    file_extensions=[".cache", ".cache2"]
                ),
                risk_level=RiskLevel.L1_SAFE,
                category="cache"
            )
        ]

        self.rules = default_rules
        self.rule_index = RuleIndex(self.rules)
        logger.info(f"Created {len(self.rules)} default rules")

    def match_file(self, file_info: FileInfo) -> RuleMatch:
        """
        匹配文件到规则

        遍历所有启用的规则，返回第一个匹配的规则。

        Args:
            file_info: 文件信息对象

        Returns:
            RuleMatch: 规则匹配结果对象

        Example:
            >>> match = engine.match_file(file_info)
            >>> if match.matched:
            ...     print(f"Risk level: {match.risk_level}")
        """
        if not self.rule_index:
            logger.warning("Rule index not initialized, loading rules")
            self.load_rules()

        # 遍历启用的规则
        for rule in self.rule_index.enabled_rules:
            if rule.matches(file_info):
                logger.debug(f"File {file_info.path.name} matched rule {rule.id}")
                return RuleMatch(
                    rule=rule,
                    file_info=file_info,
                    matched=True,
                    reason=f"Matched rule: {rule.name}"
                )

        # 没有匹配的规则
        return RuleMatch(
            rule=None,
            file_info=file_info,
            matched=False,
            reason="No matching rule found"
        )

    def evaluate_risk(self, match: RuleMatch) -> RiskLevel:
        """
        评估文件的风险等级

        根据规则匹配结果评估文件的风险等级。

        Args:
            match: 规则匹配结果对象

        Returns:
            RiskLevel: 风险等级枚举值
        """
        if not match.matched or match.rule is None:
            # 没有匹配规则，默认为需要审查
            return RiskLevel.L2_REVIEW

        return match.rule.risk_level

    def get_rules_by_risk(self, risk_level: RiskLevel) -> List[Rule]:
        """
        获取指定风险等级的所有规则

        Args:
            risk_level: 风险等级

        Returns:
            List[Rule]: 该风险等级的规则列表
        """
        if not self.rule_index:
            self.load_rules()

        return self.rule_index.get_rules_by_risk(risk_level)

    def get_all_rules(self) -> List[Rule]:
        """
        获取所有规则

        Returns:
            List[Rule]: 所有规则列表
        """
        return self.rules.copy()

    def get_enabled_rules(self) -> List[Rule]:
        """
        获取所有启用的规则

        Returns:
            List[Rule]: 启用的规则列表
        """
        if not self.rule_index:
            self.load_rules()

        return self.rule_index.enabled_rules.copy()

    def add_rule(self, rule: Rule) -> None:
        """
        添加新规则

        Args:
            rule: 规则对象
        """
        self.rules.append(rule)
        self.rule_index = RuleIndex(self.rules)
        logger.info(f"Added rule: {rule.id}")

    def remove_rule(self, rule_id: str) -> bool:
        """
        移除规则

        Args:
            rule_id: 规则ID

        Returns:
            bool: 成功移除返回 True，规则不存在返回 False
        """
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                self.rule_index = RuleIndex(self.rules)
                logger.info(f"Removed rule: {rule_id}")
                return True
        return False

    def save_rules(self) -> None:
        """
        保存规则到配置文件

        将当前所有规则保存为 JSON 格式的配置文件。
        """
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            config = {
                "version": "1.0",
                "rules": [rule.to_dict() for rule in self.rules]
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.rules)} rules to {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
            raise


def test_rule_engine():
    """
    RuleEngine Test Function

    Tests rule loading, file matching, risk evaluation and rule management.
    """
    import tempfile

    print("=" * 60)
    print("RuleEngine Test")
    print("=" * 60)

    # Test 1: RiskLevel enum
    print("\n[Test 1] RiskLevel enum")
    assert RiskLevel.L1_SAFE.value == 0, "L1_SAFE value should be 0"
    assert RiskLevel.L2_REVIEW.value == 1, "L2_REVIEW value should be 1"
    assert str(RiskLevel.L3_SYSTEM) == "L3_SYSTEM", "String representation failed"
    print("  [OK] RiskLevel enum works")

    # Test 2: RuleConditions
    print("\n[Test 2] RuleConditions")
    conditions = RuleConditions(
        file_extensions=[".tmp", ".log"],
        min_size=0,
        max_size=1024*1024  # 1MB
    )

    # Create test file info
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.tmp"
        test_file.write_text("test content")

        from src.models.scan_result import FileInfo
        import time
        file_info = FileInfo(
            path=test_file,
            size=test_file.stat().st_size,
            is_dir=False,
            modified_time=time.time()
        )

        assert conditions.matches(file_info), "Should match file extension"
        print("  [OK] RuleConditions matching works")

    # Test 3: Rule creation and matching
    print("\n[Test 3] Rule creation")
    rule = Rule(
        id="test_rule",
        name="Test Rule",
        conditions=conditions,
        risk_level=RiskLevel.L1_SAFE,
        category="test"
    )

    assert rule.id == "test_rule", "Rule ID should be set"
    assert rule.matches(file_info), "Rule should match file"
    print("  [OK] Rule creation works")

    # Test 4: RuleEngine
    print("\n[Test 4] RuleEngine")
    engine = RuleEngine(Path("config/test_rules.json"))
    engine.load_rules()  # Load default rules first

    # Add test rule
    engine.add_rule(rule)
    assert len(engine.get_all_rules()) == 4, "Should have 4 rules (3 default + 1 test)"
    print(f"  [OK] Engine has {len(engine.get_all_rules())} rules")

    # Test 5: File matching
    print("\n[Test 5] File matching")
    match = engine.match_file(file_info)
    assert match.matched, "File should match a rule"
    assert match.risk_level == RiskLevel.L1_SAFE, "Risk level should be L1_SAFE"
    print(f"  [OK] File matched rule: {match.rule.name}")

    # Test 6: Get rules by risk
    print("\n[Test 6] Get rules by risk level")
    safe_rules = engine.get_rules_by_risk(RiskLevel.L1_SAFE)
    print(f"  [OK] Found {len(safe_rules)} L1_SAFE rules")

    # Test 7: Rule serialization
    print("\n[Test 7] Rule serialization")
    rule_dict = rule.to_dict()
    rule2 = Rule.from_dict(rule_dict)
    assert rule.id == rule2.id, "Rule serialization failed"
    print("  [OK] Rule serialization works")

    # Test 8: Save and load rules
    print("\n[Test 8] Save and load rules")
    engine.save_rules()
    engine2 = RuleEngine(Path("config/test_rules.json"))
    engine2.load_rules()
    assert len(engine2.get_all_rules()) == len(engine.get_all_rules()), "Rules count mismatch"
    print("  [OK] Save and load works")

    # Cleanup
    Path("config/test_rules.json").unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("[OK] All RuleEngine tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_rule_engine()
