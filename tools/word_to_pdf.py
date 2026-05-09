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
