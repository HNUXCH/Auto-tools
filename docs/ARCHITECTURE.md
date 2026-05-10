# Auto-tools 技术文档

## 1. 项目概述

Auto-tools 是一个面向 Windows 平台的 Python GUI 自动化工具集。将图片处理、PDF 操作、网页抓取三大类工具整合到统一平台中，支持流水线编排、参数预设、自动表单生成。

**技术栈:** Python 3.10+, tkinter, Pillow, pypdf, pdf2docx, docx2pdf, requests, beautifulsoup4

**设计目标:**
- 零用户代码：参数表单由 dataclass 字段类型自动生成，无需手写 UI
- 原图零修改：所有批处理在临时目录执行，原文件不受影响
- 可组合流水线：任意 DIRECTORY 类型工具可自由串联
- 工具可扩展：新增工具只需实现 Tool 协议并注册，平台自动集成

---

## 2. 系统架构

```
┌──────────────────────────────────────────┐
│  main.py  — 导入所有工具，启动 GUI         │
├──────────────────────────────────────────┤
│  ui/  — 表示层                            │
│  ├── app.py           主窗口              │
│  ├── pipeline_editor.py  流水线编辑器      │
│  ├── preset_dialog.py    预设对话框        │
│  └── widgets/
│      ├── param_form.py    自动参数表单     │
│      └── progress_panel.py  进度面板       │
├──────────────────────────────────────────┤
│  core/  — 业务逻辑层                       │
│  ├── tool_base.py     Tool 协议定义        │
│  ├── registry.py      工具注册表           │
│  ├── pipeline.py      流水线引擎           │
│  └── preset.py        预设系统             │
├──────────────────────────────────────────┤
│  tools/  — 工具实现层                      │
│  ├── image_rename.py / image_watermark.py  │
│  ├── image_compress.py                     │
│  ├── pdf_merge.py / pdf_split.py           │
│  ├── pdf_extract_text.py / pdf_rotate.py   │
│  ├── pdf_to_word.py / word_to_pdf.py       │
│  └── crawler_beginner.py / crawler_intermediate.py │
└──────────────────────────────────────────┘
```

**依赖方向:** `main → ui → core ← tools`  
`tools` 和 `ui` 之间无直接依赖，通过 `core` 的接口解耦。

---

## 3. 核心接口

### 3.1 Tool 协议 (`core/tool_base.py`)

```python
class Tool:
    name: str              # 显示名，如 "批量重命名"
    name_slug: str         # 程序标识，如 "image_rename"
    icon: str              # emoji 图标
    category: str          # "image" | "pdf" | "web"
    input_mode: InputMode  # DIRECTORY（可入流水线）| NONE（独立运行）

    def params_type(self) -> type[ToolParams]: ...
    def validate_params(self, params: ToolParams) -> list[str]: ...
    def run(
        self,
        work_dir: Path,                                  # 临时工作目录
        params: ToolParams,                              # 参数
        on_progress: Callable[[int, int, str], None],    # 进度回调
        cancel_event: threading.Event,                   # 取消信号
    ) -> ToolResult: ...
```

### 3.2 InputMode 语义

| 模式 | 含义 | UI 行为 | 可入流水线 |
|------|------|---------|-----------|
| `DIRECTORY` | 处理 work_dir 中所有文件 | 显示"加入流水线"按钮 | 是 |
| `NONE` | 需要用户选择输入文件 | 显示"立即运行"按钮，主线程弹文件对话框，复制文件到 work_dir 后调用 run() | 否 |

### 3.3 ToolResult

```python
@dataclass
class ToolResult:
    done: int          # 成功处理数量
    total: int         # 总数量
    errors: list[str]  # 错误信息列表
```

---

## 4. 工具注册表 (`core/registry.py`)

全局单例，所有工具模块导入时通过 `ToolRegistry.register()` 自注册。

```python
class ToolRegistry:
    _tools: dict[str, Tool] = {}          # key = name_slug

    register(tool)                         # 注册工具
    get_by_slug(slug) -> Tool              # 按标识查找
    get_by_category(cat) -> list[Tool]     # 按分类查找
    get_all() -> list[Tool]                # 获取全部
```

每个工具文件末尾调用 `ToolRegistry.register(MyTool())`，`main.py` 通过 `import tools.xxx` 触发注册。

---

## 5. 流水线引擎 (`core/pipeline.py`)

### 设计原则

