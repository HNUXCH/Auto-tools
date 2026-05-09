# Auto-tools 统一平台 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 8 个独立 GUI 脚本重构为统一平台，支持流水线编排、参数预设、自动表单生成。

**Architecture:** 所有工具实现 `Tool` 协议，`ToolRegistry` 负责注册发现，`PipelineEngine` 串联步骤执行。`ui/app.py` 提供工具箱面板 + 流水线编辑器。参数表单由 dataclass 字段类型自动生成。

**Tech Stack:** Python 3.10+, tkinter, Pillow, pypdf, pdf2docx, docx2pdf, requests, beautifulsoup4

---

## 文件结构

### 新建

```
core/
  __init__.py               # 空
  tool_base.py              # Tool 协议, ToolParams, ToolResult, InputMode
  registry.py               # ToolRegistry 类
  pipeline.py               # PipelineStep, PipelineRun, PipelineResult, execute()
  preset.py                 # save_preset(), load_preset(), list_presets(), delete_preset()
ui/
  __init__.py               # 空
  app.py                    # MainWindow（工具箱 + 流水线编辑器 + 按钮栏）
  pipeline_editor.py        # PipelineEditor 帧
  preset_dialog.py          # PresetDialog 弹窗
  widgets/
    __init__.py             # 空
    param_form.py           # ParamForm（dataclass → tkinter 表单）
    progress_panel.py       # ProgressPanel（进度条 + 状态 + 信息文本）
tools/
  __init__.py               # 空
  image_rename.py           # 批量重命名 Tool
  image_watermark.py        # 文字水印 Tool
  image_compress.py         # 批量压缩 Tool
  pdf_merge.py              # PDF 合并 Tool
  pdf_split.py              # PDF 拆分 Tool
  pdf_extract_text.py       # PDF 提取文本 Tool
  pdf_rotate.py             # PDF 旋转 Tool
  pdf_to_word.py            # PDF → DOCX Tool（独立运行）
  word_to_pdf.py            # DOCX → PDF Tool（独立运行）
  crawler_beginner.py       # 入门爬虫 Tool（独立运行）
  crawler_intermediate.py   # 中级爬虫 Tool（独立运行）
main.py                      # 入口
requirements.txt             # 合并依赖
presets/
  .gitkeep                   # 空目录占位
```

### 删除

```
image_compress/main.py, image_compress/README.md, image_compress/requirements.txt
image_renamer/main.py, image_renamer/README.md
image_watermark/main.py, image_watermark/README.md, image_watermark/requirements.txt
image_workflow/main.py, image_workflow/README.md, image_workflow/requirements.txt
pdf_tools/main.py, pdf_tools/README.md, pdf_tools/requirements.txt
pdf_to_word/main.py, pdf_to_word/README.md, pdf_to_word/requirements.txt
word_to_pdf/main.py, word_to_pdf/README.md, word_to_pdf/requirements.txt
crawler_beginner/main.py, crawler_beginner/README.md, crawler_beginner/requirements.txt
crawler_intermediate/main.py, crawler_intermediate/README.md, crawler_intermediate/requirements.txt
```

---

### Task 1: 基础目录和依赖

**Files:**
- Create: `core/__init__.py`, `ui/__init__.py`, `ui/widgets/__init__.py`, `tools/__init__.py`
- Create: `requirements.txt`
- Create: `presets/.gitkeep`

- [ ] **Step 1: 创建所有目录和 `__init__.py` 文件**

```bash
mkdir -p core ui/ui/widgets tools presets
touch core/__init__.py ui/__init__.py ui/widgets/__init__.py tools/__init__.py presets/.gitkeep
```

- [ ] **Step 2: 写 `requirements.txt`**

```text
Pillow>=10.0.0
pypdf>=4.0.0
pdf2docx>=0.5.0
docx2pdf>=0.1.0
requests>=2.31.0
beautifulsoup4>=4.12.0
```

- [ ] **Step 3: Commit**

```bash
git add core/ ui/ tools/ requirements.txt presets/.gitkeep
git commit -m "chore: create unified platform directory structure and combined requirements"
```

---

### Task 2: `core/tool_base.py` — Tool 协议

**Files:**
- Create: `core/tool_base.py`

- [ ] **Step 1: 写 `core/tool_base.py`**

```python
"""工具抽象接口 — 所有工具必须满足此协议。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import threading
from typing import Callable


class InputMode(Enum):
    DIRECTORY = auto()   # 批处理目录，流水线适用
    FILES = auto()       # 选择多个文件，独立运行
    NONE = auto()        # 无文件输入（如爬虫），独立运行


@dataclass
class ToolParams:
    """工具参数基类。子类用 dataclass 声明字段，平台自动生成表单。"""
    pass


@dataclass
class ToolResult:
    done: int
    total: int
    errors: list[str] = field(default_factory=list)


class Tool:
    """工具协议 — 平台只依赖此接口。

    子类必须提供:
      name: str         — 显示名
      name_slug: str    — 程序标识
      icon: str         — emoji 图标
      category: str     — "image" | "pdf" | "web"
      input_mode: InputMode — 输入模式

    子类必须实现:
      params_type() -> type[ToolParams]
      run(work_dir, params, on_progress, cancel_event) -> ToolResult
    """

    name: str
    name_slug: str
    icon: str
    category: str
    input_mode: InputMode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return ToolParams

    def validate_params(self, params: ToolParams) -> list[str]:
        """返回错误列表。空列表表示通过。子类可覆盖。"""
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: Callable[[int, int, str], None],
        cancel_event: threading.Event,
    ) -> ToolResult:
        raise NotImplementedError


# 类型别名，方便平台代码引用
ProgressCallback = Callable[[int, int, str], None]
```

- [ ] **Step 2: Commit**

```bash
git add core/tool_base.py
git commit -m "feat: define Tool protocol and ToolParams/ToolResult/InputMode"
```

---

### Task 3: `core/registry.py` — 工具注册表

**Files:**
- Create: `core/registry.py`

- [ ] **Step 1: 写 `core/registry.py`**

```python
"""工具注册表 — 单一全局注册点，按 slug / category 查找工具。"""

from __future__ import annotations

from .tool_base import Tool


class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        if tool.name_slug in cls._tools:
            raise ValueError(f"工具 {tool.name_slug} 已注册")
        cls._tools[tool.name_slug] = tool

    @classmethod
    def get_all(cls) -> list[Tool]:
        return list(cls._tools.values())

    @classmethod
    def get_by_slug(cls, slug: str) -> Tool:
        if slug not in cls._tools:
            raise KeyError(f"未找到工具: {slug}")
        return cls._tools[slug]

    @classmethod
    def get_by_category(cls, category: str) -> list[Tool]:
        return [t for t in cls._tools.values() if t.category == category]
```

- [ ] **Step 2: Commit**

```bash
git add core/registry.py
git commit -m "feat: add ToolRegistry for tool discovery by slug and category"
```

---

### Task 4: `core/preset.py` — 预设系统

**Files:**
- Create: `core/preset.py`

- [ ] **Step 1: 写 `core/preset.py`**

```python
"""预设系统 — 保存 / 加载 / 列出 / 删除流水线预设（JSON）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .registry import ToolRegistry

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"


@dataclass
class PresetStep:
    tool_slug: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Preset:
    name: str
    steps: list[PresetStep] = field(default_factory=list)


def _path(name: str) -> Path:
    return PRESETS_DIR / f"{name}.json"


def save_preset(preset: Preset) -> Path:
    """保存预设到 presets/<name>.json，覆盖同名文件。"""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "name": preset.name,
        "steps": [{"tool": s.tool_slug, "params": s.params} for s in preset.steps],
    }
    path = _path(preset.name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_preset(name: str) -> Preset:
    """从 JSON 加载预设，通过 ToolRegistry 还原每个步骤的 ToolParams。"""
    path = _path(name)
    if not path.exists():
        raise FileNotFoundError(f"预设文件不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    steps: list[PresetStep] = []
    for s in data["steps"]:
        tool = ToolRegistry.get_by_slug(s["tool"])
        params_cls = tool.params_type()
        params_instance = params_cls(**s["params"])
        steps.append(PresetStep(tool_slug=s["tool"], params=params_instance.__dict__))
    return Preset(name=data["name"], steps=steps)


def list_presets() -> list[str]:
    """返回预设名列表（不含 .json 扩展名）。"""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for p in PRESETS_DIR.glob("*.json"):
        names.append(p.stem)
    return sorted(names)


def delete_preset(name: str) -> bool:
    path = _path(name)
    if path.exists():
        path.unlink()
        return True
    return False
```

