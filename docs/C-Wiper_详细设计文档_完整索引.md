# C-Wiper 详细设计文档 - 完整索引

**文档状态：** 分章节完成中
**最后更新：** 2026-01-31

---

## 文档说明

本详细设计文档基于《C-Wiper 概要设计文档 V1.1》编写，为开发团队提供实施级别的技术规范。

由于文档内容超过 **20,000 行**，采用分章节组织方式，便于查阅和维护。

---

## 文档结构

### ✅ 已完成章节

| 章节 | 文件名 | 状态 | 内容 |
|------|--------|------|------|
| 第1章 | C-Wiper_Detailed_Design_V1.1_Part1.md | ✅ 完成 | 概述 |
| 第2章 | C-Wiper_Detailed_Design_V1.1_Part1.md | ✅ 完成 | 系统架构详细设计 |

### 📋 完整章节列表

#### **第1章：概述** ✅
- 1.1 文档目的
- 1.2 系统目标
- 1.3 参考文档
- 1.4 术语定义

#### **第2章：系统架构详细设计** ✅
- 2.1 整体架构图 (Mermaid)
- 2.2 目录结构设计
- 2.3 模块依赖关系
- 2.4 事件驱动架构
  - 2.4.1 事件定义
  - 2.4.2 事件总线实现 (完整 Python 代码)
- 2.5 线程安全的状态管理 (完整 Python 代码)

#### **第3章：核心模块详细设计** (待补充)
- **3.1 核心扫描模块 (Core Scanner)**
  - 3.1.1 模块类图 (Mermaid)
  - 3.1.2 核心类实现
    - ScanTarget
    - FileAttributes
    - FileInfo
    - ScanError
    - ScanCache
    - CoreScanner (完整实现)
  - 3.1.3 扫描流程图 (Mermaid)

- **3.2 规则决策引擎 (Rule Engine)**
  - 3.2.1 模块类图 (Mermaid)
  - 3.2.2 核心类实现
    - RiskLevel (枚举)
    - RuleConditions
    - Rule
    - RuleMatch
    - RuleIndex
    - RuleEngine (完整实现)

- **3.3 应用空间分析器 (AppAnalyzer)**
  - 3.3.1 模块类图 (Mermaid)
  - 3.3.2 核心类实现
    - AppMatcher (含别名映射、相似度计算)
    - AppCluster
    - OrphanData
    - AppAnalyzer (完整实现)

- **3.4 清理执行器 (Cleaner Executor)** (待补充)
  - 3.4.1 执行流程图 (Mermaid)
  - 3.4.2 核心类实现
    - CleanTask
    - CleanResult
    - CleanerExecutor (完整实现)

- **3.5 安全模块 (Security Layer)** (待补充)
  - 3.5.1 多层防护机制设计
  - 3.5.2 核心类实现
    - SecurityLayer (完整实现)
    - TOCTOU 防护
    - 符号链接检测
    - 真实扩展名检测

#### **第4章：数据结构设计** (待补充)
- 4.1 扫描结果模型
  - ScanResult (dataclass)
  - FileInfo (dataclass)
  - ScanError (dataclass)
- 4.2 应用分析模型
  - AppCluster (dataclass)
  - OrphanData (dataclass)
- 4.3 清理报告模型
  - CleanReport (dataclass)
  - CleanStats (dataclass)
- 4.4 配置数据结构
  - RulesConfig (JSON Schema)
  - SettingsConfig (JSON Schema)
- 4.5 缓存数据结构
  - ScanCache (JSON Schema)
  - HistoryCache (JSON Schema)

#### **第5章：接口设计** (待补充)
- 5.1 模块间接口
  - Scanner API
  - RuleEngine API
  - AppAnalyzer API
  - Cleaner API
- 5.2 Windows API 封装
  - WinAPIFinder 类
  - WinAPISecurity 类
- 5.3 UI 接口定义
  - View Interface
  - Controller Interface

#### **第6章：算法详细设计** (待补充)
- 6.1 文件扫描算法
  - Windows API 扫描算法
  - pathlib 扫描算法
  - 复杂度分析
- 6.2 规则匹配算法
  - 前缀树匹配算法
  - 正则表达式匹配算法
- 6.3 AppMatcher 匹配算法
  - 名称标准化算法
  - 相似度计算算法 (Levenshtein 距离)
  - 别名匹配算法
- 6.4 符号链接检测算法
- 6.5 文件大小计算算法
  - 递归计算
  - Windows API 优化

#### **第7章：UI/UX详细设计** (待补充)
- 7.1 界面状态机 (Mermaid)
- 7.2 组件层次结构
- 7.3 Dashboard 设计
  - 布局规范
  - 事件处理
