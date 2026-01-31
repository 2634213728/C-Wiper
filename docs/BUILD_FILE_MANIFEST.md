# C-Wiper 构建系统文件清单

**创建日期**: 2026-01-31
**版本**: 1.0

---

## 目录结构

```
F:\aiProgram\WinTool/
├── build/                           # 构建脚本目录
│   ├── build_config.json           # 构建配置
│   ├── nuitka_config.py            # Nuitka 配置管理
│   ├── compile.py                  # 编译脚本
│   ├── package.bat                 # Windows 打包脚本
│   ├── package.sh                  # Linux/macOS 打包脚本
│   ├── quick_build.py              # 一键构建工具
│   ├── create_icon.py              # 图标生成工具
│   ├── utils.py                    # 构建辅助工具
│   └── release_checklist.md        # 发布检查清单
│
├── assets/                          # 资源文件目录
│   ├── icon.ico                    # 应用图标（待生成）
│   └── banner.png                  # 安装 Banner（待生成）
│
├── .github/workflows/               # GitHub Actions 目录
│   └── build.yml                   # CI/CD 配置
│
├── docs/                            # 文档目录
│   ├── BUILD.md                    # 完整构建文档
│   ├── BUILD_SUMMARY.md            # 构建系统总结
│   ├── BUILD_QUICK_REF.md          # 快速参考指南
│   └── BUILD_COMPLETION_REPORT.md  # 完成报告
│
├── src/                             # 源代码目录
│   └── version.py                  # 版本信息
│
├── CHANGELOG.md                     # 版本变更日志
├── LICENSE                          # MIT 许可证
├── README.md                        # 项目说明（已更新）
└── .gitignore                       # Git 忽略规则
```

---

## 文件详细说明

### 构建脚本 (build/)

#### 1. build_config.json
- **大小**: 831 bytes
- **类型**: JSON 配置文件
- **功能**: Nuitka 编译配置
- **关键配置**:
  - 版本号: 1.0.0
  - 输出目录: dist
  - 单文件打包: 是
  - 优化选项: LTO, 多线程

#### 2. nuitka_config.py
- **大小**: 4,904 bytes
- **类型**: Python 脚本
- **功能**: Nuitka 配置管理类
- **类**: NuitkaConfig
- **方法**:
  - get_nuitka_options()
  - get_main_script()
  - get_command()

#### 3. compile.py
- **大小**: 6,286 bytes
- **类型**: Python 脚本
- **功能**: Nuitka 编译脚本
- **命令行选项**:
  - --dry-run: 预览命令
  - --keep-build: 保留中间文件
  - --jobs N: 指定线程数

#### 4. package.bat
- **大小**: 2,333 bytes
- **类型**: Windows 批处理脚本
- **功能**: Windows 打包脚本
- **步骤**:
  1. 检查依赖
  2. 安装 Nuitka
  3. 清理旧构建
  4. 运行编译
  5. 创建 portable 版本

#### 5. package.sh
- **大小**: 2,640 bytes
- **类型**: Shell 脚本
- **功能**: Linux/macOS 打包脚本
- **兼容性**: Linux, macOS

#### 6. quick_build.py
- **大小**: 5,757 bytes
- **类型**: Python 脚本
- **功能**: 一键构建工具
- **流程**:
  1. 环境检查
  2. 清理构建
  3. 创建资源
  4. 编译打包
  5. 验证输出

#### 7. create_icon.py
- **大小**: 4,095 bytes
- **类型**: Python 脚本
- **功能**: 图标生成工具
- **依赖**: Pillow (可选)
- **输出**:
  - assets/icon.ico (多尺寸)
  - assets/banner.png (500x60)

#### 8. utils.py
- **大小**: 7,588 bytes
- **类型**: Python 脚本
- **功能**: 构建辅助工具
- **命令**:
  - --check: 检查环境
  - --clean: 清理构建

#### 9. release_checklist.md
- **大小**: 3,598 bytes
- **类型**: Markdown 文档
- **功能**: 发布检查清单
- **包含**:
  - 代码质量检查
  - 版本管理
  - 功能测试
  - 发布流程

### CI/CD 配置 (.github/workflows/)

#### build.yml
- **大小**: 3,389 bytes
- **类型**: YAML 配置
- **功能**: GitHub Actions 工作流
- **触发条件**:
  - Push to main/develop
  - Git Tag (v*)
  - Manual trigger
- **任务**:
  - Build job
  - Release job (仅 Tag)
  - Notify job

### 文档 (docs/)

#### BUILD.md
- **大小**: ~10 KB
- **类型**: Markdown 文档
- **功能**: 完整构建文档
- **内容**:
  - 环境要求
  - 构建步骤
  - 配置说明
  - 常见问题
  - 性能基准

#### BUILD_SUMMARY.md
- **大小**: ~8 KB
- **类型**: Markdown 文档
- **功能**: 构建系统总结
- **内容**:
  - 系统架构
  - 构建流程
  - 关键技术
  - 优化策略

#### BUILD_QUICK_REF.md
- **大小**: ~5 KB
- **类型**: Markdown 文档
- **功能**: 快速参考指南
- **内容**:
  - 快速开始
  - 常用命令
  - 文件清单
  - 故障排查

