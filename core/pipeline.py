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
