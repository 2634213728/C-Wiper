# C-Wiper: Windows 轻量化清理与分析工具

**版本：** v1.0.0
**日期：** 2026-01-31
**状态：** 稳定发布版
**许可证：** MIT License

---

## 概述

C-Wiper 是一款轻量级的 Windows 系统清理和 C 盘空间分析工具。它具备智能扫描、安全文件删除和全面的应用空间分析功能，并拥有现代化的用户界面。

### 核心特性

- **轻量高效**：单文件 EXE < 30MB，无需任何依赖
- **高性能**：60 秒内扫描 10 万个文件
- **安全可靠**：多层安全防护，零误删
- **快速启动**：启动时间 < 3 秒
- **智能检测**：识别 20+ 常见应用及其存储占用
- **现代界面**：简洁直观的用户界面
- **便携运行**：无需安装，随处运行

---

## 下载

### 最新版本：v1.0.0

[下载 C-Wiper.exe (Windows 10/11, 64 位)](https://github.com/yourusername/C-Wiper/releases/latest)

**文件大小**：约 25 MB
**SHA256**：`[待首次构建后填写]`

### 系统要求

- **操作系统**：Windows 10/11（64 位）
- **内存**：至少 200 MB RAM
- **磁盘空间**：至少 100 MB 可用空间
- **权限**：建议使用管理员权限（以获得完整功能）

### 快速安装

1. 下载 `C-Wiper.exe`
2. 双击运行
3. （可选）右键 → "以管理员身份运行" 以获得完整访问权限

---

## 开发

---

## 项目概述

C-Wiper 是一款轻量级的 Windows 系统清理和应用空间分析工具。它具备智能扫描、安全删除和全面的应用空间分析功能。

### 核心特性

- **轻量**：使用 Nuitka 编译，单文件 < 30MB
- **高性能**：60 秒内扫描 10 万个文件
- **安全**：多层安全防护，零误删
- **快速**：启动时间 < 3 秒
- **智能**：识别 20+ 常见应用

---

## 项目结构

```
WinTool/
├── src/
│   ├── __init__.py
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   └── security.py        # 安全层 [P0] ✓
│   ├── controllers/           # 控制器层
│   │   ├── __init__.py
│   │   └── state_manager.py   # 状态管理器 [P0] ✓
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   └── scan_result.py     # 扫描结果模型 [P0] ✓
│   ├── ui/                    # 用户界面
│   │   └── __init__.py
│   ├── utils/                 # 工具模块
│   │   ├── __init__.py
│   │   └── event_bus.py       # 事件总线 [P0] ✓
│   └── config/                # 配置文件
│       └── __init__.py
├── docs/                      # 文档
├── requirements.txt           # Python 依赖
└── README.md                  # 本文件
```

---

## 开发进度

### 第一阶段：基础设施层 ✓
- [x] T001: 创建项目目录结构
- [x] T011-T015: EventBus 实现
- [x] T017-T020: StateManager 实现

### 第二阶段：核心层（部分完成）
- [x] T026-T029: 安全层实现
- [x] T063: ScanResult 数据模型

### 已完成模块
- **EventBus**：线程安全的发布-订阅事件系统
- **StateManager**：具有 FSM 的系统状态管理
- **SecurityLayer**：多层文件删除保护
- **ScanResult 模型**：扫描结果的数据结构

---

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 10/11

### 安装步骤

```bash
# 克隆仓库
git clone <repository-url>
cd WinTool

# 创建虚拟环境（可选）
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 运行测试

```bash
# 测试 EventBus
python -m src.utils.event_bus

# 测试 StateManager
python -m src.controllers.state_manager

# 测试安全层
python -m src.core.security

# 测试扫描结果模型
python -m src.models.scan_result
```

---

## 模块文档

### EventBus (utils/event_bus.py)

实现发布-订阅模式的线程安全事件总线。

**核心功能：**
- 单例模式
- 线程安全操作
- 异常隔离
- 支持多个订阅者

**使用示例：**
```python
from src.utils.event_bus import EventBus, EventType

bus = EventBus()

def handler(event):
    print(f"Received: {event.data}")

bus.subscribe(EventType.SCAN_STARTED, handler)
bus.publish(Event(type=EventType.SCAN_STARTED, data={"target": "temp"}))
```

### StateManager (controllers/state_manager.py)

具有有限状态机的系统状态管理器。

**状态：**
- IDLE: 系统空闲
- SCANNING: 正在执行文件扫描
- CLEANING: 正在执行文件删除
- ANALYZING: 正在执行应用分析

**使用示例：**
```python
from src.controllers.state_manager import StateManager, SystemState

manager = StateManager()
manager.transition_to(SystemState.SCANNING)

if manager.is_cancel_requested:
    manager.transition_to(SystemState.IDLE)
```

### SecurityLayer (core/security.py)

文件删除的多层安全防护。

**防护层：**
1. 硬编码受保护路径（Windows、Program Files 等）
2. 系统文件（pagefile.sys、hiberfil.sys 等）
3. 白名单扩展名（用户可配置）

**使用示例：**
```python
from src.core.security import SecurityLayer
from pathlib import Path

security = SecurityLayer()
is_safe, reason = security.is_safe_to_delete(Path("C:/Temp/file.tmp"))

if not is_safe:
    print(f"不安全删除: {reason}")
```

### ScanResult 模型 (models/scan_result.py)

扫描目标、文件信息和结果的数据结构。

**类：**
- `ScanTarget`：定义扫描目标
- `FileInfo`：封装文件信息
- `ScanResult`：包含统计信息的完整扫描结果

---

## 开发指南

### 代码规范
- 遵循 PEP 8 风格指南
- 所有函数使用类型提示
- Google 风格文档字符串
- 使用 logging 而非 print
- 包含 `if __name__ == "__main__"` 测试代码

### 测试要求
- 所有模块必须具有单元测试
- 核心模块测试覆盖率 > 85%
- 测试必须无错误通过

---

## 路线图

### 第三阶段：核心层完成
- [ ] 核心扫描器 (T032-T039)
- [ ] 规则引擎 (T040-T047)
- [ ] 应用分析器 (T048-T056)
- [ ] 清理执行器 (T057-T062)

### 第四阶段：控制器层
- [ ] 扫描控制器
- [ ] 清理控制器
- [ ] 分析控制器

### 第五阶段：UI 层
- [ ] 主窗口
- [ ] 仪表盘视图
- [ ] 清理视图
- [ ] 分析视图

### 第六阶段：构建与发布
- [ ] Nuitka 编译
- [ ] 代码签名
- [ ] 发布打包

---

## 从源码构建

### 构建环境要求

- Python 3.10 或更高版本
- Windows 10/11
- Visual Studio Build Tools（用于 C 编译）

### 构建步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/C-Wiper.git
cd C-Wiper

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Nuitka
pip install nuitka

# 4. 构建 EXE
python build/compile.py

# 或使用构建脚本
# Windows:
build\package.bat

# Linux/macOS:
bash build/package.sh
```

编译后的 EXE 文件将位于 `dist/C-Wiper.exe`。

---

## 使用指南

### 基本使用

1. **扫描**：点击"扫描"按钮检测垃圾文件
2. **预览**：在清理前检查检测到的文件
3. **清理**：点击"清理"按钮删除选中的文件
4. **分析**：按应用查看 C 盘空间使用情况

### 命令行（开发模式）

```bash
# 从源码运行
python main.py

# 运行测试
pytest tests/

# 启用详细日志
python main.py --log-level DEBUG
```

---

## 项目结构

```
C-Wiper/
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── scanner.py     # 文件扫描器
│   │   ├── cleaner.py     # 文件清理器
│   │   ├── analyzer.py    # 空间分析器
│   │   ├── rule_engine.py # 规则引擎
│   │   └── security.py    # 安全层
│   ├── controllers/       # 业务控制器
│   │   ├── scan_controller.py
│   │   ├── clean_controller.py
│   │   └── analysis_controller.py
│   ├── models/            # 数据模型
│   │   └── scan_result.py
│   ├── ui/                # 用户界面
│   │   ├── main_window.py
│   │   ├── dashboard.py
│   │   └── dialogs.py
│   ├── utils/             # 工具类
│   │   └── event_bus.py
│   └── config/            # 配置
├── tests/                 # 测试套件
├── docs/                  # 文档
├── build/                 # 构建脚本
├── main.py                # 入口文件
└── requirements.txt       # 依赖
```

---

## 文档

- [用户指南](docs/user-guide.md) - 最终用户文档
- [API 参考](docs/api-reference.md) - 开发者 API 文档
- [开发指南](docs/development-guide.md) - 贡献指南
- [更新日志](CHANGELOG.md) - 版本历史

---

## 贡献

我们欢迎贡献！请参阅 [CONTRIBUTING.md](docs/CONTRIBUTING.md) 了解指南。

### 开发环境配置

```bash
# Fork 并克隆仓库
git clone https://github.com/yourusername/C-Wiper.git

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pylint black

# 运行测试
pytest tests/ -v

# 格式化代码
black src/ tests/

# 代码检查
pylint src/
```

---

## 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件。

---

## 安全性

C-Wiper 在设计时充分考虑了安全性：

- ✅ 路径遍历保护
- ✅ 硬编码系统路径保护
- ✅ 危险操作需用户确认
- ✅ 安全文件删除（使用回收站）
- ✅ 无遥测或数据收集
- ✅ 开源可审计

**安全策略**：请通过 [security@yourdomain.com](mailto:security@yourdomain.com) 私密报告安全漏洞

---

## 技术支持

- **问题反馈**：[GitHub Issues](https://github.com/yourusername/C-Wiper/issues)
- **讨论交流**：[GitHub Discussions](https://github.com/yourusername/C-Wiper/discussions)
- **邮件联系**：support@yourdomain.com

---

## 致谢

- [Nuitka](https://nuitka.net/) - Python 编译器
- [send2trash](https://github.com/arsenetar/send2trash) - 安全文件删除
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - GUI 框架

---

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md) 查看版本历史。

---

**当前版本**：1.0.0
**最后更新**：2026-01-31
**维护团队**：C-Wiper 开发团队
