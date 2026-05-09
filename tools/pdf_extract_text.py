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