#### BUILD_COMPLETION_REPORT.md
- **大小**: ~12 KB
- **类型**: Markdown 文档
- **功能**: 构建完成报告
- **内容**:
  - 执行摘要
  - 已完成工作
  - 下一步行动
  - 项目统计

### 核心文件

#### src/version.py
- **类型**: Python 模块
- **功能**: 版本信息管理
- **导出**:
  - __version__
  - __author__
  - __build_date__
  - __license__

#### CHANGELOG.md
- **类型**: Markdown 文档
- **功能**: 版本变更记录
- **格式**: Keep a Changelog
- **内容**:
  - v1.0.0 功能列表
  - 未来计划

#### LICENSE
- **类型**: 文本文件
- **功能**: MIT 许可证
- **内容**: 完整 MIT 许可文本

#### README.md
- **类型**: Markdown 文档
- **功能**: 项目说明
- **更新内容**:
  - 下载链接
  - 安装说明
  - 运行要求
  - 构建指南

#### .gitignore
- **类型**: 文本文件
- **功能**: Git 忽略规则
- **排除**:
  - __pycache__
  - build/
  - dist/
  - *.pyc
  - .pytest_cache

---

## 文件统计

### 按类型

| 类型 | 数量 | 总大小 |
|------|------|--------|
| Python 脚本 (.py) | 5 | ~28 KB |
| 配置文件 (.json, .yml) | 2 | ~4 KB |
| 脚本文件 (.bat, .sh) | 2 | ~5 KB |
| 文档 (.md) | 5 | ~40 KB |
| 其他 (LICENSE, .gitignore) | 2 | ~2 KB |
| **总计** | **16** | **~79 KB** |

### 按目录

| 目录 | 文件数 | 说明 |
|------|--------|------|
| build/ | 9 | 构建脚本和配置 |
| .github/workflows/ | 1 | CI/CD 配置 |
| docs/ | 4 | 构建文档 |
| src/ | 1 | 版本信息 |
| 根目录 | 4 | LICENSE, CHANGELOG, README, .gitignore |

---

## 使用指南

### 首次使用

```bash
# 1. 检查环境
python build/utils.py --check

# 2. 生成图标（可选）
python build/create_icon.py

# 3. 一键构建
python build/quick_build.py
```

### 日常使用

```bash
# 快速构建
python build/compile.py

# 清理构建
python build/utils.py --clean

# 预览命令
python build/compile.py --dry-run
```

### 发布流程

```bash
# 1. 更新版本
vim src/version.py

# 2. 更新 CHANGELOG
vim CHANGELOG.md

# 3. 构建
python build/quick_build.py

# 4. 提交
git add .
git commit -m "Release v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 5. 发布
gh release create v1.0.0 dist/C-Wiper.exe
```

---

## 文件依赖关系

```
quick_build.py
    ├─→ utils.py (环境检查)
    ├─→ create_icon.py (资源生成)
    └─→ compile.py (编译)
            └─→ nuitka_config.py (配置)
                    └─→ build_config.json (配置)

package.bat/sh
    ├─→ compile.py
    └─→ 文件操作

GitHub Actions (build.yml)
    ├─→ 依赖安装
    ├─→ Nuitka 编译
    ├─→ 测试运行
    └─→ Release 创建
```

---

## 维护建议

### 定期更新

1. **依赖更新**
   ```bash
   pip install --upgrade nuitka
   pip freeze > requirements.txt
   ```

2. **版本更新**
   - 编辑 src/version.py
   - 编辑 build/build_config.json
   - 更新 CHANGELOG.md

3. **文档同步**
   - 保持 README.md 与 BUILD.md 同步
   - 及时更新 CHANGELOG.md

### 配置调整

1. **性能优化**
   - 编辑 build/build_config.json
   - 调整 optimization 参数

2. **模块排除**
   - 编辑 exclude_modules 列表
   - 减小文件大小

3. **编译选项**
   - 编辑 nuitka_config.py
   - 自定义 Nuitka 参数

---

## 常见路径

### 输入文件

| 文件 | 路径 |
|------|------|
| 主程序 | `main.py` |
| 版本信息 | `src/version.py` |
| 构建配置 | `build/build_config.json` |
| 图标 | `assets/icon.ico` |

### 输出文件

| 文件 | 路径 |
|------|------|
| EXE 文件 | `dist/C-Wiper.exe` |
| Portable 版本 | `dist/portable/` |
| 构建日志 | `build/*.build/` |

---

## 支持与帮助

### 文档

- [完整构建文档](BUILD.md)
- [快速参考](BUILD_QUICK_REF.md)
- [系统总结](BUILD_SUMMARY.md)
- [完成报告](BUILD_COMPLETION_REPORT.md)

### 外部资源

- [Nuitka 官方文档](https://nuitka.net/doc/user-manual.html)
- [Nuitka 性能指南](https://nuitka.net/pages/performance.html)
- [GitHub Actions 文档](https://docs.github.com/en/actions)

---

**文档版本**: 1.0
**最后更新**: 2026-01-31
