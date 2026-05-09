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
