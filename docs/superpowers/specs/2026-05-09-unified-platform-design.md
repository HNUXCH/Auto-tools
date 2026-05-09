# Auto-tools 统一平台设计

## 目标

将当前 8 个独立的 Python GUI 脚本重构为一个统一平台，支持用户自由排列工具组成流水线，保存/加载预设。

## 架构概览

```
auto-tools/
├── main.py                     # 单一入口
├── ui/                         # 统一 GUI 层
│   ├── app.py                  # 主窗口（工具箱 + 流水线编辑器）
│   ├── pipeline_editor.py      # 流水线步骤编排面板
│   ├── preset_dialog.py        # 预设保存/加载
│   └── widgets/                # 共享组件（进度条、参数面板等）
├── core/                       # 平台核心
│   ├── registry.py             # 工具注册表
│   ├── pipeline.py             # 流水线执行引擎
│   └── preset.py               # 预设数据模型
├── tools/                      # 每个工具实现统一接口
│   ├── base.py                 # 工具抽象接口定义
│   ├── image_rename.py
│   ├── image_watermark.py
│   ├── image_compress.py
│   ├── pdf_merge.py
│   ├── pdf_split.py
│   ├── pdf_extract_text.py
│   ├── pdf_rotate.py
│   ├── pdf_to_word.py
│   ├── word_to_pdf.py
│   ├── crawler_beginner.py
│   └── crawler_intermediate.py
├── presets/                    # 用户保存的预设文件（JSON）
└── requirements.txt            # 合并所有依赖
```

## 核心接口：`Tool` 协议

所有工具必须满足以下协议，平台只依赖此协议做统一调度。

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import threading
from typing import Callable, Protocol

@dataclass
class ToolParams:
    """每个工具声明自己的参数 dataclass。字段类型决定自动生成的表单控件。"""
    pass

@dataclass
class ToolResult:
    done: int
    total: int
    errors: list[str] = field(default_factory=list)

class Tool(Protocol):
    name: str           # 显示名，如 "批量重命名"
    name_slug: str      # 程序标识，如 "image_rename"
    icon: str           # 图标字符（emoji），如 "✏️"
    category: str       # 分类: "image" | "pdf" | "web"

    def params_type(self) -> type[ToolParams]: ...

    def validate_params(self, params: ToolParams) -> list[str]:
        """返回校验错误列表，空列表表示通过。"""
        ...

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: Callable[[int, int, str], None],
        cancel_event: threading.Event,
    ) -> ToolResult: ...
```

## 参数类型 → 控件映射

| dataclass 字段类型 | 生成的控件 |
|---|---|
| `str` | `ttk.Entry` |
| `int` | `ttk.Entry`（运行时校验整数） |
| `int` + `typing.Annotated[int, Min/Max]` | `ttk.Spinbox` |
| `float` | `ttk.Entry`（运行时校验浮点） |
| `Literal["a","b","c"]` | `ttk.Combobox`（只读） |
| `bool` | `ttk.Checkbutton` |
| `Path`（无标注） | `ttk.Entry` + 「浏览」按钮 |
| `Optional[X]` | 同 X，但字段可留空，值为 `None` |

平台通过 `dataclasses.fields(params_type())` 读取字段名、类型、默认值，递归构建参数表单。工具开发者零 UI 代码。

## 流水线引擎

### 数据模型

```python
@dataclass
class PipelineStep:
    tool: Tool
    params: ToolParams

@dataclass
class PipelineRun:
    steps: list[PipelineStep]
    cancel_event: threading.Event

@dataclass
class PipelineResult:
    success: bool
    step_results: list[tuple[str, ToolResult]]  # [(step_name, result), ...]
    logs: list[str]
```

### 执行流程

```
1. 验证：至少一个步骤；每个步骤调用 tool.validate_params(params)
2. 提示用户选择输入目录
3. 如果是最后一步需要输出，提示选择输出目录
4. 创建临时目录 work_dir，复制输入文件到 work_dir
5. for each step:
   a. 检查 cancel_event → 未取消则执行 tool.run(work_dir, params, ...)
   b. 收集 step_results、errors、更新进度条
   c. 步骤间 work_dir 串联（上一步输出是下一步输入）
6. 最后一步：如果不是纯输出步骤（如 pdf_to_word 已经自己写输出了），
   引擎负责将 work_dir 内容复制到用户输出目录
