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

        for pdf in pdf_files:
            pdf.unlink()
        output_pdf = work_dir / "merged.pdf"
        with output_pdf.open("wb") as f:
            writer.write(f)

        return ToolResult(done=len(pdf_files), total=len(pdf_files))


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfMergeTool())