- **纯数据处理，不涉及 UI** — 所有目录选择、错误弹窗由 UI 层在主线程完成
- **临时目录隔离** — 输入文件复制到 `tempfile.TemporaryDirectory` 后执行，原文件零修改
- **步骤串联** — 上一步的 work_dir 直接作为下一步的输入

### 执行流程

```
UI 层 (_run, 主线程)
  ├─ validate_params() for each step
  ├─ filedialog.askdirectory() → input_dir
  ├─ filedialog.askdirectory() → output_dir
  └─ threading.Thread → _run_async (后台线程)
       └─ execute_pipeline(steps, input_dir, output_dir, cancel_event, on_status)
            ├─ _copy_files_to_work(input_dir → work/)    复制全部文件类型
            ├─ for each step:
            │    tool.run(work, params, _progress, cancel)
            │    ├─ on_progress() → 流水线进度百分比
            │    └─ collect ToolResult
            ├─ _copy_all_from_work(work/ → output_dir)   输出结果
            └─ return PipelineResult
```

### 进度计算

```
总进度 = (当前步骤索引 + 步骤内进度百分比) / 总步骤数 × 100
```

所有进度更新通过 `on_status` 回调推送到 UI 层，UI 层用 `root.after(0, ...)` 切换回主线程更新控件。

### 取消机制

- UI 层持有 `threading.Event`，通过参数传入 `execute_pipeline()`
- 每步开始前检查 `cancel_event.is_set()`
- 每个工具的 `run()` 内部也定期检查 `cancel_event`

---

## 6. 预设系统 (`core/preset.py`)

### 数据模型

```python
Preset {
    name: str
    steps: [
        {
            tool: "image_rename",
            params: {"prefix": "img", "suffix": "", "start": "001"}
        },
        ...
    ]
}
```

### 序列化流程

```
保存: PipelineStep → PresetStep(tool_slug, params.__dict__) → JSON
       └─ presets/<name>.json

加载: JSON → ToolRegistry.get_by_slug(tool_slug)
       → tool.params_type()(**params_dict)
       → PipelineStep(tool, params)
```

### 存储位置

`presets/` 目录，每个预设一个 `.json` 文件。文件名即为预设名。

---

## 7. 自动参数表单 (`ui/widgets/param_form.py`)

### 类型 → 控件映射

| dataclass 字段类型 | 生成的控件 | 说明 |
|---|---|---|
| `str` | `ttk.Entry` | 文本输入 |
| `int` | `ttk.Entry` | 数字输入，读取时自动转换 `int(raw)` |
| `float` | `ttk.Entry` | 浮点输入，读取时自动转换 |
| `bool` | `ttk.Checkbutton` | 复选框 |
| `Literal["a","b"]` | `ttk.Combobox` | 下拉选择（只读） |
| `Path` | `ttk.Entry` + 浏览按钮 | 目录选择器 |
| `Optional[X]` | 同 X 的控件 | 值可为空 |

### 类型解析

工具文件使用 `from __future__ import annotations` (PEP 563)，导致 `dataclasses.fields()` 返回的 `field.type` 是字符串（如 `"int"` 而非 `int`）。ParamForm 通过 `_resolve_type()` 函数将常见字符串类型映射回真实类型对象：

```python
def _resolve_type(raw):
    mapping = {"int": int, "str": str, "bool": bool, "float": float, "Path": Path}
    return mapping.get(raw, str)
```

### 读取表单值

`get_params()` 遍历所有字段，从对应的 `StringVar` / `BooleanVar` 读取值，对 `int`/`float` 类型做数值转换，最终构造 `params_cls(**kwargs)`。

---

## 8. 主窗口 (`ui/app.py`)

### 布局

```
┌──────────────────────────────┐
│  工具箱 (ttk.Notebook)        │
│  ┌─ 📷图片 ─┬─ 📄PDF ─┬─ 🌐网页 ─┐
│  │ 批量重命名│ PDF合并  │ 入门爬虫  │
│  │ 文字水印  │ PDF拆分  │ 中级爬虫  │
│  │ 批量压缩  │ ...      │          │
│  └──────────┴─────────┴──────────┘
├──────────────────────────────┤
│  流水线编辑器                   │
│  [工具选择 ▼] [+ 添加步骤]     │
│  步骤1: ✏️ 批量重命名  [参数][×]│
│  步骤2: 💧 文字水印    [参数][×]│
├──────────────────────────────┤
│  [▶ 执行] [⏹ 取消]           │
│  [📋 保存预设] [📂 加载预设]   │
│  ████████████░░░░ 67%         │
└──────────────────────────────┘
```

