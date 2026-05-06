from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def get_image_files(folder: Path) -> list[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def build_new_name(prefix: str, number: int, width: int, suffix: str, ext: str) -> str:
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    parts.append(str(number).zfill(width))
    if suffix:
        parts.append(suffix)
    return "_".join(parts) + ext


def batch_rename_images(folder: Path, prefix: str, suffix: str, start_str: str) -> tuple[int, int]:
    images = get_image_files(folder)
    if not images:
        return 0, 0

    width = len(start_str)
    start_num = int(start_str)

    plans: list[tuple[Path, Path]] = []
    for i, old_path in enumerate(images):
        new_name = build_new_name(prefix, start_num + i, width, suffix, old_path.suffix.lower())
        new_path = old_path.with_name(new_name)
        plans.append((old_path, new_path))

    target_names = [new_path.name for _, new_path in plans]
    if len(target_names) != len(set(target_names)):
        raise ValueError("新文件名发生重复，请调整前后缀或起始编号。")

    for old_path, new_path in plans:
        if old_path.name == new_path.name:
            continue
        if new_path.exists():
            raise FileExistsError(f"目标文件已存在：{new_path.name}")

    temp_paths: list[tuple[Path, Path]] = []
    for idx, (old_path, _) in enumerate(plans):
        temp_path = old_path.with_name(f"__tmp_rename_{idx}__{old_path.name}")
        old_path.rename(temp_path)
        temp_paths.append((temp_path, old_path))

    renamed = 0
    for idx, (temp_path, _) in enumerate(temp_paths):
        _, final_path = plans[idx]
        temp_path.rename(final_path)
        renamed += 1

    return renamed, len(images)


def ask_inputs(root: tk.Tk) -> tuple[Path, str, str, str] | None:
    folder_str = filedialog.askdirectory(title="请选择图片文件夹")
    if not folder_str:
        return None
    folder = Path(folder_str)

    prefix = simpledialog.askstring("输入前缀", "请输入文件名前缀（可留空）", parent=root)
    if prefix is None:
        return None

    suffix = simpledialog.askstring("输入后缀", "请输入文件名后缀（可留空）", parent=root)
    if suffix is None:
        return None

    start_str = simpledialog.askstring(
        "起始编号",
        "请输入起始编号（如 00 / 000 / 0000）",
        parent=root,
    )
    if start_str is None:
        return None
    if not start_str.isdigit():
        messagebox.showerror("输入错误", "起始编号必须是纯数字，例如 00 或 000。", parent=root)
        return None

    return folder, prefix.strip(), suffix.strip(), start_str


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    inputs = ask_inputs(root)
    if inputs is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    folder, prefix, suffix, start_str = inputs

    try:
        renamed, total = batch_rename_images(folder, prefix, suffix, start_str)
    except (ValueError, FileExistsError) as exc:
        messagebox.showerror("重命名失败", str(exc), parent=root)
        return
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("异常", f"发生未预期错误：{exc}", parent=root)
        return

    if total == 0:
        messagebox.showinfo("完成", "该文件夹中未找到支持的图片文件。", parent=root)
    else:
        messagebox.showinfo("完成", f"已重命名 {renamed}/{total} 张图片。", parent=root)


if __name__ == "__main__":
    main()
