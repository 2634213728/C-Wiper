
# C-Wiper：Windows 轻量化清理与分析工具概要设计文档

**版本：** v1.0 (Draft)
**日期：** 2023-10
**文档状态：** 待评审

---

## 1. 引言 (Introduction)

### 1.1 项目背景

Windows 系统的 C 盘随着使用时间的推移，会堆积大量临时文件、更新缓存以及应用残留数据（AppData）。现有的清理工具（如 CCleaner）往往体积庞大、包含广告或后台驻留进程。用户急需一款**绿色、开源、透明且具备决策辅助能力**的轻量化工具。

### 1.2 核心目标

1. **轻量化 (Lightweight):** 单文件执行 (EXE)，无安装，无后台服务，启动即用，用完即走。
2. **决策辅助 (Decision Support):** 不仅仅是“一键清理”，而是通过可视化的分析报告，告诉用户“什么占用了空间”以及“能否安全删除”。
3. **安全性 (Safety First):** 默认操作为“移至回收站”，配合严格的白名单机制，杜绝误删系统关键文件。

---

## 2. 系统架构 (System Architecture)

采用 **MVC (Model-View-Controller)** 变体架构，实现界面展示与底层逻辑的解耦。

### 2.1 技术栈 (Tech Stack)

* **开发语言:** Python 3.10+
* **GUI 框架:** Tkinter (原生库，保证体积最小) 或 CustomTkinter (可选，为了美观)
* **核心库:**
* `os`, `pathlib`: 文件系统遍历
* `send2trash`: 实现安全删除（移入回收站）
* `ctypes`: 调用 Windows API (检查管理员权限、DPI 适配)
* `threading`: 实现扫描任务异步化，防止界面卡死


* **构建工具:** Nuitka (编译为 C 代码，实现高性能与极小体积)
* **配置存储:** JSON (存储扫描规则与白名单)

---

## 3. 功能模块设计 (Functional Modules)

系统主要由四大功能模块组成：

### 3.1 核心扫描模块 (Core Scanner)

* **靶点扫描 (Targeted Scan):** 不进行全盘盲扫，基于预设的高频垃圾路径列表（如 `%Temp%`, `%SoftwareDistribution%`）进行精准打击。
* **多线程处理:** 扫描过程在独立线程运行，主线程负责 UI 刷新（进度条、状态文本）。

### 3.2 规则决策引擎 (Rule Engine)

* 负责将扫描到的文件与 `rules.json` 进行匹配。
* **风险分级:**
* 🟢 **L1 (Safe):** 临时文件、日志、浏览器缓存 -> 默认勾选。
* 🟡 **L2 (Review):** 下载目录、大文件、未知应用数据 -> 默认不勾选，需人工确认。
* 🔴 **L3 (System):** 系统核心文件 -> 仅显示分析结果，禁止操作。



### 3.3 应用空间分析器 (AppAnalyzer) - *[重点特性]*

* **功能:** 关联 `Program Files` (程序本体) 与 `AppData` (用户数据)，生成空间占用对比报告。
* **价值:** 帮助用户发现那些“本体很小，缓存巨大”的应用（如微信、Chrome）。

### 3.4 清理执行器 (Cleaner Executor)

* **双重确认:** 在执行前弹出汇总弹窗（文件数、释放空间）。
* **安全删除:** 调用系统回收站接口。
* **容错处理:** 遇到文件占用 (PermissionError/FileInUse) 自动跳过并记录日志，不中断流程。

---

## 4. 详细设计 (Detailed Design)

### 4.1 数据结构设计：规则库 (`rules.json`)

```json
{
  "scan_targets": [
    {
      "id": "win_temp",
      "name": "Windows 临时文件",
      "path": "C:\\Windows\\Temp",
      "risk": 0,
      "description": "系统运行时产生的临时数据，可安全删除。"
    },
    {
      "id": "chrome_cache",
      "name": "Chrome 缓存",
      "path": "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache",
      "risk": 0
    }
  ],
  "whitelist_extensions": [".docx", ".xlsx", ".pdf", ".key"],
  "protected_paths": ["C:\\Windows\\System32", "C:\\Windows\\SysWOW64"]
}

```