7. 汇总 PipelineResult
8. work_dir 自动清理
```

### 进度计算

流水线总进度 = 所有步骤等权重。步骤内进度 = `done/total`。总完成度 = `(当前步骤索引 * 每步权重 + 步骤内进度 * 每步权重) * 100`。

## 预设系统

### 格式（JSON）

```json
{
  "name": "产品图处理",
  "steps": [
    {
      "tool": "image_rename",
      "params": { "prefix": "product", "suffix": "", "start": "001" }
    },
    {
      "tool": "image_watermark",
      "params": { "text": "©MyShop", "position": "bottom-right", "font_size": 36, "opacity": 120 }
    },
    {
      "tool": "image_compress",
      "params": { "quality": 80, "max_width": 1920, "max_height": 1920 }
    }
  ]
}
```

### 操作

- **保存**：将当前 `PipelineRun.steps` 序列化为 JSON，写入 `presets/<name>.json`
- **加载**：通过 `registry.get_by_slug(step.tool)` 查找 Tool，用 `params_type()` 创建 dataclass 实例，填充字段值
- **删除**：删除对应 JSON 文件

## 工具注册表

```python
class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.name_slug] = tool

    @classmethod
    def get_all(cls) -> list[Tool]: ...

    @classmethod
    def get_by_slug(cls, slug: str) -> Tool: ...

    @classmethod
    def get_by_category(cls, category: str) -> list[Tool]: ...
```

每个工具模块末尾调用 `ToolRegistry.register(MyTool())`。`main.py` 启动时 import 所有工具模块完成注册。

## 主窗口布局

```
┌──────────────────────────────────────────┐
│  Auto-tools                    [_][□][X] │
├──────────────────────────────────────────┤
│  工具箱                                  │
│  ┌──────────┬──────────┬──────────┐      │
│  │  📷 图片  │  📄 PDF  │  🌐 网页  │     │
│  ├──────────┼──────────┼──────────┤      │
│  │ 批量重命名│ PDF 合并  │ 基础爬虫  │     │
│  │ 文字水印  │ PDF 拆分  │ 中级爬虫  │     │
│  │ 批量压缩  │ 提取文本  │          │      │
│  │          │ 旋转页面  │          │      │
│  │          │ PDF→Word │          │      │
│  │          │ Word→PDF │          │      │
│  └──────────┴──────────┴──────────┘      │
├──────────────────────────────────────────┤
│  流水线编辑器                             │
│  ┌────────────────────────────────────┐  │
│  │ 步骤 1: [✏️ 批量重命名      ▼] [×] │  │
│  │ 步骤 2: [💧 文字水印        ▼] [×] │  │
│  │ 步骤 3: [📦 批量压缩        ▼] [×] │  │
│  │ [+ 添加步骤]                       │  │
│  └────────────────────────────────────┘  │
├──────────────────────────────────────────┤
│  [▶ 执行] [📋 保存预设] [📂 加载预设]   │
│  ████████████████░░░░ 67%               │
│  正在执行：水印 12/50: product_012.jpg    │
└──────────────────────────────────────────┘
```

## 现有模块迁移清单

| 现有模块 | 新位置 | 迁移内容 |
|---|---|---|
| `image_renamer/main.py` | `tools/image_rename.py` | 提取 `batch_rename_images` 为 Tool 类 |
| `image_watermark/main.py` | `tools/image_watermark.py` | 提取 `process_batch`，补上字体检测 |
| `image_compress/main.py` | `tools/image_compress.py` | 提取 `compress_batch` 为 Tool 类 |
| `image_workflow/main.py` | **废弃** | 功能由流水线引擎替代 |
| `pdf_tools/main.py` | `tools/pdf_merge.py` `pdf_split.py` `pdf_extract_text.py` `pdf_rotate.py` | 拆为 4 个 Tool |
| `pdf_to_word/main.py` | `tools/pdf_to_word.py` | 提取核心函数为 Tool |
| `word_to_pdf/main.py` | `tools/pdf_to_pdf.py` | 提取核心函数为 Tool |
| `crawler_beginner/main.py` | `tools/crawler_beginner.py` | 提取爬虫逻辑为 Tool |
| `crawler_intermediate/main.py` | `tools/crawler_intermediate.py` | 提取爬虫逻辑为 Tool |

## 不涉及的内容

- 命令行支持（保持 GUI 定位）
- 暗色模式 / 换肤
- 多语言
- 自动更新
- 右键菜单集成
- 打包 .exe