- [ ] **Step 2: Commit**

```bash
git add core/preset.py
git commit -m "feat: add preset save/load/list/delete system for pipeline configs"
```

---

### Task 5: `core/pipeline.py` — 流水线引擎

**Files:**
- Create: `core/pipeline.py`

- [ ] **Step 1: 写 `core/pipeline.py`**

```python
"""流水线引擎 — 串联多个 Tool 步骤，管理临时目录、进度、取消。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from .tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


@dataclass
class PipelineStep:
    tool: Tool
    params: ToolParams


@dataclass
class PipelineRun:
    steps: list[PipelineStep]
    cancel_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class PipelineResult:
    success: bool
    step_results: list[tuple[str, ToolResult]]
    logs: list[str]


def _copy_images_to_work(src: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in sorted(src.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            shutil.copy2(p, dst / p.name)
            count += 1
    return count


def _copy_all_from_work(work: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in work.iterdir():
        if p.is_file():
            shutil.copy2(p, dst / p.name)
            count += 1
    return count


def execute_pipeline(
    root: tk.Tk,
    steps: list[PipelineStep],
    on_status: ProgressCallback | None = None,
) -> PipelineResult | None:
    """执行流水线。提示目录选择、管理临时目录、串联步骤。返回 PipelineResult，用户取消返回 None。"""
    if not steps:
        messagebox.showerror("错误", "流水线至少需要一个步骤。", parent=root)
        return None

    # 验证参数
    for step in steps:
        errs = step.tool.validate_params(step.params)
        if errs:
            messagebox.showerror(
                f"参数错误 — {step.tool.name}",
                "\n".join(errs),
                parent=root,
            )
            return None

    # 选择目录
    input_dir = filedialog.askdirectory(parent=root, title="选择输入目录")
    if not input_dir:
        return None
    output_dir = filedialog.askdirectory(parent=root, title="选择输出目录")
    if not output_dir:
        return None

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    cancel = threading.Event()
    all_results: list[tuple[str, ToolResult]] = []
    logs: list[str] = []

    try:
        with tempfile.TemporaryDirectory(prefix="autotools_") as tmp:
            work = Path(tmp) / "work"
            file_count = _copy_images_to_work(input_path, work)
            if file_count == 0:
                messagebox.showinfo("提示", "输入目录没有支持的图片文件。", parent=root)
                return None
            logs.append(f"已加载 {file_count} 个文件")

            total_steps = len(steps)
            for idx, step in enumerate(steps):
                if cancel.is_set():
                    logs.append(f"⚠ 用户取消于步骤: {step.tool.name}")
                    break

                # 步骤级进度回调
                def _progress(i: int, t: int, name: str) -> None:
                    pct = ((idx + i / max(t, 1)) / total_steps) * 100
                    detail = f"{step.tool.name} {i}/{t}: {name}"
                    if on_status:
                        on_status(min(int(pct), 100), t, detail)

                result = step.tool.run(work, step.params, _progress, cancel)
                all_results.append((step.tool.name, result))
                logs.append(f"{step.tool.name}: 完成 {result.done}/{result.total}")
                if result.errors:
                    logs.append(f"  ⚠ {len(result.errors)} 个错误:")
                    logs.extend(f"    {e}" for e in result.errors[:5])
                    if len(result.errors) > 5:
                        logs.append(f"    ... 及 {len(result.errors) - 5} 项")

            if not cancel.is_set():
                out_count = _copy_all_from_work(work, output_path)
                logs.append(f"输出到 {output_path} ({out_count} 个文件)")

    except Exception as exc:
        logs.append(f"流水线异常: {exc}")
        return PipelineResult(success=False, step_results=all_results, logs=logs)

    return PipelineResult(
        success=not cancel.is_set(),
        step_results=all_results,
        logs=logs,
    )
```

- [ ] **Step 2: Commit**

```bash
git add core/pipeline.py
git commit -m "feat: add pipeline engine with temp-dir isolation and progress tracking"
```

---

### Task 6: `ui/widgets/param_form.py` — 自动参数表单

**Files:**
- Create: `ui/widgets/param_form.py`

- [ ] **Step 1: 写 `ui/widgets/param_form.py`**

```python
"""自动参数表单 — 根据 ToolParams dataclass 的字段类型自动构建 tkinter 表单。"""

from __future__ import annotations

import dataclasses
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, get_args, get_origin

from core.tool_base import ToolParams

# 从 typing.Literal 提取字面量值
try:
    from typing import Literal  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import Literal


class ParamForm(ttk.Frame):
    """根据 ToolParams 的子类 dataclass 自动生成表单。"""

    def __init__(self, parent: tk.Widget, params_cls: type[ToolParams]) -> None:
        super().__init__(parent)
        self._params_cls = params_cls
        self._widgets: dict[str, tk.Widget] = {}
        self._stringvars: dict[str, tk.StringVar] = {}
        self._boolvars: dict[str, tk.BooleanVar] = {}

        pad = {"padx": 6, "pady": 3}
        for idx, field in enumerate(dataclasses.fields(params_cls)):
            label = ttk.Label(self, text=f"{field.name}:")
            label.grid(row=idx, column=0, sticky="e", **pad)

            widget = self._build_widget(field)
            widget.grid(row=idx, column=1, sticky="ew", **pad)
            self._widgets[field.name] = widget

        self.columnconfigure(1, weight=1)

    def _build_widget(self, field: dataclasses.Field) -> tk.Widget:
        field_type = field.type
        origin = get_origin(field_type)
        args = get_args(field_type)

        # Optional[X] → 内部类型 X
        if origin is type(None) or (origin in (type(None), type(None).__class__)):
            field_type = args[0]
            origin = get_origin(field_type)
            args = get_args(field_type)
        elif origin is not None and type(None) in args:
            args = tuple(a for a in args if a is not type(None))
            field_type = args[0]
            origin = get_origin(field_type)
            args = get_args(field_type)

        default = field.default if field.default is not dataclasses.MISSING else field.default_factory
        if default is not dataclasses.MISSING and callable(default):
            default = default()

        # Literal → Combobox
        if origin is Literal:
            values = list(args)
            sv = tk.StringVar(value=str(default) if default is not dataclasses.MISSING else values[0])
            self._stringvars[field.name] = sv
            cb = ttk.Combobox(self, textvariable=sv, values=values, state="readonly", width=22)
            return cb

        # bool → Checkbutton
        if field_type is bool:
            bv = tk.BooleanVar(value=bool(default) if default is not dataclasses.MISSING else False)
            self._boolvars[field.name] = bv
            cb = ttk.Checkbutton(self, variable=bv)
            return cb

        # int → Entry / Spinbox
        if field_type is int:
            init = str(default) if default is not dataclasses.MISSING else ""
            sv = tk.StringVar(value=init)
            self._stringvars[field.name] = sv
            e = ttk.Entry(self, textvariable=sv, width=24)
            return e

        # Path → Entry + 浏览按钮
        if field_type is Path:
            init = str(default) if default is not dataclasses.MISSING else ""
            sv = tk.StringVar(value=init)
            self._stringvars[field.name] = sv
            frame = ttk.Frame(self)
            e = ttk.Entry(frame, textvariable=sv, width=18)
            e.pack(side="left", fill="x", expand=True)
            btn = ttk.Button(
                frame, text="浏览", width=6,
                command=lambda sv=sv: self._browse_path(sv),
            )
            btn.pack(side="right", padx=(4, 0))
            return frame

        # str → Entry (default)
        init = str(default) if default is not dataclasses.MISSING else ""
        sv = tk.StringVar(value=init)
        self._stringvars[field.name] = sv
        e = ttk.Entry(self, textvariable=sv, width=24)
        return e

    @staticmethod
    def _browse_path(sv: tk.StringVar) -> None:
        path = filedialog.askdirectory(title="选择路径")
        if path:
            sv.set(path)

    def get_params(self) -> ToolParams:
        """读取表单值，返回 ToolParams 实例。"""
        kwargs: dict[str, Any] = {}
        for field in dataclasses.fields(self._params_cls):
            if field.name in self._boolvars:
                kwargs[field.name] = self._boolvars[field.name].get()
            elif field.name in self._stringvars:
                raw = self._stringvars[field.name].get()
                # 尝试转换为声明类型
                if field.type is int:
                    try:
                        kwargs[field.name] = int(raw)
                    except ValueError:
                        kwargs[field.name] = raw  # 让 validate 处理
                else:
                    kwargs[field.name] = raw
        return self._params_cls(**kwargs)
```