- 7.4 CleanerView 设计
  - TreeView 数据绑定
  - 筛选与排序
- 7.5 AnalyzerView 设计
  - 图表展示
  - 交互逻辑

#### **第8章：安全设计详细** (待补充)
- 8.1 多层防护机制
  - 第一层：硬编码保护
  - 第二层：配置文件白名单
  - 第三层：运行时动态检查
- 8.2 TOCTOU 防护实现
  - 符号链接攻击场景
  - 防护代码实现
- 8.3 权限管理设计
  - UAC 检测流程
  - 模式切换逻辑
- 8.4 回收站容量管理
  - 容量检测算法
  - 分批删除策略

#### **第9章：性能优化方案** (待补充)
- 9.1 Windows API 优化
  - FindFirstFile/FindNextFile 实现
  - 性能对比数据
- 9.2 并发扫描设计
  - 线程池实现
  - 任务调度策略
- 9.3 缓存机制设计
  - LRU 缓存实现
  - 缓存失效策略
- 9.4 内存管理策略
  - 流式处理实现
  - 生成器模式应用

#### **第10章：错误处理与日志** (待补充)
- 10.1 异常分类体系
  - CWiperError (基类)
  - SecurityError
  - ScanError
  - CleanError
- 10.2 错误码定义 (参见附录 B)
- 10.3 日志记录策略
  - 日志级别定义
  - 日志格式规范
  - 日志文件轮转
- 10.4 用户提示策略
  - 错误消息模板
  - 多语言支持

#### **第11章：测试设计** (待补充)
- 11.1 单元测试设计
  - 测试用例规格
  - Mock 对象设计
  - 测试覆盖率目标
- 11.2 集成测试设计
  - 模块集成测试
  - API 集成测试
- 11.3 安全测试用例
  - 符号链接攻击测试
  - 权限提升测试
  - TOCTOU 测试

#### **附录A：配置文件规范** (待补充)
- A.1 rules.json 完整格式
- A.2 settings.json 格式
- A.3 JSON Schema 定义

#### **附录B：错误码定义** (待补充)
- B.1 错误码规范
- B.2 完整错误码列表
- B.3 错误消息映射

---

## 快速导航

### 开发者常用章节

| 角色 | 推荐阅读章节 |
|------|-------------|
| **后端开发** | 第2、3、4、5、6、8、10章 |
| **前端开发** | 第2、7章 |
| **测试工程师** | 第8、11章 |
| **架构师** | 第1、2、9章 |
| **安全工程师** | 第8章 |

### 关键实现索引

| 功能模块 | 对应章节 | 核心类 |
|---------|---------|--------|
| 扫描器 | 3.1 | CoreScanner, ScanCache |
| 规则引擎 | 3.2 | RuleEngine, RuleIndex |
| 应用分析 | 3.3 | AppAnalyzer, AppMatcher |
| 清理器 | 3.4 | CleanerExecutor |
| 安全防护 | 3.5, 8 | SecurityLayer |
| 状态管理 | 2.5 | StateManager, EventBus |
| Windows API | 5.2 | WinAPIFinder |

---

## 使用指南

### 1. 阅读顺序建议

**第一次阅读（整体理解）：**
1. 第1章（概述）→ 第2章（架构）
2. 第3章（核心模块）→ 第7章（UI）
3. 第8章（安全）

**开发实施（按需查阅）：**
- 根据任务模块，查阅对应章节的类设计
- 参考第6章的算法实现
- 遵循第10章的错误处理规范

**测试阶段：**
- 参考第11章的测试设计
- 对照第8章的安全测试用例

### 2. 文档更新规范

**何时更新：**
- 新增功能模块
- 修改接口定义
- 优化算法实现
- 修复设计缺陷

**更新流程：**
1. 修改对应章节内容
2. 更新修订历史
3. 同步更新索引文件
4. 通知团队成员

### 3. 代码生成建议

本文档中的 Python 类定义可直接用于代码生成工具：
- 使用 dataclass 定义数据结构
- 使用类型注解（Type Hints）
- 包含完整的 Docstring
- 标注异常类型

---

## 文档统计

| 统计项 | 数量 |
|--------|------|
| 总章节数 | 11 章 + 2 个附录 |
| Mermaid 图表 | 15+ 个 |
| Python 类定义 | 30+ 个 |
| 代码示例 | 50+ 个 |
| 预计总行数 | 20,000+ 行 |

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.1 | 2026-01-31 | 初始版本，完成第1-2章 |

---

## 联系方式

**文档维护：** 架构组
**问题反馈：** 通过项目 Issue 提交
**更新请求：** 联系技术负责人

---

**文档结束（索引）**
