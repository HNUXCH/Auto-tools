from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from pdf2docx import Converter


def convert_one(pdf_path: Path, output_dir: Path) -> Path:
    output_file = output_dir / f"{pdf_path.stem}.docx"
    cv = Converter(str(pdf_path))
    try:
        cv.convert(str(output_file))
    finally:
        cv.close()
    return output_file


def convert_batch(pdf_files: list[Path], output_dir: Path) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    total = len(pdf_files)
    for pdf in pdf_files:
        try:
            convert_one(pdf, output_dir)
            ok += 1
        except Exception:
            # Continue converting remaining files even if one fails.
            continue
    return ok, total


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    selected = filedialog.askopenfilenames(
        parent=root,
        title="选择要转换的 PDF（可多选）",
        filetypes=[("PDF files", "*.pdf")],
    )
    if not selected:
        messagebox.showinfo("已取消", "未选择 PDF 文件。", parent=root)
        return

    output_dir_str = filedialog.askdirectory(parent=root, title="选择 Word 输出文件夹")
    if not output_dir_str:
        messagebox.showinfo("已取消", "未选择输出文件夹。", parent=root)
        return

    pdf_files = [Path(p) for p in selected]
    output_dir = Path(output_dir_str)

    try:
        ok, total = convert_batch(pdf_files, output_dir)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("转换失败", f"发生错误：{exc}", parent=root)
        return

    if ok == total:
        messagebox.showinfo("完成", f"转换成功：{ok}/{total}\n输出目录：{output_dir}", parent=root)
    else:
        messagebox.showwarning(
            "部分完成",
            f"转换成功：{ok}/{total}\n部分文件转换失败（可能是扫描件或损坏文件）。\n输出目录：{output_dir}",
            parent=root,
        )


if __name__ == "__main__":
    main()