- [ ] **Step 2: Commit**

```bash
git add ui/widgets/param_form.py
git commit -m "feat: add auto-generated parameter form from ToolParams dataclass fields"
```

---

### Task 7: `ui/widgets/progress_panel.py` — 进度面板

**Files:**
- Create: `ui/widgets/progress_panel.py`

- [ ] **Step 1: 写 `ui/widgets/progress_panel.py`**

```python
"""进度面板 — 进度条 + 状态文本 + 详情文本。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ProgressPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.progress_var = tk.DoubleVar(value=0.0)
        self._bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self._bar.pack(fill="x", pady=(4, 2))

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status_var).pack()

        self.detail_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.detail_var, foreground="gray").pack()

    def update(self, percent: float, status: str, detail: str) -> None:
        self.progress_var.set(percent)
        self.status_var.set(status)
        self.detail_var.set(detail)

    def reset(self) -> None:
        self.progress_var.set(0)
        self.status_var.set("就绪")
        self.detail_var.set("")
```

- [ ] **Step 2: Commit**

```bash
git add ui/widgets/progress_panel.py
git commit -m "feat: add shared progress panel widget"
```

---

### Task 8: `ui/pipeline_editor.py` — 流水线编辑器

**Files:**
- Create: `ui/pipeline_editor.py`

- [ ] **Step 1: 写 `ui/pipeline_editor.py`**

```python
"""流水线编辑器 — 拖拽式添加/移除/排序工具步骤。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core.pipeline import PipelineStep
from core.tool_base import Tool, ToolParams


class PipelineEditor(ttk.LabelFrame):
    """流水线步骤编排面板。每个步骤：下拉选择工具 + 参数按钮 + 删除。"""

    def __init__(self, parent: tk.Widget, tools: list[Tool]) -> None:
        super().__init__(parent, text="流水线编辑器", padding=8)
        self._tools = {t.name_slug: t for t in tools}
        self._steps: list[PipelineStep] = []
        self._step_frames: list[ttk.Frame] = []

        self._controls = ttk.Frame(self)
        self._controls.pack(fill="x", pady=(0, 6))

        self._tool_var = tk.StringVar()
        # 初始默认值
        tool_names = [t.name for t in tools]
        if tool_names:
            self._tool_var.set(tool_names[0])
        cb = ttk.Combobox(
            self._controls, textvariable=self._tool_var,
            values=tool_names, state="readonly", width=20,
        )
        cb.pack(side="left", padx=(0, 6))

        ttk.Button(self._controls, text="+ 添加步骤", command=self._add_step).pack(side="left")

    def get_steps(self) -> list[PipelineStep]:
        return list(self._steps)

    def _add_step(self) -> None:
        name = self._tool_var.get()
        tool = self._tools.get(self._tool_name_to_slug(name))
        if tool is None:
            return
        params_cls = tool.params_type()
        params = params_cls()
        step = PipelineStep(tool=tool, params=params)
        self._steps.append(step)

        row = len(self._step_frames)
        frame = ttk.Frame(self)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text=f"{tool.icon} {tool.name}", width=22).pack(side="left")
        ttk.Button(frame, text="参数", width=5, command=lambda i=row: self._edit_params(i)).pack(side="right", padx=2)
        ttk.Button(frame, text="×", width=3, command=lambda i=row: self._remove_step(i)).pack(side="right")

        self._step_frames.append(frame)

    def _edit_params(self, index: int) -> None:
        from ui.widgets.param_form import ParamForm

        step = self._steps[index]
        params_cls = step.tool.params_type()

        dialog = tk.Toplevel(self)
        dialog.title(f"参数 — {step.tool.name}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        form = ParamForm(dialog, params_cls)
        form.pack(padx=12, pady=12, fill="both", expand=True)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))

        def _on_ok() -> None:
            step.params = form.get_params()
            errs = step.tool.validate_params(step.params)
            if errs:
                messagebox.showerror("参数错误", "\n".join(errs), parent=dialog)
                return
            dialog.destroy()

        ttk.Button(btn_frame, text="确定", command=_on_ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)
        dialog.bind("<Return>", lambda e: _on_ok())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _remove_step(self, index: int) -> None:
        del self._steps[index]
        self._step_frames[index].destroy()
        del self._step_frames[index]
        # 重新绑定 index
        for i, f in enumerate(self._step_frames):
            for child in f.winfo_children():
                if isinstance(child, ttk.Button):
                    if child.cget("text") == "参数":
                        child.configure(command=lambda idx=i: self._edit_params(idx))
                    elif child.cget("text") == "×":
                        child.configure(command=lambda idx=i: self._remove_step(idx))

    def _tool_name_to_slug(self, name: str) -> str:
        for t in self._tools.values():
            if t.name == name:
                return t.name_slug
        return ""
```

- [ ] **Step 2: Commit**

```bash
git add ui/pipeline_editor.py
git commit -m "feat: add pipeline editor with add/remove/configure steps"
```

---

### Task 9: `ui/preset_dialog.py` — 预设对话框

**Files:**
- Create: `ui/preset_dialog.py`

- [ ] **Step 1: 写 `ui/preset_dialog.py`**

```python
"""预设对话框 — 保存/加载/删除流水线预设。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core import preset
from core.pipeline import PipelineStep
from core.registry import ToolRegistry


def show_save_dialog(parent: tk.Widget, steps: list[PipelineStep]) -> None:
    """弹出保存预设对话框。"""
    if not steps:
        messagebox.showinfo("提示", "流水线为空，无法保存。", parent=parent)
        return

    dialog = tk.Toplevel(parent)
    dialog.title("保存预设")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    pad = {"padx": 10, "pady": 6}
    ttk.Label(dialog, text="预设名称:").pack(**pad)
    name_var = tk.StringVar()
    name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
    name_entry.pack(padx=10, pady=(0, 6))
    name_entry.focus()

    def _save() -> None:
        name = name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "预设名称不能为空。", parent=dialog)
            return
        p = preset.Preset(
            name=name,
            steps=[
                preset.PresetStep(
                    tool_slug=s.tool.name_slug,
                    params=s.params.__dict__,
                )
                for s in steps
            ],
        )
        path = preset.save_preset(p)
        messagebox.showinfo("已保存", f"预设已保存: {path}", parent=dialog)
        dialog.destroy()

    ttk.Button(dialog, text="保存", command=_save).pack(pady=(0, 10))
    dialog.bind("<Return>", lambda e: _save())
    dialog.bind("<Escape>", lambda e: dialog.destroy())


def show_load_dialog(parent: tk.Widget) -> list[PipelineStep] | None:
    """弹出加载预设对话框。返回 PipelineStep 列表或 None（取消）。"""
    names = preset.list_presets()
    if not names:
        messagebox.showinfo("提示", "没有已保存的预设。", parent=parent)
        return None

    dialog = tk.Toplevel(parent)
    dialog.title("加载预设")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    ttk.Label(dialog, text="选择预设:").pack(padx=12, pady=(12, 6))

    selection = tk.StringVar(value=names[0])
    lb = tk.Listbox(dialog, listvariable=tk.StringVar(value=names), height=min(8, len(names)), width=28)
    lb.pack(padx=12, pady=(0, 8))

    result: list[PipelineStep] | None = None

    def _load() -> None:
        nonlocal result
        sel = lb.curselection()
        if not sel:
            return
        name = names[sel[0]]
        p = preset.load_preset(name)
        steps: list[PipelineStep] = []
        for ps in p.steps:
            tool = ToolRegistry.get_by_slug(ps.tool_slug)
            params = tool.params_type()(**ps.params)
            steps.append(PipelineStep(tool=tool, params=params))
        result = steps
        dialog.destroy()

    def _delete() -> None:
        sel = lb.curselection()
        if not sel:
            return
        name = names[sel[0]]
        if messagebox.askyesno("确认", f"确定删除预设「{name}」？", parent=dialog):
            preset.delete_preset(name)
            messagebox.showinfo("已删除", f"预设「{name}」已删除。", parent=dialog)
            dialog.destroy()

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(0, 10))
    ttk.Button(btn_frame, text="加载", command=_load).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="删除", command=_delete).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)

    dialog.bind("<Escape>", lambda e: dialog.destroy())
    dialog.wait_window()
    return result
```

- [ ] **Step 2: Commit**

```bash
git add ui/preset_dialog.py
git commit -m "feat: add preset save/load/delete dialogs"
```

