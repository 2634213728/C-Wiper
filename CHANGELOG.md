# Changelog

All notable changes to C-Wiper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-31

### Added
- 初始版本发布
- 扫描模块：支持系统垃圾文件扫描
- 清理模块：安全的文件删除功能
- 分析模块：存储空间分析和报告
- 规则引擎：可配置的清理规则
- 安全模块：文件路径验证和保护
- UI 界面：基于 Tkinter 的图形界面
- 控制器层：统一的业务逻辑管理
- 数据层：扫描结果数据模型

### Security
- 路径遍历保护
- 危险操作确认机制
- 管理员权限检测
- 安全文件删除（使用回收站）

### Performance
- 优化的扫描算法
- 多线程支持
- 内存优化
- 启动时间 < 3 秒

### Documentation
- 完整的用户文档
- API 文档
- 构建打包说明
- 发布检查清单

---

## [Unreleased]

### Planned
- 自动清理计划
- 更多清理规则
- 性能优化
- 多语言支持

---

## 版本说明

### 版本格式
- 主版本号.次版本号.修订号 (MAJOR.MINOR.PATCH)
- MAJOR: 不兼容的 API 变更
- MINOR: 向后兼容的功能新增
- PATCH: 向后兼容的问题修复

### 发布类型
- **Stable**: 稳定版本，适合生产环境
- **Beta**: 测试版本，功能完整但可能有问题
- **Alpha**: 早期版本，功能可能不完整

---

**更新日期**: 2026-01-31
