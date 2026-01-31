# C-Wiper UI 层使用说明

## 概述

C-Wiper UI 层基于 Tkinter 实现，提供完整的图形用户界面，包括主窗口、仪表盘、清理工具、空间分析和各类对话框。

## 组件结构

```
src/ui/
├── __init__.py           # 模块导出
├── main_window.py        # 主窗口框架
├── dashboard.py          # 仪表盘视图
├── cleaner_view.py       # 清理工具视图
├── analyzer_view.py      # 空间分析视图
└── dialogs.py            # 对话框组件
```

## 快速开始

### 1. 启动应用

```bash
# 直接运行
python main.py

# 或运行测试脚本
python test_ui.py
```

### 2. 主要功能

#### 主窗口（MainWindow）

- **菜单栏**：文件、编辑、视图、帮助
- **工具栏**：快速扫描、空间分析、管理员模式指示器
- **状态栏**：显示当前状态和操作进度
- **页面切换**：仪表盘、清理工具、空间分析

#### 仪表盘（Dashboard）

- **C盘使用率**：环形图显示使用情况
- **统计卡片**：临时文件、缓存文件、日志文件、回收站
- **快捷操作**：开始全面扫描、空间分析、设置

#### 清理工具（CleanerView）

- **扫描选项**：选择扫描目标（临时文件、缓存、日志、回收站）
- **结果列表**：TreeView 显示扫描结果
- **筛选排序**：按风险等级筛选、按大小/名称排序
- **批量操作**：全选、反选、清理选中文件

#### 空间分析（AnalyzerView）

- **应用列表**：显示所有应用程序
- **详细信息**：应用占用空间、文件数量、安装路径
- **空间图表**：Top 10 应用空间占比条形图
- **操作功能**：打开文件夹、查看文件列表、导出报告

#### 对话框（Dialogs）

- **ConfirmCleanDialog**：清理确认对话框
- **ProgressDialog**：进度显示对话框
- **ResultDialog**：结果展示对话框
- **ErrorDialog**：错误提示对话框

## 编程接口

### 使用主窗口

```python
import tkinter as tk
from src.controllers.scan_controller import ScanController
from src.controllers.clean_controller import CleanController
from src.controllers.analysis_controller import AnalysisController
from src.ui.main_window import MainWindow

# 创建控制器
scan_ctrl = ScanController()
clean_ctrl = CleanController()
analysis_ctrl = AnalysisController()

# 创建主窗口
root = tk.Tk()
app = MainWindow(root, scan_ctrl, clean_ctrl, analysis_ctrl)

# 启动主循环
root.mainloop()
```

### 使用对话框

```python
from src.ui.dialogs import ConfirmCleanDialog, ProgressDialog

# 清理确认对话框
dialog = ConfirmCleanDialog(parent, files=file_list, total_size=size)
dialog.wait_window()
if dialog.result:
    # 用户确认清理
    pass

# 进度对话框
progress = ProgressDialog(parent, message="正在扫描...", cancellable=True)
progress.update_progress(50, 100)  # 更新进度
progress.close()  # 关闭对话框
```

### 自定义视图

所有视图都继承自 `ttk.Frame`，可以方便地集成到自定义窗口中：

```python
from src.ui.dashboard import Dashboard

# 创建仪表盘视图
dashboard = Dashboard(parent_frame, main_window)
dashboard.pack(fill=tk.BOTH, expand=True)
```

## 事件系统

UI 层通过 EventBus 与控制器层通信：

```python
# 订阅事件
event_bus.subscribe(EventType.SCAN_PROGRESS, callback_function)

# 发布事件
event_bus.publish(Event(
    type=EventType.SCAN_COMPLETED,
    data={"total_files": 100}
))
```

## 样式自定义

UI 使用 Tkinter 样式系统，可以自定义主题：

```python
style = ttk.Style()
style.theme_use('clam')  # 使用 clam 主题

# 自定义样式
style.configure('Primary.TButton', font=('Microsoft YaHei UI', 10))
```

## 测试

### 运行测试

```bash
# 测试整个 UI 层
python test_ui.py

# 测试单个组件
python src/ui/main_window.py
python src/ui/dashboard.py
python src/ui/cleaner_view.py
python src/ui/analyzer_view.py
python src/ui/dialogs.py
```

### 手动测试

1. 启动应用：`python main.py`
2. 测试视图切换：点击工具栏按钮
3. 测试扫描功能：选择扫描目标并开始扫描
4. 测试清理功能：选择文件并执行清理
5. 测试分析功能：启动空间分析

## 常见问题

### Q: 窗口显示不正常？

A: 确保使用支持的屏幕分辨率（建议 1280x720 以上）

### Q: 字体显示问题？

A: UI 使用 Microsoft YaHei UI 字体，如未安装会自动降级

### Q: 如何更改主题颜色？

A: 修改 `MainWindow` 类中的颜色常量：
```python
COLOR_PRIMARY = "#2E86AB"  # 主色调
COLOR_SUCCESS = "#4CAF50"  # 成功色
COLOR_WARNING = "#FF9800"  # 警告色
COLOR_ERROR = "#F44336"    # 错误色
```

### Q: 如何添加新的视图？

A: 参考 `dashboard.py` 的实现：
```python
class MyView(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._create_ui()

    def _create_ui(self):
        # 创建UI组件
        pass
```

## 技术栈

- **GUI 框架**：Tkinter（Python 原生）
- **主题系统**：ttk.Style
- **布局管理**：pack、grid、place
- **事件驱动**：EventBus 发布-订阅模式
- **线程安全**：后台任务 + 事件通知

## 性能优化

- 使用 `update_idletasks()` 优化 UI 更新
- 长时间操作在后台线程执行
- 大数据列表使用虚拟化 Treeview
- 进度更新限制频率（避免卡顿）

## 开发规范

- 使用 Google 风格 Docstring
- 遵循 PEP 8 代码规范
- 事件处理函数使用 `_on_` 前缀
- UI 创建函数使用 `_create_` 前缀
- 辅助函数使用 `_` 前缀表示私有

## 后续计划

- [ ] 添加暗色主题支持
- [ ] 实现自定义快捷键
- [ ] 添加多语言支持
- [ ] 优化大数据显示性能
- [ ] 添加动画效果

## 维护者

C-Wiper 开发团队

## 许可证

MIT License