---

### Task 10: `ui/app.py` — 主窗口

**Files:**
- Create: `ui/app.py`

- [ ] **Step 1: 写 `ui/app.py`**

```python
"""Auto-tools 主窗口 — 工具箱面板 + 流水线编辑器 + 执行控制。"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from core.pipeline import PipelineStep, PipelineResult, execute_pipeline
from core.registry import ToolRegistry
from core.tool_base import InputMode

from .pipeline_editor import PipelineEditor
from .preset_dialog import show_load_dialog, show_save_dialog
from .widgets.progress_panel import ProgressPanel


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Auto-tools")
        root.geometry("580x520")
        root.minsize(480, 400)

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)

        # ── 工具箱区域 ──
        ttk.Label(outer, text="工具箱", font=("", 12, "bold")).pack(anchor="w", pady=(0, 4))
        self._build_toolbox(outer)

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=8)

        # ── 流水线编辑器 ──
        tools = ToolRegistry.get_all()
        self._editor = PipelineEditor(outer, tools)
        self._editor.pack(fill="both", expand=False, pady=(0, 6))

        # ── 进度面板 ──
        self._progress = ProgressPanel(outer)
        self._progress.pack(fill="x", pady=(0, 8))

        # ── 按钮栏 ──
        btn_bar = ttk.Frame(outer)
        btn_bar.pack(fill="x")

        self._run_btn = ttk.Button(btn_bar, text="▶ 执行", command=self._run)
        self._run_btn.pack(side="left", padx=2)

        self._cancel_btn = ttk.Button(btn_bar, text="⏹ 取消", command=self._cancel, state="disabled")
        self._cancel_btn.pack(side="left", padx=2)

        ttk.Button(btn_bar, text="📋 保存预设", command=self._save_preset).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="📂 加载预设", command=self._load_preset).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="退出", command=root.destroy).pack(side="right", padx=2)

        self._cancel_event = threading.Event()
        self._running = False

    # ── 工具箱 ──

    def _build_toolbox(self, parent: ttk.Frame) -> None:
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="x", pady=(0, 4))

        categories = ["image", "pdf", "web"]
        labels = ["📷 图片", "📄 PDF", "🌐 网页"]
        for cat, label in zip(categories, labels):
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=label)
            tools = ToolRegistry.get_by_category(cat)
            for t in tools:
                frame = ttk.Frame(tab)
                frame.pack(fill="x", padx=4, pady=2)

                ttk.Label(frame, text=f"{t.icon} {t.name}", width=20).pack(side="left")

                if t.input_mode == InputMode.DIRECTORY:
                    ttk.Button(
                        frame, text="加入流水线", width=10,
                        command=lambda tool=t: self._add_to_pipeline(tool),
                    ).pack(side="right")
                else:
                    ttk.Button(
                        frame, text="▶ 立即运行", width=10,
                        command=lambda tool=t: self._run_standalone(tool),
                    ).pack(side="right")

    def _add_to_pipeline(self, tool) -> None:
        # 临时设置 tool_var 为该工具名然后调用 editor._add_step
        name = tool.name
        self._editor._tool_var.set(name)
        self._editor._add_step()

    def _run_standalone(self, tool) -> None:
        from ui.widgets.param_form import ParamForm

        params_cls = tool.params_type()
        if dataclasses.fields(params_cls):
            dialog = tk.Toplevel(self.root)
            dialog.title(f"参数 — {tool.name}")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.resizable(False, False)

            form = ParamForm(dialog, params_cls)
            form.pack(padx=12, pady=12, fill="both", expand=True)

            result_params = None

            def _ok() -> None:
                nonlocal result_params
                p = form.get_params()
                errs = tool.validate_params(p)
                if errs:
                    messagebox.showerror("参数错误", "\n".join(errs), parent=dialog)
                    return
                result_params = p
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=(0, 10))
            ttk.Button(btn_frame, text="确定", command=_ok).pack(side="left", padx=4)
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)
            dialog.bind("<Return>", lambda e: _ok())
            dialog.bind("<Escape>", lambda e: dialog.destroy())
            dialog.wait_window()

            if result_params is None:
                return
        else:
            result_params = params_cls()

        self._enter_running()
        threading.Thread(
            target=self._run_standalone_async,
            args=(tool, result_params),
            daemon=True,
        ).start()

    def _run_standalone_async(self, tool, params) -> None:
        from pathlib import Path
        import tempfile

        try:
            with tempfile.TemporaryDirectory(prefix="autotools_") as tmp:
                work = Path(tmp) / "work"
                work.mkdir()

                def _progress(i: int, t: int, name: str) -> None:
                    pct = (i / max(t, 1)) * 100
                    self.root.after(0, lambda: self._progress.update(pct, tool.name, f"{i}/{t}: {name}"))

                result = tool.run(work, params, _progress, self._cancel_event)

            def _finish() -> None:
                self._enter_idle()
                if result.errors:
                    msg = f"完成 {result.done}/{result.total}\n⚠ {len(result.errors)} 个错误\n" + "\n".join(result.errors[:5])
                else:
                    msg = f"完成 {result.done}/{result.total}"
                messagebox.showinfo(tool.name, msg)

            self.root.after(0, _finish)
        except Exception as exc:
            self.root.after(0, lambda: self._finish_error(tool.name, str(exc)))
            self.root.after(0, self._enter_idle)

    # ── 执行 ──

    def _run(self) -> None:
        if self._running:
            return
        steps = self._editor.get_steps()
        if not steps:
            messagebox.showerror("提示", "流水线至少需要一个步骤。", parent=self.root)
            return

        self._enter_running()
        threading.Thread(target=self._run_async, args=(steps,), daemon=True).start()

    def _run_async(self, steps: list[PipelineStep]) -> None:
        result = execute_pipeline(
            self.root, steps,
            on_status=lambda p, t, d: self.root.after(0, lambda: self._progress.update(p, t, d)),
        )

        def _finish() -> None:
            self._enter_idle()
            if result is None:
                return
            if result.success:
                messagebox.showinfo("流水线完成", "\n".join(result.logs))
            else:
                messagebox.showerror("流水线未完成", "\n".join(result.logs))

        self.root.after(0, _finish)

    def _finish_error(self, title: str, msg: str) -> None:
        messagebox.showerror(title, msg)

    # ── 预设 ──

    def _save_preset(self) -> None:
        show_save_dialog(self.root, self._editor.get_steps())

    def _load_preset(self) -> None:
        steps = show_load_dialog(self.root)
        if steps:
            # 重建编辑器
            for _ in range(len(self._editor._step_frames)):
                self._editor._remove_step(0)
            for step in steps:
                self._editor._tool_var.set(step.tool.name)
                self._editor._add_step()
                self._editor._steps[-1].params = step.params

    # ── 状态 ──

    def _enter_running(self) -> None:
        self._cancel_event.clear()
        self._running = True
        self._run_btn.config(state="disabled")
        self._cancel_btn.config(state="normal")
        self._progress.reset()

    def _enter_idle(self) -> None:
        self._running = False
        self._run_btn.config(state="normal")
        self._cancel_btn.config(state="disabled")

    def _cancel(self) -> None:
        self._cancel_event.set()
        self._progress.update(0, "正在取消...", "")
        self._cancel_btn.config(state="disabled")

    def _finish_error(self, title: str, msg: str) -> None:
        self._enter_idle()
        messagebox.showerror(title, msg)
```

- [ ] **Step 2: Commit**

```bash
git add ui/app.py
git commit -m "feat: add main window with toolbox, pipeline editor, and execution control"
```

---

### Task 11: 迁移图片工具（image_rename, image_watermark, image_compress）

**Files:**
- Create: `tools/image_rename.py`, `tools/image_watermark.py`, `tools/image_compress.py`

- [ ] **Step 1: 写 `tools/image_rename.py`**

