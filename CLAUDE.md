# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供指导。

## 项目概览

Auto-tools — 统一的 Python GUI 自动化工具平台，面向 Windows。

单一入口 `main.py`，tkinter GUI。所有工具通过 `core/tool_base.py` 定义的 `Tool` 协议注册到 `ToolRegistry`，支持流水线串联执行。

## 运行方式

```bash
pip install -r requirements.txt
python main.py
```

## 架构

```
core/          — 平台核心：Tool 协议、注册表、流水线引擎、预设系统
ui/            — tkinter GUI：主窗口、流水线编辑器、预设对话框、组件
tools/         — 11 个工具，每个实现 Tool 协议，末尾调用 ToolRegistry.register()
main.py        — 导入所有工具，启动 MainWindow
presets/       — 用户保存的流水线预设 (JSON)
```

### 关键设计决策

- **所有工具实现 `Tool` 协议** (`core/tool_base.py`) — 包含 `name`, `name_slug`, `category`, `input_mode`, `params_type()`, `validate_params()`, `run()`
- **ToolRegistry** 是全局单例注册点 — `get_by_slug()` / `get_by_category()` 用于查找工具
- **流水线引擎** (`core/pipeline.py`) 纯数据处理，不涉及 UI — 目录选择在主线程完成后才传给引擎，引擎内部使用临时目录隔离，原图零修改
- **ParamForm** (`ui/widgets/param_form.py`) 根据 ToolParams dataclass 字段类型自动生成 tkinter 表单
- **预设系统** (`core/preset.py`) 序列化流水线步骤为 JSON，通过 ToolRegistry 反序列化还原
- **`InputMode`** 区分工具类型：`DIRECTORY`（可入流水线）、`NONE`（独立运行，如爬虫/转换）

### 添加新工具

1. 在 `tools/` 下创建新 `.py` 文件
2. 定义 `XxxParams(ToolParams)` dataclass
3. 定义 `XxxTool(Tool)` 类，设置 `name/name_slug/icon/category/input_mode`
4. 实现 `params_type()`, `run()`, 可选的 `validate_params()`
5. 文件末尾调用 `ToolRegistry.register(XxxTool())`
6. 在 `main.py` 中添加 `import tools.new_tool  # noqa: F401`
7. ParamForm 自动为 ToolParams 的每个字段生成对应控件

## 工具清单

| slug | name | category | input_mode | 依赖 |
|---|---|---|---|---|
| `image_rename` | 批量重命名 | image | DIRECTORY | Pillow |
| `image_watermark` | 文字水印 | image | DIRECTORY | Pillow |
| `image_compress` | 批量压缩 | image | DIRECTORY | Pillow |
| `pdf_merge` | PDF 合并 | pdf | DIRECTORY | pypdf |
| `pdf_split` | PDF 拆分 | pdf | DIRECTORY | pypdf |
| `pdf_extract_text` | 提取 PDF 文本 | pdf | DIRECTORY | pypdf |
| `pdf_rotate` | PDF 旋转 | pdf | DIRECTORY | pypdf |
| `pdf_to_word` | PDF → Word | pdf | NONE | pdf2docx |
| `word_to_pdf` | Word → PDF | pdf | NONE | docx2pdf |
| `crawler_beginner` | 入门爬虫 | web | NONE | requests, beautifulsoup4 |
| `crawler_intermediate` | 中级爬虫 | web | NONE | requests, beautifulsoup4 |

## 编码约定

- Python 3.10+，工具文件使用 `from __future__ import annotations`，UI 层（param_form.py）不使用（因需运行时类型检测）
- tkinter 主线程安全：所有 filedialog/messagebox 必须在主线程调用
- 独立工具 (`InputMode.NONE`) 由 `ui/app.py` 在主线程弹文件对话框，复制到临时 work_dir，再调用 `tool.run()`
- 流水线引擎 `execute_pipeline()` 不接受 UI 参数，由调用方在主线程选好目录后传入
- 输出目录通过 `Path.mkdir(parents=True, exist_ok=True)` 创建
- CSV 输出使用 `utf-8-sig` 编码（便于 Windows Excel 打开）
- 所有用户界面文字为中文
