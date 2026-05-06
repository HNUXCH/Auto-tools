from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def list_images(folder: Path) -> list[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def calc_position(
    base_w: int,
    base_h: int,
    mark_w: int,
    mark_h: int,
    position: str,
    margin: int = 20,
) -> tuple[int, int]:
    if position == "top-left":
        return margin, margin
    if position == "top-right":
        return max(margin, base_w - mark_w - margin), margin
    if position == "bottom-left":
        return margin, max(margin, base_h - mark_h - margin)
    if position == "center":
        return max(0, (base_w - mark_w) // 2), max(0, (base_h - mark_h) // 2)
    return max(margin, base_w - mark_w - margin), max(margin, base_h - mark_h - margin)


def add_text_watermark(
    image: Image.Image,
    text: str,
    position: str,
    font_size: int,
    opacity: int,
) -> Image.Image:
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        # Windows common font
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x, y = calc_position(base.width, base.height, text_w, text_h, position)

    draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
    merged = Image.alpha_composite(base, overlay)
    return merged


def process_batch(
    input_dir: Path,
    output_dir: Path,
    text: str,
    position: str,
    font_size: int,
    opacity: int,
) -> tuple[int, int]:
    images = list_images(input_dir)
    if not images:
        return 0, 0

    output_dir.mkdir(parents=True, exist_ok=True)
    success = 0
    for img_path in images:
        with Image.open(img_path) as img:
            marked = add_text_watermark(img, text, position, font_size, opacity)
            if img_path.suffix.lower() in {".jpg", ".jpeg"}:
                marked.convert("RGB").save(output_dir / img_path.name, quality=95)
            else:
                marked.save(output_dir / img_path.name)
            success += 1
    return success, len(images)


def ask_params(root: tk.Tk) -> tuple[Path, Path, str, str, int, int] | None:
    input_dir_str = filedialog.askdirectory(parent=root, title="选择输入图片文件夹")
    if not input_dir_str:
        return None
    output_dir_str = filedialog.askdirectory(parent=root, title="选择输出文件夹（建议新建）")
    if not output_dir_str:
        return None

    text = simpledialog.askstring("水印文字", "请输入水印文字", parent=root)
    if text is None or not text.strip():
        messagebox.showerror("输入错误", "水印文字不能为空。", parent=root)
        return None

    pos = simpledialog.askstring(
        "水印位置",
        "输入位置：top-left / top-right / bottom-left / bottom-right / center",
        parent=root,
    )
    if pos is None:
        return None
    position = pos.strip().lower()
    allowed = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}
    if position not in allowed:
        messagebox.showerror("输入错误", "位置不正确。", parent=root)
        return None

    font_size = simpledialog.askinteger("字体大小", "请输入字体大小（默认 36）", initialvalue=36, parent=root)
    if font_size is None:
        return None
    if font_size < 8:
        messagebox.showerror("输入错误", "字体大小不能小于 8。", parent=root)
        return None

    opacity = simpledialog.askinteger("透明度", "请输入透明度（0-255，推荐 80-180）", initialvalue=120, parent=root)
    if opacity is None:
        return None
    if not 0 <= opacity <= 255:
        messagebox.showerror("输入错误", "透明度必须在 0 到 255 之间。", parent=root)
        return None

    return Path(input_dir_str), Path(output_dir_str), text.strip(), position, font_size, opacity


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    params = ask_params(root)
    if params is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    input_dir, output_dir, text, position, font_size, opacity = params

    try:
        done, total = process_batch(input_dir, output_dir, text, position, font_size, opacity)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("处理失败", f"发生错误：{exc}", parent=root)
        return

    if total == 0:
        messagebox.showinfo("完成", "输入目录未找到支持的图片文件。", parent=root)
    else:
        messagebox.showinfo("完成", f"已处理 {done}/{total} 张图片。", parent=root)


if __name__ == "__main__":
    main()