```python
"""批量重命名图片 Tool。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


@dataclass
class ImageRenameParams(ToolParams):
    prefix: str = ""
    suffix: str = ""
    start: str = "001"


class ImageRenameTool(Tool):
    name = "批量重命名"
    name_slug = "image_rename"
    icon = "✏️"
    category = "image"
    input_mode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return ImageRenameParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: ImageRenameParams = params
        if not p.start.isdigit():
            return ["起始编号必须为纯数字"]
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: ImageRenameParams = params
        images = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: f.name.lower(),
        )
        width = len(p.start)
        start_num = int(p.start)

        plans: list[tuple[Path, Path]] = []
        for i, old_path in enumerate(images):
            parts: list[str] = []
            if p.prefix:
                parts.append(p.prefix)
            parts.append(str(start_num + i).zfill(width))
            if p.suffix:
                parts.append(p.suffix)
            new_name = "_".join(parts) + old_path.suffix.lower()
            plans.append((old_path, old_path.with_name(new_name)))

        target_names = [new.name for _, new in plans]
        if len(target_names) != len(set(target_names)):
            return ToolResult(done=0, total=len(images), errors=["目标文件名冲突"])

        # 临时名中转
        temp_paths: list[tuple[Path, Path]] = []
        for idx, (old_path, _) in enumerate(plans):
            tmp = old_path.with_name(f"__wf_tmp_{idx}__{old_path.name}")
            old_path.rename(tmp)
            temp_paths.append((tmp, old_path))

        errors: list[str] = []
        renamed = 0
        for idx, (tmp, _) in enumerate(temp_paths):
            if cancel_event.is_set():
                break
            try:
                _, final_path = plans[idx]
                tmp.rename(final_path)
                renamed += 1
            except OSError as exc:
                errors.append(f"重命名失败 [{tmp.name}]: {exc}")
            on_progress(renamed, len(temp_paths), plans[idx][1].name)

        return ToolResult(done=renamed, total=len(temp_paths), errors=errors)


# 注册
from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(ImageRenameTool())
```

- [ ] **Step 2: 写 `tools/image_watermark.py`**

```python
"""批量文字水印 Tool。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
_CANDIDATE_FONTS = (
    "msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc",
    "simkai.ttf", "simfang.ttf", "arial.ttf",
)


def _find_font_path() -> str | None:
    font_dirs = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        for name in _CANDIDATE_FONTS:
            candidate = font_dir / name
            if candidate.exists():
                return str(candidate)
    return None


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    path = _find_font_path()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


@dataclass
class ImageWatermarkParams(ToolParams):
    text: str = ""
    position: str = "bottom-right"
    font_size: int = 36
    opacity: int = 120


class ImageWatermarkTool(Tool):
    name = "文字水印"
    name_slug = "image_watermark"
    icon = "💧"
    category = "image"
    input_mode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return ImageWatermarkParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: ImageWatermarkParams = params
        errs: list[str] = []
        if not p.text.strip():
            errs.append("水印文字不能为空")
        if p.font_size < 8:
            errs.append("字体大小不能小于 8")
        if not 0 <= p.opacity <= 255:
            errs.append("透明度必须在 0-255 之间")
        return errs

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: ImageWatermarkParams = params
        images = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: f.name.lower(),
        )
        font = _load_font(p.font_size)
        errors: list[str] = []
        done = 0

        for img_path in images:
            if cancel_event.is_set():
                break
            try:
                with Image.open(img_path) as img:
                    base = img.convert("RGBA")
                    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
                    draw = ImageDraw.Draw(overlay)
                    bbox = draw.textbbox((0, 0), p.text, font=font)
                    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x, y = self._calc_pos(base.width, base.height, w, h, p.position)
                    draw.text((x, y), p.text, font=font, fill=(255, 255, 255, p.opacity))
                    merged = Image.alpha_composite(base, overlay)
                    if img_path.suffix.lower() in {".jpg", ".jpeg"}:
                        merged.convert("RGB").save(img_path, quality=95)
                    else:
                        merged.save(img_path)
                    done += 1
            except Exception as exc:
                errors.append(f"水印失败 [{img_path.name}]: {exc}")
            on_progress(done, len(images), img_path.name)

        return ToolResult(done=done, total=len(images), errors=errors)

    @staticmethod
    def _calc_pos(bw: int, bh: int, mw: int, mh: int, pos: str, margin: int = 20) -> tuple[int, int]:
        if pos == "top-left":
            return margin, margin
        if pos == "top-right":
            return max(margin, bw - mw - margin), margin
        if pos == "bottom-left":
            return margin, max(margin, bh - mh - margin)
        if pos == "center":
            return max(0, (bw - mw) // 2), max(0, (bh - mh) // 2)
        return max(margin, bw - mw - margin), max(margin, bh - mh - margin)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(ImageWatermarkTool())
```

- [ ] **Step 3: 写 `tools/image_compress.py`**

```python
"""批量压缩图片 Tool。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

from PIL import Image

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


@dataclass
class ImageCompressParams(ToolParams):
    quality: int = 80
    max_width: int = 1920
    max_height: int = 1920


class ImageCompressTool(Tool):
    name = "批量压缩"
    name_slug = "image_compress"
    icon = "📦"
    category = "image"
    input_mode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return ImageCompressParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: ImageCompressParams = params
        errs: list[str] = []
        if not 1 <= p.quality <= 95:
            errs.append("JPEG 质量必须在 1-95 之间")
        if p.max_width < 1 or p.max_height < 1:
            errs.append("最大宽高必须为正整数")
        return errs

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: ImageCompressParams = params
        images = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: f.name.lower(),
        )
        errors: list[str] = []
        done = 0

        for img_path in images:
            if cancel_event.is_set():
                break
            try:
                with Image.open(img_path) as img:
                    out = img.copy()
                    out.thumbnail((p.max_width, p.max_height), Image.Resampling.LANCZOS)
                    if img_path.suffix.lower() in {".jpg", ".jpeg"}:
                        out.convert("RGB").save(img_path, quality=p.quality, optimize=True)
                    elif img_path.suffix.lower() == ".png":
                        out.save(img_path, optimize=True)
                    else:
                        out.save(img_path)
                    done += 1
            except Exception as exc:
                errors.append(f"压缩失败 [{img_path.name}]: {exc}")
            on_progress(done, len(images), img_path.name)

        return ToolResult(done=done, total=len(images), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(ImageCompressTool())
```

- [ ] **Step 4: Commit**

```bash
git add tools/image_rename.py tools/image_watermark.py tools/image_compress.py
git commit -m "feat: migrate image rename, watermark, compress tools to unified interface"
```

---

### Task 12: 迁移 PDF 批处理工具（merge, split, extract_text, rotate）

**Files:**
- Create: `tools/pdf_merge.py`, `tools/pdf_split.py`, `tools/pdf_extract_text.py`, `tools/pdf_rotate.py`

- [ ] **Step 1: 写 `tools/pdf_merge.py`**

```python
"""PDF 合并 Tool。"""

from __future__ import annotations

from pathlib import Path
import threading

from pypdf import PdfReader, PdfWriter

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


class PdfMergeTool(Tool):
    name = "PDF 合并"
    name_slug = "pdf_merge"
    icon = "📎"
    category = "pdf"
    input_mode = InputMode.DIRECTORY

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        pdf_files = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"],
            key=lambda f: f.name.lower(),
        )
        if not pdf_files:
            return ToolResult(done=0, total=0, errors=["输入目录没有 PDF 文件"])

        writer = PdfWriter()
        total_pages = 0
        for i, pdf in enumerate(pdf_files):
            if cancel_event.is_set():
                return ToolResult(done=i, total=len(pdf_files), errors=[])
            reader = PdfReader(str(pdf))
            for page in reader.pages:
                writer.add_page(page)
                total_pages += 1
            on_progress(i + 1, len(pdf_files), pdf.name)

        # 删除原文件，写入合并结果
        for pdf in pdf_files:
            pdf.unlink()
        output_pdf = work_dir / "merged.pdf"
        with output_pdf.open("wb") as f:
            writer.write(f)

        return ToolResult(done=len(pdf_files), total=len(pdf_files))


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfMergeTool())
```

- [ ] **Step 2: 写 `tools/pdf_split.py`**

```python
"""PDF 按页拆分 Tool。"""

from __future__ import annotations

from pathlib import Path
import threading

from pypdf import PdfReader, PdfWriter

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


class PdfSplitTool(Tool):
    name = "PDF 拆分"
    name_slug = "pdf_split"
    icon = "✂️"
    category = "pdf"
    input_mode = InputMode.DIRECTORY

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        pdf_files = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"],
            key=lambda f: f.name.lower(),
        )
        if not pdf_files:
            return ToolResult(done=0, total=0, errors=["输入目录没有 PDF 文件"])

        errors: list[str] = []
        total_processed = 0
        total_pages = 0

        for pdf in pdf_files:
            if cancel_event.is_set():
                break
            try:
                reader = PdfReader(str(pdf))
                for idx, page in enumerate(reader.pages, start=1):
                    writer = PdfWriter()
                    writer.add_page(page)
                    out_file = work_dir / f"{pdf.stem}_p{idx:03d}.pdf"
                    with out_file.open("wb") as f:
                        writer.write(f)
                    total_pages += 1
                pdf.unlink()  # 删除原始 PDF
                total_processed += 1
            except Exception as exc:
                errors.append(f"拆分失败 [{pdf.name}]: {exc}")
            on_progress(total_processed, len(pdf_files), pdf.name)

        return ToolResult(done=total_processed, total=len(pdf_files), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfSplitTool())
```

