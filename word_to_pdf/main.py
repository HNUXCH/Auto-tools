from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from docx2pdf import convert


def convert_one(docx_path: Path, output_dir: Path) -> Path:
    output_file = output_dir / f"{docx_path.stem}.pdf"
    convert(str(docx_path), str(output_file))
    return output_file


def convert_batch(docx_files: list[Path], output_dir: Path) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    total = len(docx_files)
    for docx in docx_files:
        try:
            convert_one(docx, output_dir)
            ok += 1
        except Exception:
            continue
    return ok, total


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    selected = filedialog.askopenfilenames(
        parent=root,
        title="选择要转换的 Word 文件（可多选）",
        filetypes=[("Word files", "*.docx")],
    )
    if not selected:
        messagebox.showinfo("已取消", "未选择 Word 文件。", parent=root)
        return

    output_dir_str = filedialog.askdirectory(parent=root, title="选择 PDF 输出文件夹")
    if not output_dir_str:
        messagebox.showinfo("已取消", "未选择输出文件夹。", parent=root)
        return

    files = [Path(p) for p in selected]
    output_dir = Path(output_dir_str)

    try:
        ok, total = convert_batch(files, output_dir)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("转换失败", f"发生错误：{exc}", parent=root)
        return

    if ok == total:
        messagebox.showinfo("完成", f"转换成功：{ok}/{total}\n输出目录：{output_dir}", parent=root)
    else:
        messagebox.showwarning(
            "部分完成",
            f"转换成功：{ok}/{total}\n部分文件转换失败。\n输出目录：{output_dir}",
            parent=root,
        )


if __name__ == "__main__":
    main()
