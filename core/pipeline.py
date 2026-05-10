"""流水线引擎 — 串联多个 Tool 步骤，管理临时目录、进度、取消。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import tempfile
import threading

from .tool_base import ProgressCallback, Tool, ToolParams, ToolResult


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


def _copy_files_to_work(src: Path, dst: Path) -> int:
    """复制 src 目录下所有文件到 dst。"""
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in sorted(src.iterdir()):
        if p.is_file():
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
    steps: list[PipelineStep],
    input_dir: str,
    output_dir: str,
    cancel_event: threading.Event | None = None,
    on_status: ProgressCallback | None = None,
) -> PipelineResult | None:
    """执行流水线。纯数据处理，不涉及 UI。

    由调用方在主线程完成目录选择后调用（可从后台线程调用）。
    返回 PipelineResult，用户取消返回 None。
    """
    if not steps:
        return None

    # 验证参数
    for step in steps:
        errs = step.tool.validate_params(step.params)
        if errs:
            return None

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    cancel = cancel_event if cancel_event is not None else threading.Event()
    all_results: list[tuple[str, ToolResult]] = []
    logs: list[str] = []

    try:
        with tempfile.TemporaryDirectory(prefix="autotools_") as tmp:
            work = Path(tmp) / "work"
            file_count = _copy_files_to_work(input_path, work)
            if file_count == 0:
                logs.append("输入目录没有文件")
                return PipelineResult(success=False, step_results=[], logs=logs)
            logs.append(f"已加载 {file_count} 个文件")

            total_steps = len(steps)
            for idx, step in enumerate(steps):
                if cancel.is_set():
                    logs.append(f"用户取消于步骤: {step.tool.name}")
                    break

                # 用默认参数捕获当前 idx/step 的值
                def _progress(i: int, t: int, name: str, _idx: int = idx, _step: object = step) -> None:
                    pct = ((_idx + i / max(t, 1)) / total_steps) * 100
                    detail = f"{_step.tool.name} {i}/{t}: {name}"
                    if on_status:
                        on_status(min(int(pct), 100), t, detail)

                result = step.tool.run(work, step.params, _progress, cancel)
                all_results.append((step.tool.name, result))
                logs.append(f"{step.tool.name}: 完成 {result.done}/{result.total}")
                if result.errors:
                    logs.append(f"  {len(result.errors)} 个错误:")
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