- [ ] **Step 3: 写 `tools/pdf_extract_text.py`**

```python
"""PDF 提取文本 Tool。"""

from __future__ import annotations

from pathlib import Path
import threading

from pypdf import PdfReader

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


class PdfExtractTextTool(Tool):
    name = "提取 PDF 文本"
    name_slug = "pdf_extract_text"
    icon = "📝"
    category = "pdf"
    input_mode = InputMode.DIRECTORY

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        pdf_files = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"],
            key=lambda f: f.name.lower(),
        )
        if not pdf_files:
            return ToolResult(done=0, total=0, errors=["输入目录没有 PDF 文件"])

        errors: list[str] = []
        done = 0
        for pdf in pdf_files:
            if cancel_event.is_set():
                break
            try:
                reader = PdfReader(str(pdf))
                parts: list[str] = []
                for i, page in enumerate(reader.pages, start=1):
                    text = page.extract_text() or ""
                    parts.append(f"===== Page {i} =====\n{text}\n")
                out_txt = work_dir / f"{pdf.stem}.txt"
                out_txt.write_text("\n".join(parts), encoding="utf-8")
                done += 1
            except Exception as exc:
                errors.append(f"提取失败 [{pdf.name}]: {exc}")
            on_progress(done, len(pdf_files), pdf.name)

        return ToolResult(done=done, total=len(pdf_files), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfExtractTextTool())
```

- [ ] **Step 4: 写 `tools/pdf_rotate.py`**

```python
"""PDF 旋转 Tool。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

from pypdf import PdfReader, PdfWriter

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


@dataclass
class PdfRotateParams(ToolParams):
    degrees: int = 90


class PdfRotateTool(Tool):
    name = "PDF 旋转"
    name_slug = "pdf_rotate"
    icon = "🔄"
    category = "pdf"
    input_mode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return PdfRotateParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: PdfRotateParams = params
        if p.degrees not in {90, 180, 270}:
            return ["角度只支持 90、180、270"]
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: PdfRotateParams = params
        pdf_files = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"],
            key=lambda f: f.name.lower(),
        )
        if not pdf_files:
            return ToolResult(done=0, total=0, errors=["输入目录没有 PDF 文件"])

        errors: list[str] = []
        done = 0
        for pdf in pdf_files:
            if cancel_event.is_set():
                break
            try:
                reader = PdfReader(str(pdf))
                writer = PdfWriter()
                for page in reader.pages:
                    page.rotate(p.degrees)
                    writer.add_page(page)
                tmp_path = pdf.with_suffix(".tmp")
                with tmp_path.open("wb") as f:
                    writer.write(f)
                pdf.unlink()
                tmp_path.rename(pdf)
                done += 1
            except Exception as exc:
                errors.append(f"旋转失败 [{pdf.name}]: {exc}")
            on_progress(done, len(pdf_files), pdf.name)

        return ToolResult(done=done, total=len(pdf_files), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfRotateTool())
```

- [ ] **Step 5: Commit**

```bash
git add tools/pdf_merge.py tools/pdf_split.py tools/pdf_extract_text.py tools/pdf_rotate.py
git commit -m "feat: migrate PDF merge, split, extract_text, rotate tools"
```

---

### Task 13: 迁移独立运行工具（pdf_to_word, word_to_pdf, crawler_beginner, crawler_intermediate）

**Files:**
- Create: `tools/pdf_to_word.py`, `tools/word_to_pdf.py`, `tools/crawler_beginner.py`, `tools/crawler_intermediate.py`

- [ ] **Step 1: 写 `tools/pdf_to_word.py`**

```python
"""PDF → DOCX 转换 Tool（独立运行）。"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
import threading

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

PDF_EXTS = {".pdf"}


class PdfToWordTool(Tool):
    name = "PDF → Word"
    name_slug = "pdf_to_word"
    icon = "📄→📝"
    category = "pdf"
    input_mode = InputMode.NONE

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        from pdf2docx import Converter

        # 这个工具需要直接的文件对话框，但 run() 是后台线程调用的
        # 所以由平台在调用前收集好文件信息
        errors: list[str] = []
        done = 0

        for i, pdf_path in enumerate(sorted(work_dir.iterdir())):
            if pdf_path.suffix.lower() not in PDF_EXTS:
                continue
            if cancel_event.is_set():
                break
            try:
                out_file = work_dir / f"{pdf_path.stem}.docx"
                cv = Converter(str(pdf_path))
                try:
                    cv.convert(str(out_file))
                finally:
                    cv.close()
                done += 1
            except Exception as exc:
                errors.append(f"转换失败 [{pdf_path.name}]: {exc}")
            on_progress(done, len(list(work_dir.iterdir())), pdf_path.name)

        return ToolResult(done=done, total=len(list(work_dir.iterdir())), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfToWordTool())
```

嗯，pdf_to_word 和 word_to_pdf 需要单独处理——它们要弹出文件选择对话框，而不是基于目录。我改一下思路：这些工具的 `input_mode=NONE`，主程序直接用 tkinter 弹文件对话框，收集好文件后复制到 work_dir，再调 tool.run()。但这与 PipelineEngine 的使用方式冲突...

更简单的处理：让 `_run_standalone` 在主线程弹文件对话框，把选中的文件路径信息编码到 ToolParams 中传入。但这会让 ToolParams 包含文件路径字段，破坏"参数 vs 输入"的分离。

**最干净方案**：独立工具在 `_run_standalone` 里直接弹对话框，选完文件后复制到临时 work_dir，调 `tool.run()` 处理，输出也由 `_run_standalone` 管理。这样独立工具仍然只需要操作 work_dir。

让我重写这几个文件，保持简洁——work_dir 里已经有文件了（由 _run_standalone 负责放入），工具只管处理：

- [ ] **Step 1 (修订): 写 `tools/pdf_to_word.py`**

```python
"""PDF → DOCX 转换 Tool（独立运行，处理 work_dir 中的 PDF）。"""

from __future__ import annotations

from pathlib import Path
import threading

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


PDF_EXT = ".pdf"


class PdfToWordTool(Tool):
    name = "PDF → Word"
    name_slug = "pdf_to_word"
    icon = "📄📝"
    category = "pdf"
    input_mode = InputMode.NONE

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        from pdf2docx import Converter

        src_files = sorted([f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() == PDF_EXT],
                           key=lambda f: f.name.lower())
        if not src_files:
            return ToolResult(done=0, total=0, errors=["没有 PDF 文件"])

        errors: list[str] = []
        done = 0
        for pdf_path in src_files:
            if cancel_event.is_set():
                break
            try:
                out_file = work_dir / f"{pdf_path.stem}.docx"
                cv = Converter(str(pdf_path))
                try:
                    cv.convert(str(out_file))
                finally:
                    cv.close()
                done += 1
            except Exception as exc:
                errors.append(f"转换失败 [{pdf_path.name}]: {exc}")
            on_progress(done, len(src_files), pdf_path.name)

        return ToolResult(done=done, total=len(src_files), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfToWordTool())
```

- [ ] **Step 2: 写 `tools/word_to_pdf.py`**

```python
"""DOCX → PDF 转换 Tool（独立运行，处理 work_dir 中的 DOCX）。"""

from __future__ import annotations

from pathlib import Path
import threading

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


DOCX_EXT = ".docx"


class WordToPdfTool(Tool):
    name = "Word → PDF"
    name_slug = "word_to_pdf"
    icon = "📝📄"
    category = "pdf"
    input_mode = InputMode.NONE

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        from docx2pdf import convert

        src_files = sorted([f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() == DOCX_EXT],
                           key=lambda f: f.name.lower())
        if not src_files:
            return ToolResult(done=0, total=0, errors=["没有 DOCX 文件"])

        errors: list[str] = []
        done = 0
        for docx_path in src_files:
            if cancel_event.is_set():
                break
            try:
                out_file = work_dir / f"{docx_path.stem}.pdf"
                convert(str(docx_path), str(out_file))
                done += 1
            except Exception as exc:
                errors.append(f"转换失败 [{docx_path.name}]: {exc}")
            on_progress(done, len(src_files), docx_path.name)

        return ToolResult(done=done, total=len(src_files), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(WordToPdfTool())
```

