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
