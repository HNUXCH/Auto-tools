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