- [ ] **Step 3: 写 `tools/crawler_beginner.py`**

```python
"""入门爬虫 Tool — 抓取 quotes.toscrape.com → CSV（独立运行）。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import threading

import requests
from bs4 import BeautifulSoup

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

BASE_URL = "https://quotes.toscrape.com"


@dataclass
class CrawlerBeginnerParams(ToolParams):
    max_pages: int = 3


class CrawlerBeginnerTool(Tool):
    name = "入门爬虫"
    name_slug = "crawler_beginner"
    icon = "🕷️"
    category = "web"
    input_mode = InputMode.NONE

    def params_type(self) -> type[ToolParams]:
        return CrawlerBeginnerParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: CrawlerBeginnerParams = params
        if p.max_pages < 1:
            return ["页数至少为 1"]
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: CrawlerBeginnerParams = params
        all_items: list[dict[str, str]] = []
        url = BASE_URL
        errors: list[str] = []

        for page_num in range(p.max_pages):
            if cancel_event.is_set():
                break
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for quote in soup.select("div.quote"):
                    text_el = quote.select_one("span.text")
                    author_el = quote.select_one("small.author")
                    tags = [t.get_text(strip=True) for t in quote.select("div.tags a.tag")]
                    all_items.append({
                        "quote": text_el.get_text(strip=True) if text_el else "",
                        "author": author_el.get_text(strip=True) if author_el else "",
                        "tags": ",".join(tags),
                    })

                next_btn = soup.select_one("li.next > a")
                if not next_btn:
                    break
                next_href = next_btn.get("href")
                if not next_href:
                    break
                url = f"{BASE_URL}{next_href}"
                on_progress(page_num + 1, p.max_pages, f"Page {page_num+1}")
            except Exception as exc:
                errors.append(f"抓取失败 (page {page_num+1}): {exc}")
                break

        # 输出 CSV 到 work_dir
        csv_path = work_dir / "quotes_beginner.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["quote", "author", "tags"])
            writer.writeheader()
            writer.writerows(all_items)

        return ToolResult(done=len(all_items), total=p.max_pages, errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(CrawlerBeginnerTool())
```

- [ ] **Step 4: 写 `tools/crawler_intermediate.py`**

```python
"""中级爬虫 Tool — 抓取 books.toscrape.com → CSV + SQLite（独立运行）。"""

from __future__ import annotations

import csv
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
import threading
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

BASE_URL = "https://books.toscrape.com/"


@dataclass
class CrawlerIntermediateParams(ToolParams):
    max_pages: int = 5
    workers: int = 6


class CrawlerIntermediateTool(Tool):
    name = "中级爬虫"
    name_slug = "crawler_intermediate"
    icon = "🕸️"
    category = "web"
    input_mode = InputMode.NONE

    def params_type(self) -> type[ToolParams]:
        return CrawlerIntermediateParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: CrawlerIntermediateParams = params
        errs: list[str] = []
        if p.max_pages < 1:
            errs.append("页数至少为 1")
        if p.workers < 1:
            errs.append("并发线程至少为 1")
        return errs

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: CrawlerIntermediateParams = params
        session = requests.Session()

        # 收集链接
        links: list[str] = []
        page_url = urljoin(BASE_URL, "catalogue/page-1.html")
        for pg in range(p.max_pages):
            if cancel_event.is_set():
                break
            try:
                html = self._fetch_with_retry(session, page_url)
                soup = BeautifulSoup(html, "html.parser")
                for article in soup.select("article.product_pod h3 a"):
                    href = article.get("href", "")
                    links.append(urljoin(page_url, href))
                next_btn = soup.select_one("li.next > a")
                if not next_btn:
                    break
                page_url = urljoin(page_url, next_btn.get("href", ""))
            except Exception as exc:
                return ToolResult(done=pg, total=p.max_pages, errors=[str(exc)])

        if not links:
            return ToolResult(done=0, total=0, errors=["未找到书籍链接"])

        links = sorted(set(links))
        rows: list[dict] = []

        with ThreadPoolExecutor(max_workers=p.workers) as pool:
            futures = [pool.submit(self._parse_detail, session, url) for url in links]
            for i, fut in enumerate(as_completed(futures)):
                if cancel_event.is_set():
                    break
                try:
                    rows.append(fut.result())
                except Exception:
                    pass
                on_progress(i + 1, len(links), f"详情 {i+1}/{len(links)}")

        # 保存到 SQLite
        db_path = work_dir / "books_intermediate.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                product_url TEXT PRIMARY KEY, title TEXT, price_gbp TEXT,
                rating TEXT, availability TEXT, upc TEXT, scraped_at TEXT
            )
        """)
        for row in rows:
            conn.execute(
                """INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(product_url) DO UPDATE SET
                   title=excluded.title, price_gbp=excluded.price_gbp,
                   rating=excluded.rating, availability=excluded.availability,
                   upc=excluded.upc, scraped_at=excluded.scraped_at""",
                (row["product_url"], row["title"], row["price_gbp"],
                 row["rating"], row["availability"], row["upc"], row["scraped_at"]),
            )
        conn.commit()
        conn.close()

        # 导出 CSV
        csv_path = work_dir / "books_intermediate.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "product_url", "title", "price_gbp", "rating", "availability", "upc", "scraped_at",
            ])
            writer.writeheader()
            writer.writerows(rows)

        return ToolResult(done=len(rows), total=len(links))

    @staticmethod
    def _fetch_with_retry(session: requests.Session, url: str, retries: int = 3) -> str:
        for i in range(retries):
            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
                return resp.text
            except Exception:
                if i < retries - 1:
                    time.sleep(1.2 * (i + 1))
        raise RuntimeError(f"请求失败: {url}")

    @staticmethod
    def _parse_detail(session: requests.Session, url: str) -> dict:
        html = CrawlerIntermediateTool._fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.select_one("div.product_main h1")
        price = soup.select_one("div.product_main p.price_color")
        rating_el = soup.select_one("div.product_main p.star-rating")
        availability = soup.select_one("div.product_main p.instock.availability")
        upc = ""
        for row in soup.select("table.table.table-striped tr"):
            key, val = row.select_one("th"), row.select_one("td")
            if key and val and key.get_text(strip=True) == "UPC":
                upc = val.get_text(strip=True)
                break
        return {
            "product_url": url,
            "title": title.get_text(strip=True) if title else "",
            "price_gbp": price.get_text(strip=True) if price else "",
            "rating": CrawlerIntermediateTool._parse_rating(rating_el.get("class", [])) if rating_el else "",
            "availability": availability.get_text(" ", strip=True) if availability else "",
            "upc": upc,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _parse_rating(classes: list[str]) -> str:
        for c in classes:
            if c != "star-rating":
                return c
        return ""


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(CrawlerIntermediateTool())
```

- [ ] **Step 5: Commit**

```bash
git add tools/pdf_to_word.py tools/word_to_pdf.py tools/crawler_beginner.py tools/crawler_intermediate.py
git commit -m "feat: migrate standalone tools (pdf_to_word, word_to_pdf, crawlers)"
```

---

### Task 14: `ui/app.py` 完善 — 独立工具的文件选择

**Files:**
- Modify: `ui/app.py`

Task 10 的初始 `_run_standalone` / `_run_standalone_async` 仅处理参数表单。独立工具（`InputMode.NONE`）还需要主线程弹出文件对话框。

- [ ] **Step 1: 替换 `_run_standalone` 方法**

将 `ui/app.py` 中现有的 `_run_standalone` 方法替换为：

