"""批量文字水印 Tool。支持单点水印和满铺斜向重复水印。"""

from __future__ import annotations

from dataclasses import dataclass
import math
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
    # 单点模式
    position: str = "bottom-right"   # top-left | top-right | bottom-left | bottom-right | center
    # 满铺模式
    mode: str = "single"             # "single" | "tiled"
    angle: int = 30                  # 满铺模式下文字倾斜角度 (0-90)
    spacing: int = 3                 # 满铺模式下间距倍数 (2-8，越大越稀疏)
    # 通用
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
        if p.mode not in ("single", "tiled"):
            errs.append("模式只支持 single 或 tiled")
        if not 0 <= p.angle <= 90:
            errs.append("角度必须在 0-90 之间")
        if p.spacing < 2 or p.spacing > 8:
            errs.append("间距倍数必须在 2-8 之间")
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

                    if p.mode == "tiled":
                        self._draw_tiled(overlay, p.text, font, (255, 255, 255, p.opacity), p.angle, p.spacing)
                    else:
                        self._draw_single(overlay, p.text, font, p.position, (255, 255, 255, p.opacity))

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

    # ── 单点水印 ──

    def _draw_single(self, overlay: Image.Image, text: str, font: ImageFont.FreeTypeFont, position: str, color: tuple) -> None:
        draw = ImageDraw.Draw(overlay)
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = self._calc_pos(overlay.width, overlay.height, w, h, position)
        draw.text((x, y), text, font=font, fill=color)

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

    # ── 满铺斜向水印 ──

    def _draw_tiled(self, overlay: Image.Image, text: str, font: ImageFont.FreeTypeFont, color: tuple, angle: int, spacing: int) -> None:
        """在 overlay 上绘制满铺的斜向重复文字水印。

        策略：创建一个大方 canvas，铺满文字 → 旋转整个 canvas → 裁剪中心区域 → 贴到 overlay。
        """
        w, h = overlay.size

        # 测量文字尺寸
        tmp = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw_tmp = ImageDraw.Draw(tmp)
        bbox = draw_tmp.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        step_x = max(tw * spacing, tw + 40)
        step_y = max(th * spacing, th + 40)

        # canvas 对角线长度，确保旋转后还能覆盖原图
        canvas_size = int(math.sqrt(w * w + h * h)) + max(tw, th) * 2 + 200
        canvas_size += canvas_size % 2  # 偶数方便裁剪

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        canvas_draw = ImageDraw.Draw(canvas)

        # 铺满文字
        for row_y in range(0, canvas_size + step_y, step_y):
            for col_x in range(0, canvas_size + step_x, step_x):
                canvas_draw.text((col_x, row_y), text, font=font, fill=color)

        # 旋转整个 canvas（正向角度=顺时针，这里用负角产生经典 / 向倾斜）
        rotated = canvas.rotate(-angle, expand=False, resample=Image.Resampling.BICUBIC)

        # 从旋转后的 canvas 中心裁剪出 w×h 区域
        rw, rh = rotated.size
        left = (rw - w) // 2
        top = (rh - h) // 2
        cropped = rotated.crop((left, top, left + w, top + h))

        overlay.paste(cropped, (0, 0), cropped)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(ImageWatermarkTool())