### 4.2 核心逻辑：应用空间分析器 (AppAnalyzer)

本模块通过**目录名启发式聚合算法**，解决 C 盘空间不明占用的痛点。

#### 4.2.1 扫描区域

1. **Static Zone (本体):** `C:\Program Files`, `C:\Program Files (x86)`
2. **Dynamic Zone (数据):** `%LOCALAPPDATA%`, `%APPDATA%`

#### 4.2.2 聚合逻辑

1. 遍历 Static Zone 获取一级目录名（如 `Adobe`），记录大小。
2. 遍历 Dynamic Zone 获取一级目录名，记录大小。
3. **匹配合并:** 如果名称相同（忽略大小写），则归为一个 `AppCluster` 对象。
4. **孤儿数据识别:** 若 Dynamic Zone 存在巨大文件夹但在 Static Zone 无对应（且非系统目录），标记为“可能的卸载残留”。

#### 4.2.3 输出对象

```python
class AppCluster:
    name: str          # e.g., "Tencent"
    program_size: int  # e.g., 500 MB
    data_size: int     # e.g., 15 GB
    ratio: float       # data_size / program_size
    suggestion: str    # "建议使用应用内清理"

```

---

## 5. UI/UX 设计 (User Interface)

界面采用单窗口布局，分为三个主要状态。

### 5.1 仪表盘 (Dashboard)

* **视觉中心:** 一个环形进度条，显示 C 盘当前使用率。
* **操作:** 巨大的 "开始分析" 按钮。
* **状态:** 显示 "管理员模式: [开启/关闭]"。

### 5.2 分析报告页 (Analysis Report)

扫描完成后自动跳转至此页，包含两个标签页 (Tab)：

* **Tab 1: 垃圾清理 (Trash Cleaner)**
* Treeview 列表，按类别分组（系统垃圾、浏览器缓存）。
* 每行包含：复选框 | 类别 | 路径 | 大小 | 风险颜色标签。
* 底部：清理按钮（显示预计释放空间）。


* **Tab 2: 应用洞察 (App Insights)**
* **Top 10 占用排行:** 堆叠条形图（蓝色=程序，红色=数据）。
* **异常提示:** 高亮显示数据体积 > 程序体积 5 倍的应用。
* **操作:** 此处不提供直接删除，而是提供 "打开文件夹" 按钮，引导用户人工处理。



---

## 6. 安全与权限策略 (Safety & Security)

1. **UAC 提权检测:**
* 程序启动时检测 `IsUserAnAdmin()`。
* 若为 False，扫描路径自动降级（跳过 `Windows\Temp` 等受限目录），并在 UI 提示“以管理员运行可清理更多垃圾”。


2. **关键目录硬编码保护:**
* 代码内部维护一份 `Critical_Paths` 列表，即使规则库被篡改，程序也会在删除前进行最后一道路径校验，禁止删除系统根目录。


3. **异常捕获:**
* 针对 `PermissionError` (无权限) 和 `OSError` (文件被占用) 进行静默处理，统计失败数量并在清理报告中展示，避免弹窗打断用户。



---

## 7. 开发路线图 (Roadmap)

| 阶段 | 目标 | 关键功能点 |
| --- | --- | --- |
| **Phase 1: MVP** | **可用性验证** | 基础 UI、Python `send2trash` 集成、扫描指定 Temp 目录、列表展示。 |
| **Phase 2: 核心增强** | **规则与分析** | 实现 JSON 规则引擎、**集成 AppAnalyzer 模块**、区分红绿灯风险等级。 |
| **Phase 3: 体验优化** | **交互与分发** | 多线程防卡死、UI 美化 (CustomTkinter)、Nuitka 打包优化体积。 |
| **Phase 4: 进阶** | **高级功能** | 空文件夹清理、大文件可视化图表、自动更新规则库。 |

---