```python
def _run_standalone(self, tool) -> None:
    from ui.widgets.param_form import ParamForm
    from tkinter import filedialog
    import shutil

    params_cls = tool.params_type()
    if dataclasses.fields(params_cls):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"参数 — {tool.name}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        form = ParamForm(dialog, params_cls)
        form.pack(padx=12, pady=12, fill="both", expand=True)

        result_params = None

        def _ok() -> None:
            nonlocal result_params
            p = form.get_params()
            errs = tool.validate_params(p)
            if errs:
                messagebox.showerror("参数错误", "\n".join(errs), parent=dialog)
                return
            result_params = p
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="确定", command=_ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)
        dialog.bind("<Return>", lambda e: _ok())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.wait_window()

        if result_params is None:
            return
    else:
        result_params = params_cls()

    # 文件选择（独立工具需要输入文件和输出目录）
    input_files: list[Path] | None = None
    output_dir: Path | None = None

    if tool.input_mode == InputMode.NONE:
        if tool.category == "pdf":
            filetypes = [("PDF files", "*.pdf")] if tool.name_slug == "pdf_to_word" else [("Word files", "*.docx")]
            files = filedialog.askopenfilenames(parent=self.root, title="选择输入文件", filetypes=filetypes)
            if not files:
                return
            input_files = [Path(f) for f in files]
        elif tool.category == "web":
            input_files = []  # 爬虫不需要输入文件
        # 选择输出目录
        out = filedialog.askdirectory(parent=self.root, title="选择输出目录")
        if not out:
            return
        output_dir = Path(out)

    self._enter_running()
    threading.Thread(
        target=self._run_standalone_async,
        args=(tool, result_params, input_files, output_dir),
        daemon=True,
    ).start()
```

- [ ] **Step 2: 替换 `_run_standalone_async` 方法**

将 `ui/app.py` 中现有的 `_run_standalone_async` 方法替换为：

```python
def _run_standalone_async(self, tool, params, input_files=None, output_dir=None) -> None:
    import shutil
    import tempfile
    from pathlib import Path

    try:
        with tempfile.TemporaryDirectory(prefix="autotools_") as tmp:
            work = Path(tmp) / "work"
            work.mkdir()

            # 复制输入文件到 work（独立工具）
            if input_files:
                for f in input_files:
                    shutil.copy2(f, work / f.name)
            elif tool.input_mode == InputMode.NONE:
                pass  # 无输入文件

            def _progress(i: int, t: int, name: str) -> None:
                pct = (i / max(t, 1)) * 100
                self.root.after(0, lambda: self._progress.update(pct, tool.name, f"{i}/{t}: {name}"))

            result = tool.run(work, params, _progress, self._cancel_event)

            # 复制输出到用户目录
            if output_dir:
                for f in work.iterdir():
                    if f.is_file():
                        shutil.copy2(f, output_dir / f.name)

        def _finish() -> None:
            self._enter_idle()
            if result.errors:
                msg = f"完成 {result.done}/{result.total}\n⚠ {len(result.errors)} 个错误\n" + "\n".join(result.errors[:5])
            else:
                msg = f"完成 {result.done}/{result.total}"
                if output_dir:
                    msg += f"\n输出目录: {output_dir}"
            messagebox.showinfo(tool.name, msg)

        self.root.after(0, _finish)
    except Exception as exc:
        self.root.after(0, lambda: self._finish_error(tool.name, str(exc)))
        self.root.after(0, self._enter_idle)

from core.tool_base import InputMode  # noqa: E402
```

- [ ] **Step 3: Commit**

```bash
git add ui/app.py
git commit -m "feat: add file selection and output handling for standalone tools"
```

---

### Task 15: `main.py` 入口 + 最终集成

**Files:**
- Create: `main.py`

- [ ] **Step 1: 写 `main.py`**

```python
"""Auto-tools 统一平台入口。"""

from __future__ import annotations

import tkinter as tk

# 导入所有工具模块完成注册
import tools.image_rename       # noqa: F401
import tools.image_watermark    # noqa: F401
import tools.image_compress     # noqa: F401
import tools.pdf_merge          # noqa: F401
import tools.pdf_split          # noqa: F401
import tools.pdf_extract_text   # noqa: F401
import tools.pdf_rotate         # noqa: F401
import tools.pdf_to_word        # noqa: F401
import tools.word_to_pdf        # noqa: F401
import tools.crawler_beginner   # noqa: F401
import tools.crawler_intermediate  # noqa: F401

from ui.app import MainWindow


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试运行**

```bash
python main.py
```

预期：主窗口正常显示，三个分类标签页各有对应工具，流水线可添加步骤，预设可保存加载。

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add unified main.py entry point with all tools registered"
```

---

### Task 16: 删除旧模块目录

**Files to remove:**
- `image_compress/` (整个目录)
- `image_renamer/` (整个目录)
- `image_watermark/` (整个目录)
- `image_workflow/` (整个目录)
- `pdf_tools/` (整个目录)
- `pdf_to_word/` (整个目录)
- `word_to_pdf/` (整个目录)
- `crawler_beginner/` (整个目录)
- `crawler_intermediate/` (整个目录)

- [ ] **Step 1: 删除旧目录**

```bash
rm -rf image_compress image_renamer image_watermark image_workflow \
       pdf_tools pdf_to_word word_to_pdf crawler_beginner crawler_intermediate
```

- [ ] **Step 2: 验证目录结构**

```bash
ls -la
```

预期：只剩下 `core/`, `ui/`, `tools/`, `presets/`, `main.py`, `requirements.txt`, `CLAUDE.md`, `README.md`, `spiral_matrix.py`, `docs/`。

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove old standalone module directories"
```

---

### Task 17: 自检修复

- [ ] **Step 1: 检查所有文件 import 一致性**

核对以下 import 路径在模块间正确：
- `core.tool_base` → `Tool`, `ToolParams`, `ToolResult`, `InputMode`, `ProgressCallback`
- `core.registry` → `ToolRegistry`
- `core.pipeline` → `PipelineStep`, `PipelineRun`, `PipelineResult`, `execute_pipeline`
- `core.preset` → `save_preset`, `load_preset`, `list_presets`, `delete_preset`
- `ui.widgets.param_form` → `ParamForm`
- `ui.widgets.progress_panel` → `ProgressPanel`

- [ ] **Step 2: 运行 `python main.py` 确认无 import 错误**

- [ ] **Step 3: 检查 `ui/app.py` 中 `_run_standalone_async` 的 `shutil` import**

确保 `shutil` 在文件顶部已 import（`import shutil`），目前 `_run_standalone_async` 内部也有 `import shutil`，去掉内部的重复 import：

将 `_run_standalone_async` 方法中的 `import shutil` 移除，改为在文件顶部添加 `import shutil`。

- [ ] **Step 4: 检查 `ui/app.py` 中 `InputMode` import**

确保 `from core.tool_base import InputMode` 已存在（在 Task 15 的 `_run_standalone` 中使用）。

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "fix: clean up imports and fix inconsistencies"
```
```

（注：实际在 ui/app.py 文件顶部已有 `from core.tool_base import InputMode` 和 `import shutil`）

---

### Task 18: 更新根 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md 内容**

将现有内容替换为：

```markdown
# Auto-tools

统一的 Python GUI 自动化工具平台，面向 Windows。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 功能

### 📷 图片工具（支持流水线串联）

| 工具 | 功能 |
|---|---|
| 批量重命名 | 按前缀/编号/后缀批量重命名 |
| 文字水印 | 批量添加文字水印（位置、透明度可调） |
| 批量压缩 | 批量压缩/缩放（JPEG 质量、最大宽高） |

### 📄 PDF 工具

| 工具 | 功能 |
|---|---|
| PDF 合并 | 合并多个 PDF |
| PDF 拆分 | 按页拆分 PDF |
| 提取 PDF 文本 | 提取 PDF 文本到 TXT |
| PDF 旋转 | 旋转 PDF 页面（90/180/270 度） |
| PDF → Word | 批量 PDF 转 DOCX |
| Word → PDF | 批量 DOCX 转 PDF（需本机安装 Word） |

### 🌐 网页工具

| 工具 | 功能 |
|---|---|
| 入门爬虫 | 抓取 quotes.toscrape.com → CSV |
| 中级爬虫 | 抓取 books.toscrape.com → SQLite + CSV |

## 流水线

图片工具可自由组合为流水线（重命名 → 水印 → 压缩），保存为预设一键复用。

## 特点

- 🛡️ 原图零修改（临时目录隔离）
- 🚫 中途取消
- 🔤 自动检测中文字体
- 📋 参数表单自动生成
- 💾 流水线预设保存/加载
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for unified platform"
```

---

### Task 19: 最终验证

- [ ] **Step 1: 从干净环境安装依赖**

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: 运行主程序**

```bash
python main.py
```

检查清单：
- [ ] 主窗口显示三个分类标签页（图片 / PDF / 网页）
- [ ] 图片工具可"加入流水线"
- [ ] 流水线可添加/删除步骤
- [ ] 步骤参数可编辑
- [ ] 预设可保存和加载
- [ ] 执行流水线功能正常
- [ ] 独立工具（PDF→Word、Word→PDF、爬虫）正常弹出文件对话框并执行
- [ ] 取消按钮正常工作

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "chore: final integration fixes after testing"
```
```

