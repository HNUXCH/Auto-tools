from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def list_images(folder: Path) -> list[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def save_compressed(img: Image.Image, out_path: Path, quality: int, max_width: int, max_height: int) -> None:
    image = img.copy()
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    ext = out_path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        image.convert("RGB").save(out_path, quality=quality, optimize=True)
    elif ext == ".png":
        image.save(out_path, optimize=True)
    else:
        image.save(out_path)


def compress_batch(input_dir: Path, output_dir: Path, quality: int, max_width: int, max_height: int) -> tuple[int, int]:
    images = list_images(input_dir)
    if not images:
        return 0, 0

    output_dir.mkdir(parents=True, exist_ok=True)
    done = 0
    for img_path in images:
        with Image.open(img_path) as img:
            out_path = output_dir / img_path.name
            save_compressed(img, out_path, quality, max_width, max_height)
            done += 1
    return done, len(images)


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    input_dir_str = filedialog.askdirectory(parent=root, title="选择输入图片文件夹")
    if not input_dir_str:
        messagebox.showinfo("已取消", "未选择输入目录。", parent=root)
        return

    output_dir_str = filedialog.askdirectory(parent=root, title="选择压缩输出文件夹")
    if not output_dir_str:
        messagebox.showinfo("已取消", "未选择输出目录。", parent=root)
        return

    quality = simpledialog.askinteger("压缩质量", "JPEG质量（1-95，推荐 70-85）", parent=root, initialvalue=80, minvalue=1, maxvalue=95)
    if quality is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    max_width = simpledialog.askinteger("最大宽度", "输入最大宽度（像素）", parent=root, initialvalue=1920, minvalue=1)
    if max_width is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    max_height = simpledialog.askinteger("最大高度", "输入最大高度（像素）", parent=root, initialvalue=1920, minvalue=1)
    if max_height is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    try:
        done, total = compress_batch(Path(input_dir_str), Path(output_dir_str), quality, max_width, max_height)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("压缩失败", f"发生错误：{exc}", parent=root)
        return

    if total == 0:
        messagebox.showinfo("完成", "输入目录未找到支持的图片。", parent=root)
    else:
        messagebox.showinfo("完成", f"已压缩 {done}/{total} 张图片。", parent=root)


if __name__ == "__main__":
    main()
