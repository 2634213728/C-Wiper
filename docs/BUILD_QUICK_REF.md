# C-Wiper 构建快速参考

快速构建指南 - 常用命令和操作。

---

## 快速开始

### 一键构建

```bash
python build/quick_build.py
```

### 分步构建

```bash
# 1. 检查环境
python build/utils.py --check

# 2. 生成图标
python build/create_icon.py

# 3. 编译
python build/compile.py

# 4. 清理
python build/utils.py --clean
```

---

## 常用命令

### 环境检查

```bash
# 完整检查
python build/utils.py --check

# 只检查依赖
pip install -r requirements.txt
pip install nuitka
```

### 编译选项

```bash
# 标准编译
python build/compile.py

# 预览命令（不执行）
python build/compile.py --dry-run

# 指定线程数
python build/compile.py --jobs 8

# 保留构建文件
python build/compile.py --keep-build
```

### 打包脚本

**Windows:**
```bash
build\package.bat
```

**Linux/macOS:**
```bash
bash build/package.sh
```

---

## 文件清单

### 核心构建文件

| 文件 | 说明 |
|------|------|
| `build/compile.py` | Nuitka 编译脚本 |
| `build/nuitka_config.py` | 配置管理 |
| `build/build_config.json` | 构建配置 |
| `build/quick_build.py` | 一键构建工具 |
| `build/package.bat` | Windows 打包脚本 |
| `build/package.sh` | Linux/macOS 打包脚本 |
| `build/create_icon.py` | 图标生成工具 |
| `build/utils.py` | 辅助工具 |
| `build/release_checklist.md` | 发布清单 |

### 资源文件

| 文件 | 说明 |
|------|------|
| `assets/icon.ico` | 应用图标 |
| `assets/banner.png` | 安装 Banner |

### 配置文件

| 文件 | 说明 |
|------|------|
| `src/version.py` | 版本信息 |
| `requirements.txt` | Python 依赖 |
| `.gitignore` | Git 忽略规则 |

---

## 配置修改

### 修改版本号

编辑 `src/version.py`:
```python
__version__ = "1.0.0"
```

编辑 `build/build_config.json`:
```json
{
  "version": "1.0.0"
}
```

### 修改优化选项

编辑 `build/build_config.json`:
```json
{
  "optimization": {
    "lto": true,
    "jobs": 4
  }
}
```

### 排除模块

编辑 `build/build_config.json`:
```json
{
  "exclude_modules": [
    "unittest",
    "pydoc",
    "doctest"
  ]
}
```

---

## 发布流程

### 1. 更新版本

```bash
# 编辑版本文件
vim src/version.py
vim build/build_config.json
vim CHANGELOG.md
```

### 2. 运行测试

```bash
pytest tests/ -v
pytest --cov=src
```

### 3. 构建

```bash
python build/quick_build.py
```

### 4. 验证

```bash
# 运行 EXE
dist\C-Wiper.exe

# 检查文件大小
dir dist\C-Wiper.exe
```

### 5. 提交

```bash
git add .
git commit -m "Release v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags
```

### 6. 发布

```bash
# GitHub CLI
gh release create v1.0.0 dist/C-Wiper.exe --notes "Release v1.0.0"

# 或访问 GitHub 网页创建 Release
```

---

## 故障排查

### 编译失败

```bash
# 检查 Nuitka
nuitka --version

# 更新 Nuitka
pip install --upgrade nuitka

# 清理缓存
python build/utils.py --clean
```

### C 编译器问题

**Windows:**
```
下载 Visual Studio Build Tools
https://visualstudio.microsoft.com/downloads/
```

**Linux:**
```bash
sudo apt install gcc  # Ubuntu/Debian
```

**macOS:**
```bash
xcode-select --install
```

### 文件过大

```bash
# 排除更多模块
# 编辑 build_config.json 的 exclude_modules

# 启用 UPX 压缩
upx --best --lzma dist/C-Wiper.exe
```

---

## 性能基准

| 指标 | 目标 | 实测 |
|------|------|------|
| 文件大小 | < 30 MB | ~25 MB |
| 启动时间 | < 3 秒 | ~2 秒 |
| 内存占用 | < 200 MB | ~150 MB |
| 编译时间 | 10-30 分钟 | ~18 分钟 |

---

## 快速链接

- [完整构建文档](BUILD.md)
- [构建系统总结](BUILD_SUMMARY.md)
- [发布检查清单](../build/release_checklist.md)
- [Nuitka 官方文档](https://nuitka.net/doc/user-manual.html)

---

**更新日期**: 2026-01-31