### 线程模型

| 操作 | 线程 | 说明 |
|------|------|------|
| GUI 交互、按钮点击 | 主线程 | tkinter 所有 UI 操作 |
| 文件对话框 | 主线程 | `_run()` / `_run_standalone()` 在启动后台线程前弹窗 |
| 工具执行 | 后台线程 | `tool.run()` 在线程池中运行 |
| 进度更新 | 后台→主线程 | `root.after(0, callback)` 切换回主线程 |
| messagebox | 主线程 | 完成/错误通知通过 `root.after(0, ...)` 延迟到主线程 |

### 取消流程

1. 用户点击"取消" → 主线程 `_cancel()` → `self._cancel_event.set()`
2. `self._cancel_event` 传入 `execute_pipeline()` / `tool.run()`
3. 工具内部检查 `cancel_event.is_set()` → 立即返回当前状态
4. UI 更新为"正在取消..."，按钮变灰

---

## 9. 工具详细规格

### 9.1 图片工具

#### image_rename — 批量重命名

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| prefix | str | `""` | 文件名前缀（可空） |
| suffix | str | `""` | 文件名后缀（可空） |
| start | str | `"001"` | 起始编号（纯数字） |

**处理逻辑:** 按字母序排列 → 临时名中转避免冲突 → 逐一重命名为 `prefix_N_suffix.ext`

#### image_watermark — 文字水印

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| text | str | `""` | 水印文字 |
| mode | str | `"single"` | `"single"` 单点 / `"tiled"` 满铺斜向 |
| position | str | `"bottom-right"` | 单点模式位置：center / top-left / top-right / bottom-left / bottom-right |
| angle | int | `30` | 满铺模式倾斜角度 (0-90) |
| spacing | int | `3` | 满铺模式间距倍数 (2-8)，越大越稀疏 |
| font_size | int | `36` | 字体大小（≥8） |
| opacity | int | `120` | 不透明度 (0-255) |

**满铺模式实现:**
1. 创建对角线长度 ×2 的方形 canvas
2. 以 `step = font_size × spacing` 为间距铺满文字
3. 旋转整个 canvas（默认 -30°，产生左下→右上的倾斜效果）
4. 裁剪中心区域至原图尺寸
5. Alpha composite 到原图

**字体查找策略:** 微软雅黑 → 黑体 → 宋体 → 楷体 → 仿宋 → Arial → PIL 默认

#### image_compress — 批量压缩

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| quality | int | `80` | JPEG 质量 (1-95) |
| max_width | int | `1920` | 最大宽度（像素） |
| max_height | int | `1920` | 最大高度（像素） |

**处理逻辑:** `Image.thumbnail(max_w, max_h)` 等比缩放 → JPEG 用指定质量，PNG 用 optimize，其他格式直接保存

### 9.2 PDF 工具

#### pdf_merge — PDF 合并

无参数。将 work_dir 中所有 PDF 按文件名排序 → 合并为 `merged.pdf` → 删除原始 PDF。

#### pdf_split — PDF 拆分

无参数。每个 PDF 的每一页拆分为 `{stem}_p001.pdf`, `{stem}_p002.pdf` ... → 删除原始 PDF。

#### pdf_extract_text — 提取 PDF 文本

无参数。每个 PDF 提取文本 → 输出 `{stem}.txt`（保留原始 PDF）。

#### pdf_rotate — PDF 旋转

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| degrees | int | `90` | 旋转角度，仅支持 90/180/270 |

写入临时 `.tmp` 文件后替换原文件。

#### pdf_to_word — PDF → DOCX

无参数。`InputMode.NONE` 独立运行。由 UI 层弹出文件对话框多选 PDF → 复制到 work_dir → 逐一转换 → 输出到用户选择目录。

**依赖 pdf2docx**（内含 PyMuPDF）。转换失败的文件跳过不打断整体。

#### word_to_pdf — DOCX → PDF

无参数。`InputMode.NONE` 独立运行。同上流程。

**依赖 docx2pdf**（需要本机安装 Microsoft Word）。

### 9.3 网页工具

#### crawler_beginner — 入门爬虫

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_pages | int | `3` | 抓取页数（≥1） |

**目标:** `quotes.toscrape.com`  
**输出:** `quotes_beginner.csv`（字段：quote, author, tags）  
`InputMode.NONE`，输出到用户选择的目录。

#### crawler_intermediate — 中级爬虫

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_pages | int | `5` | 抓取页数（≥1） |
| workers | int | `6` | 并发线程数（≥1） |

