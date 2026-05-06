from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, simpledialog
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def list_images(folder: Path) -> list[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def copy_all_images(src: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    images = list_images(src)
    for p in images:
        shutil.copy2(p, dst / p.name)
    return len(images)


def run_rename(
    folder: Path,
    prefix: str,
    suffix: str,
    start_str: str,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> int:
    images = list_images(folder)
    width = len(start_str)
    start_num = int(start_str)

    plans: list[tuple[Path, Path]] = []
    for i, old_path in enumerate(images):
        parts: list[str] = []
        if prefix:
            parts.append(prefix)
        parts.append(str(start_num + i).zfill(width))
        if suffix:
            parts.append(suffix)
        new_name = "_".join(parts) + old_path.suffix.lower()
        plans.append((old_path, old_path.with_name(new_name)))

    target_names = [new.name for _, new in plans]
    if len(target_names) != len(set(target_names)):
        raise ValueError("重命名阶段目标文件名冲突。")

    for old_path, new_path in plans:
        if old_path.name != new_path.name and new_path.exists():
            raise FileExistsError(f"重命名冲突：{new_path.name}")

    temp_paths: list[tuple[Path, Path]] = []
    for idx, (old_path, _) in enumerate(plans):
        tmp = old_path.with_name(f"__wf_tmp_{idx}__{old_path.name}")
        old_path.rename(tmp)
        temp_paths.append((tmp, old_path))

    renamed = 0
    for idx, (tmp, _) in enumerate(temp_paths):
        _, final_path = plans[idx]
        tmp.rename(final_path)
        renamed += 1
        if progress_cb:
            progress_cb(renamed, len(temp_paths), final_path.name)
    return renamed


def calc_position(base_w: int, base_h: int, mark_w: int, mark_h: int, pos: str, margin: int = 20) -> tuple[int, int]:
    if pos == "top-left":
        return margin, margin
    if pos == "top-right":
        return max(margin, base_w - mark_w - margin), margin
    if pos == "bottom-left":
        return margin, max(margin, base_h - mark_h - margin)
    if pos == "center":
        return max(0, (base_w - mark_w) // 2), max(0, (base_h - mark_h) // 2)
    return max(margin, base_w - mark_w - margin), max(margin, base_h - mark_h - margin)


def run_watermark(
    folder: Path,
    text: str,
    position: str,
    font_size: int,
    opacity: int,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> int:
    images = list_images(folder)
    done = 0
    for p in images:
        with Image.open(p) as img:
            base = img.convert("RGBA")
            overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x, y = calc_position(base.width, base.height, w, h, position)
            draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
            merged = Image.alpha_composite(base, overlay)
            if p.suffix.lower() in {".jpg", ".jpeg"}:
                merged.convert("RGB").save(p, quality=95)
            else:
                merged.save(p)
            done += 1
            if progress_cb:
                progress_cb(done, len(images), p.name)
    return done


def run_compress(
    src_folder: Path,
    dst_folder: Path,
    quality: int,
    max_width: int,
    max_height: int,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> int:
    images = list_images(src_folder)
    dst_folder.mkdir(parents=True, exist_ok=True)
    done = 0
    for p in images:
        with Image.open(p) as img:
            out = img.copy()
            out.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            target = dst_folder / p.name
            if p.suffix.lower() in {".jpg", ".jpeg"}:
                out.convert("RGB").save(target, quality=quality, optimize=True)
            elif p.suffix.lower() == ".png":
                out.save(target, optimize=True)
            else:
                out.save(target)
            done += 1
            if progress_cb:
                progress_cb(done, len(images), p.name)
    return done


class WorkflowApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("图片工作流（重命名 -> 水印 -> 压缩）")
        self.root.geometry("960x640")
        self.root.resizable(False, False)

        self.do_rename = tk.BooleanVar(value=True)
        self.do_watermark = tk.BooleanVar(value=True)
        self.do_compress = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="就绪")
        self.detail_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0.0)

        tk.Label(root, text="选择要执行的步骤", font=("Segoe UI", 12, "bold")).pack(pady=(16, 8))
        tk.Checkbutton(root, text="1) 批量重命名", variable=self.do_rename).pack(anchor="w", padx=40)
        tk.Checkbutton(root, text="2) 批量文字水印", variable=self.do_watermark).pack(anchor="w", padx=40)
        tk.Checkbutton(root, text="3) 批量压缩输出", variable=self.do_compress).pack(anchor="w", padx=40)

        tk.Label(root, text="说明：工作流不会改动原图，结果输出到你选择的输出目录。").pack(pady=(14, 8))
        self.run_btn = tk.Button(root, text="开始执行工作流", width=26, command=self.run)
        self.run_btn.pack(pady=8)
        tk.Button(root, text="退出", width=26, command=root.destroy).pack()
        ttk.Progressbar(root, variable=self.progress_var, maximum=100, length=360).pack(pady=(10, 2))
        tk.Label(root, textvariable=self.status_var).pack(pady=(8, 0))
        tk.Label(root, textvariable=self.detail_var).pack()

    def run(self) -> None:
        if not (self.do_rename.get() or self.do_watermark.get() or self.do_compress.get()):
            messagebox.showerror("提示", "请至少勾选一个步骤。", parent=self.root)
            return

        input_dir = filedialog.askdirectory(parent=self.root, title="选择输入图片目录")
        if not input_dir:
            return
        output_dir = filedialog.askdirectory(parent=self.root, title="选择最终输出目录")
        if not output_dir:
            return

        rename_params: tuple[str, str, str] | None = None
        wm_params: tuple[str, str, int, int] | None = None
        compress_params: tuple[int, int, int] | None = None

        if self.do_rename.get():
            prefix = simpledialog.askstring("重命名", "前缀（可空）", parent=self.root)
            if prefix is None:
                return
            suffix = simpledialog.askstring("重命名", "后缀（可空）", parent=self.root)
            if suffix is None:
                return
            start = simpledialog.askstring("重命名", "起始编号（如 001）", parent=self.root)
            if start is None or not start.isdigit():
                messagebox.showerror("输入错误", "起始编号必须为数字。", parent=self.root)
                return
            rename_params = (prefix.strip(), suffix.strip(), start)

        if self.do_watermark.get():
            text = simpledialog.askstring("水印", "输入水印文字", parent=self.root)
            if text is None or not text.strip():
                messagebox.showerror("输入错误", "水印文字不能为空。", parent=self.root)
                return
            position = simpledialog.askstring(
                "水印位置",
                "top-left / top-right / bottom-left / bottom-right / center",
                parent=self.root,
            )
            if position is None:
                return
            pos_norm = position.strip().lower()
            if pos_norm not in {"top-left", "top-right", "bottom-left", "bottom-right", "center"}:
                messagebox.showerror("输入错误", "水印位置不正确。", parent=self.root)
                return
            size = simpledialog.askinteger("水印", "字体大小", parent=self.root, initialvalue=36, minvalue=8)
            if size is None:
                return
            opacity = simpledialog.askinteger("水印", "透明度（0-255）", parent=self.root, initialvalue=120, minvalue=0, maxvalue=255)
            if opacity is None:
                return
            wm_params = (text.strip(), pos_norm, size, opacity)

        if self.do_compress.get():
            quality = simpledialog.askinteger("压缩", "JPEG质量（1-95）", parent=self.root, initialvalue=80, minvalue=1, maxvalue=95)
            if quality is None:
                return
            max_w = simpledialog.askinteger("压缩", "最大宽度", parent=self.root, initialvalue=1920, minvalue=1)
            if max_w is None:
                return
            max_h = simpledialog.askinteger("压缩", "最大高度", parent=self.root, initialvalue=1920, minvalue=1)
            if max_h is None:
                return
            compress_params = (quality, max_w, max_h)

        self.run_btn.config(state="disabled")
        self.status_var.set("正在执行，请稍候...")
        self.detail_var.set("")
        self.progress_var.set(0.0)
        threading.Thread(
            target=self._run_workflow_async,
            args=(Path(input_dir), Path(output_dir), rename_params, wm_params, compress_params),
            daemon=True,
        ).start()

    def _run_workflow_async(
        self,
        input_dir: Path,
        output_dir: Path,
        rename_params: tuple[str, str, str] | None,
        wm_params: tuple[str, str, int, int] | None,
        compress_params: tuple[int, int, int] | None,
    ) -> None:
        try:
            with tempfile.TemporaryDirectory(prefix="img_workflow_") as tmp:
                work = Path(tmp) / "work"
                total = copy_all_images(input_dir, work)
                if total == 0:
                    self.root.after(0, lambda: self._finish_info("完成", "输入目录没有可处理图片。"))
                    return

                stages: list[str] = []
                if rename_params:
                    stages.append("重命名")
                if wm_params:
                    stages.append("水印")
                if compress_params:
                    stages.append("压缩")
                else:
                    stages.append("输出")

                stage_offsets: dict[str, int] = {}
                for idx, name in enumerate(stages):
                    stage_offsets[name] = idx * total
                total_units = max(1, len(stages) * total)

                def update_progress(stage_name: str, idx: int, stage_total: int, file_name: str) -> None:
                    done_units = stage_offsets[stage_name] + idx
                    percent = max(0.0, min(100.0, done_units * 100.0 / total_units))
                    self.root.after(
                        0,
                        lambda: self._set_progress_ui(percent, f"正在{stage_name}...", f"{stage_name} {idx}/{stage_total}: {file_name}"),
                    )

                logs: list[str] = [f"已加载图片: {total} 张"]
                if rename_params:
                    renamed = run_rename(
                        work,
                        *rename_params,
                        progress_cb=lambda i, t, name: update_progress("重命名", i, t, name),
                    )
                    logs.append(f"重命名完成: {renamed} 张")
                if wm_params:
                    marked = run_watermark(
                        work,
                        *wm_params,
                        progress_cb=lambda i, t, name: update_progress("水印", i, t, name),
                    )
                    logs.append(f"水印完成: {marked} 张")

                if compress_params:
                    done = run_compress(
                        work,
                        output_dir,
                        *compress_params,
                        progress_cb=lambda i, t, name: update_progress("压缩", i, t, name),
                    )
                    logs.append(f"压缩输出完成: {done} 张")
                else:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    final_images = list_images(work)
                    for i, p in enumerate(final_images, start=1):
                        shutil.copy2(p, output_dir / p.name)
                        update_progress("输出", i, len(final_images), p.name)
                    logs.append(f"输出完成: {len(final_images)} 张")

            self.root.after(
                0,
                lambda: self._finish_info("工作流完成", "\n".join(logs) + f"\n输出目录: {output_dir}"),
            )
        except Exception as exc:  # pragma: no cover
            self.root.after(0, lambda: self._finish_error("工作流失败", str(exc)))

    def _finish_info(self, title: str, msg: str) -> None:
        self.run_btn.config(state="normal")
        self.status_var.set("就绪")
        self.detail_var.set("")
        self.progress_var.set(100.0)
        messagebox.showinfo(title, msg, parent=self.root)

    def _finish_error(self, title: str, msg: str) -> None:
        self.run_btn.config(state="normal")
        self.status_var.set("就绪")
        self.detail_var.set("")
        messagebox.showerror(title, msg, parent=self.root)

    def _set_progress_ui(self, percent: float, status: str, detail: str) -> None:
        self.progress_var.set(percent)
        self.status_var.set(status)
        self.detail_var.set(detail)


def main() -> None:
    root = tk.Tk()
    WorkflowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
