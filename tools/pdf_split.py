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
                pdf.unlink()
                total_processed += 1
            except Exception as exc:
                errors.append(f"拆分失败 [{pdf.name}]: {exc}")
            on_progress(total_processed, len(pdf_files), pdf.name)

        return ToolResult(done=total_processed, total=len(pdf_files), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(PdfSplitTool())
