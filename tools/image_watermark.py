"""批量文字水印 Tool。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

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