**目标:** `books.toscrape.com`  
**输出:** `books_intermediate.db` (SQLite) + `books_intermediate.csv`  
**特性:** 3 次重试、upsert 增量入库、线程池并发抓取详情页  
`InputMode.NONE`，输出到用户选择的目录。

---

## 10. 目录结构

```
auto-tools/
├── main.py                     # 入口：import 全部工具 → 启动 MainWindow
├── requirements.txt            # 合并依赖
├── CLAUDE.md                   # Claude Code 指导
├── README.md                   # 用户文档
├── docs/
│   └── ARCHITECTURE.md         # 本技术文档
├── core/
│   ├── __init__.py
│   ├── tool_base.py            # Tool 协议, ToolParams, ToolResult, InputMode
│   ├── registry.py             # ToolRegistry 全局单例
│   ├── pipeline.py             # PipelineStep, PipelineResult, execute_pipeline()
│   └── preset.py               # Preset, save/load/list/delete
├── ui/
│   ├── __init__.py
│   ├── app.py                  # MainWindow
│   ├── pipeline_editor.py      # PipelineEditor (ttk.LabelFrame)
│   ├── preset_dialog.py        # show_save/load_dialog()
│   └── widgets/
│       ├── __init__.py
│       ├── param_form.py       # ParamForm (dataclass → tkinter)
│       └── progress_panel.py   # ProgressPanel (进度条+状态+详情)
├── tools/
│   ├── __init__.py
│   ├── image_rename.py         # 批量重命名
│   ├── image_watermark.py      # 文字水印 (single + tiled)
│   ├── image_compress.py       # 批量压缩
│   ├── pdf_merge.py            # PDF 合并
│   ├── pdf_split.py            # PDF 拆分
│   ├── pdf_extract_text.py     # 提取 PDF 文本
│   ├── pdf_rotate.py           # PDF 旋转
│   ├── pdf_to_word.py          # PDF → DOCX
│   ├── word_to_pdf.py          # DOCX → PDF
│   ├── crawler_beginner.py     # 入门爬虫
│   └── crawler_intermediate.py # 中级爬虫
└── presets/
    └── .gitkeep                # 预设存储目录
```

---

## 11. 扩展指南：添加新工具

以添加一个 `png_to_jpg` 工具为例：

```python
# tools/png_to_jpg.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path, threading
from PIL import Image

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

IMAGE_EXTS = {".png"}

@dataclass
class PngToJpgParams(ToolParams):
    quality: int = 90

class PngToJpgTool(Tool):
    name = "PNG → JPG"
    name_slug = "png_to_jpg"
    icon = "🖼️"
    category = "image"
    input_mode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return PngToJpgParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: PngToJpgParams = params
        if not 1 <= p.quality <= 95:
            return ["质量需在 1-95 之间"]
        return []

    def run(self, work_dir, params, on_progress, cancel_event):
        p: PngToJpgParams = params
        images = sorted(
            [f for f in work_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: f.name.lower(),
        )
        errors = []
        done = 0
        for img_path in images:
            if cancel_event.is_set():
                break
            try:
                with Image.open(img_path) as img:
                    jpg = img.convert("RGB")
                    new_path = img_path.with_suffix(".jpg")
                    jpg.save(new_path, "JPEG", quality=p.quality)
                    img_path.unlink()  # 删除原 PNG
                    done += 1
            except Exception as exc:
                errors.append(f"转换失败 [{img_path.name}]: {exc}")
            on_progress(done, len(images), img_path.name)
        return ToolResult(done=done, total=len(images), errors=errors)

from core.registry import ToolRegistry
ToolRegistry.register(PngToJpgTool())
```

然后在 `main.py` 添加一行 `import tools.png_to_jpg  # noqa: F401`，完成。

ParamForm 自动识别 `PngToJpgParams` 的 `quality: int` 字段，生成带数值校验的输入框。无需任何 UI 代码。

---

## 12. 已知限制

| 限制 | 说明 |
|------|------|
| word_to_pdf 需要 Microsoft Word | docx2pdf 依赖本机安装的 Word |
| tkinter 外观 | 无暗色模式/现代主题，仅系统默认风格 |
| 仅 Windows | 字体检测、docx2pdf 等组件依赖 Windows |
| 无命令行模式 | 纯 GUI，不支持 CI/脚本调用 |
| 单实例 | 不支持多个流水线并行执行 |
| 无国际化 | 所有 UI 文字硬编码中文 |
