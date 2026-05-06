from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from pypdf import PdfReader, PdfWriter


def merge_pdfs(inputs: list[Path], output: Path) -> None:
    writer = PdfWriter()
    for pdf in inputs:
        reader = PdfReader(str(pdf))
        for page in reader.pages:
            writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as f:
        writer.write(f)


def split_pdf(input_file: Path, output_dir: Path) -> int:
    reader = PdfReader(str(input_file))
    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        out_file = output_dir / f"{input_file.stem}_p{idx:03d}.pdf"
        with out_file.open("wb") as f:
            writer.write(f)
    return len(reader.pages)


def extract_text(input_file: Path, output_txt: Path) -> int:
    reader = PdfReader(str(input_file))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        parts.append(f"===== Page {i} =====\n{text}\n")
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text("\n".join(parts), encoding="utf-8")
    return len(reader.pages)


def rotate_pdf(input_file: Path, output_file: Path, degrees: int) -> int:
    if degrees not in {90, 180, 270}:
        raise ValueError("degrees 只支持 90/180/270")
    reader = PdfReader(str(input_file))
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(degrees)
        writer.add_page(page)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("wb") as f:
        writer.write(f)
    return len(reader.pages)


def choose_output_pdf(parent: tk.Tk, title: str, default_name: str) -> Path | None:
    out = filedialog.asksaveasfilename(
        parent=parent,
        title=title,
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF files", "*.pdf")],
    )
    return Path(out) if out else None


def choose_input_pdf(parent: tk.Tk, title: str) -> Path | None:
    file_path = filedialog.askopenfilename(
        parent=parent,
        title=title,
        filetypes=[("PDF files", "*.pdf")],
    )
    return Path(file_path) if file_path else None


def on_merge(root: tk.Tk) -> None:
    input_paths = filedialog.askopenfilenames(
        parent=root,
        title="选择要合并的 PDF（可多选）",
        filetypes=[("PDF files", "*.pdf")],
    )
    if not input_paths:
        return
    output = choose_output_pdf(root, "保存合并后的 PDF", "merged.pdf")
    if output is None:
        return

    try:
        merge_pdfs([Path(p) for p in input_paths], output)
        messagebox.showinfo("完成", f"已合并 {len(input_paths)} 个 PDF。", parent=root)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("错误", f"合并失败：{exc}", parent=root)


def on_split(root: tk.Tk) -> None:
    input_file = choose_input_pdf(root, "选择要拆分的 PDF")
    if input_file is None:
        return
    output_dir = filedialog.askdirectory(parent=root, title="选择输出目录")
    if not output_dir:
        return

    try:
        count = split_pdf(input_file, Path(output_dir))
        messagebox.showinfo("完成", f"已拆分 {count} 页。", parent=root)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("错误", f"拆分失败：{exc}", parent=root)


def on_extract_text(root: tk.Tk) -> None:
    input_file = choose_input_pdf(root, "选择要提取文本的 PDF")
    if input_file is None:
        return
    out_txt = filedialog.asksaveasfilename(
        parent=root,
        title="保存提取的文本",
        defaultextension=".txt",
        initialfile=f"{input_file.stem}.txt",
        filetypes=[("Text files", "*.txt")],
    )
    if not out_txt:
        return

    try:
        count = extract_text(input_file, Path(out_txt))
        messagebox.showinfo("完成", f"已提取 {count} 页文本。", parent=root)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("错误", f"提取失败：{exc}", parent=root)


def on_rotate(root: tk.Tk) -> None:
    input_file = choose_input_pdf(root, "选择要旋转的 PDF")
    if input_file is None:
        return
    degree_str = simpledialog.askstring("旋转角度", "输入角度：90 / 180 / 270", parent=root)
    if degree_str is None:
        return
    if degree_str not in {"90", "180", "270"}:
        messagebox.showerror("输入错误", "角度必须是 90、180 或 270。", parent=root)
        return
    output = choose_output_pdf(root, "保存旋转后的 PDF", f"{input_file.stem}_rotated.pdf")
    if output is None:
        return

    try:
        count = rotate_pdf(input_file, output, int(degree_str))
        messagebox.showinfo("完成", f"已旋转 {count} 页。", parent=root)
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("错误", f"旋转失败：{exc}", parent=root)


def main() -> None:
    root = tk.Tk()
    root.title("PDF 工具箱（Windows）")
    root.geometry("380x260")
    root.resizable(False, False)

    tk.Label(root, text="请选择要执行的 PDF 功能", font=("Segoe UI", 12, "bold")).pack(pady=(18, 16))

    tk.Button(root, text="合并 PDF", width=24, command=lambda: on_merge(root)).pack(pady=6)
    tk.Button(root, text="按页拆分 PDF", width=24, command=lambda: on_split(root)).pack(pady=6)
    tk.Button(root, text="提取 PDF 文本", width=24, command=lambda: on_extract_text(root)).pack(pady=6)
    tk.Button(root, text="旋转 PDF 页面", width=24, command=lambda: on_rotate(root)).pack(pady=6)
    tk.Button(root, text="退出", width=24, command=root.destroy).pack(pady=(14, 6))

    root.mainloop()


if __name__ == "__main__":
    main()
