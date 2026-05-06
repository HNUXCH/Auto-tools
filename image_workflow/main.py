"""图片工作流：重命名 → 水印 → 压缩，支持中途取消，原图零修改。"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

# ── 常量 ──────────────────────────────────────────────────

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

# Windows 常用中文字体（按优先级排列）
_CANDIDATE_FONTS = (
    "msyh.ttc",       # 微软雅黑
    "msyhbd.ttc",     # 微软雅黑 Bold
    "simhei.ttf",     # 黑体
    "simsun.ttc",     # 宋体
    "simkai.ttf",     # 楷体
    "simfang.ttf",    # 仿宋
    "arial.ttf",      # 英文 fallback
)

# ── 字体搜索 ──────────────────────────────────────────────


def _find_font_path() -> str | None:
    """在系统字体目录中搜索可用字体，返回第一个匹配项的路径。"""
    font_dirs = [
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
    ]
    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        for name in _CANDIDATE_FONTS:
            candidate = font_dir / name
            if candidate.exists():
                return str(candidate)
    return None


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """加载字体，优先系统中文，最终 fallback 到 PIL 默认字体。"""
    path = _find_font_path()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


# ── 工具函数 ──────────────────────────────────────────────


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


def calc_position(
    base_w: int, base_h: int, mark_w: int, mark_h: int, pos: str, margin: int = 20,
) -> tuple[int, int]:
    if pos == "top-left":
        return margin, margin
    if pos == "top-right":
        return max(margin, base_w - mark_w - margin), margin
    if pos == "bottom-left":
        return margin, max(margin, base_h - mark_h - margin)
    if pos == "center":
        return max(0, (base_w - mark_w) // 2), max(0, (base_h - mark_h) // 2)
    # bottom-right (default)
    return max(margin, base_w - mark_w - margin), max(margin, base_h - mark_h - margin)


# ── 处理函数（支持取消 + 单文件容错）──────────────────────


def run_rename(
    folder: Path,
    prefix: str,
    suffix: str,
    start_str: str,
    progress_cb: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> dict:
    """返回 {"done": int, "errors": list[str]}"""
    images = list_images(folder)
    errors: list[str] = []
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
        return {"done": 0, "errors": ["重命名阶段目标文件名冲突"]}

    # 临时名中转，避免冲突
    temp_paths: list[tuple[Path, Path]] = []
    for idx, (old_path, _) in enumerate(plans):
        tmp = old_path.with_name(f"__wf_tmp_{idx}__{old_path.name}")
        old_path.rename(tmp)
        temp_paths.append((tmp, old_path))

    renamed = 0
    for idx, (tmp, _) in enumerate(temp_paths):
        if cancel_event and cancel_event.is_set():
            break
        try:
            _, final_path = plans[idx]
            tmp.rename(final_path)
            renamed += 1
        except OSError as exc:
            errors.append(f"重命名失败 [{tmp.name}]: {exc}")
        if progress_cb:
            progress_cb(renamed, len(temp_paths), plans[idx][1].name)
    return {"done": renamed, "errors": errors}


def run_watermark(
    folder: Path,
    text: str,
    position: str,
    font_size: int,
    opacity: int,
    progress_cb: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> dict:
    """返回 {"done": int, "errors": list[str]}"""
    images = list_images(folder)
    errors: list[str] = []
    font = _load_font(font_size)
    done = 0
    for p in images:
        if cancel_event and cancel_event.is_set():
            break
        try:
            with Image.open(p) as img:
                base = img.convert("RGBA")
                overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(overlay)
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
        except Exception as exc:
            errors.append(f"水印失败 [{p.name}]: {exc}")
        if progress_cb:
            progress_cb(done, len(images), p.name)
    return {"done": done, "errors": errors}


def run_compress(
    src_folder: Path,
    dst_folder: Path,
    quality: int,
    max_width: int,
    max_height: int,
    progress_cb: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> dict:
    """返回 {"done": int, "errors": list[str]}"""
    images = list_images(src_folder)
    dst_folder.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    done = 0
    for p in images:
        if cancel_event and cancel_event.is_set():
            break
        try:
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
        except Exception as exc:
            errors.append(f"压缩失败 [{p.name}]: {exc}")
        if progress_cb:
            progress_cb(done, len(images), p.name)
    return {"done": done, "errors": errors}


# ── 参数表单（替代多个弹窗）────────────────────────────────


class ParamsForm(tk.Toplevel):
    """单页参数输入窗口，收集重命名/水印/压缩的所有参数。"""

    def __init__(
        self,
        parent: tk.Tk,
        do_rename: bool,
        do_watermark: bool,
        do_compress: bool,
    ) -> None:
        super().__init__(parent)
        self.title("工作流参数")
        self.result: dict | None = None
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 10, "pady": 4}
        row = 0

        # ── 重命名 ──
        if do_rename:
            ttk.Label(self, text="【批量重命名】", font=("", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="前缀（可空）：").grid(row=row, column=0, sticky="e", **pad)
            self.rename_prefix = ttk.Entry(self, width=24)
            self.rename_prefix.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="后缀（可空）：").grid(row=row, column=0, sticky="e", **pad)
            self.rename_suffix = ttk.Entry(self, width=24)
            self.rename_suffix.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="起始编号：").grid(row=row, column=0, sticky="e", **pad)
            self.rename_start = ttk.Entry(self, width=12)
            self.rename_start.insert(0, "001")
            self.rename_start.grid(row=row, column=1, sticky="w", **pad)
            row += 1

        # ── 水印 ──
        if do_watermark:
            ttk.Label(self, text="【文字水印】", font=("", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="水印文字：").grid(row=row, column=0, sticky="e", **pad)
            self.wm_text = ttk.Entry(self, width=24)
            self.wm_text.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="位置：").grid(row=row, column=0, sticky="e", **pad)
            self.wm_position = ttk.Combobox(
                self, width=16,
                values=["bottom-right", "bottom-left", "top-right", "top-left", "center"],
                state="readonly",
            )
            self.wm_position.current(0)
            self.wm_position.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="字体大小：").grid(row=row, column=0, sticky="e", **pad)
            self.wm_size = ttk.Spinbox(self, from_=8, to=200, width=10)
            self.wm_size.insert(0, "36")
            self.wm_size.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="透明度 (0-255)：").grid(row=row, column=0, sticky="e", **pad)
            self.wm_opacity = ttk.Spinbox(self, from_=0, to=255, width=10)
            self.wm_opacity.insert(0, "120")
            self.wm_opacity.grid(row=row, column=1, sticky="w", **pad)
            row += 1

        # ── 压缩 ──
        if do_compress:
            ttk.Label(self, text="【批量压缩】", font=("", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="JPEG 质量 (1-95)：").grid(row=row, column=0, sticky="e", **pad)
            self.cp_quality = ttk.Spinbox(self, from_=1, to=95, width=10)
            self.cp_quality.insert(0, "80")
            self.cp_quality.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="最大宽度：").grid(row=row, column=0, sticky="e", **pad)
            self.cp_max_w = ttk.Spinbox(self, from_=1, to=10000, width=10)
            self.cp_max_w.insert(0, "1920")
            self.cp_max_w.grid(row=row, column=1, sticky="w", **pad)
            row += 1
            ttk.Label(self, text="最大高度：").grid(row=row, column=0, sticky="e", **pad)
            self.cp_max_h = ttk.Spinbox(self, from_=1, to=10000, width=10)
            self.cp_max_h.insert(0, "1920")
            self.cp_max_h.grid(row=row, column=1, sticky="w", **pad)
            row += 1

        # ── 按钮 ──
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="开始执行", command=self._on_ok).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda _: self._on_ok())
        self.bind("<Escape>", lambda _: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _on_ok(self) -> None:
        self.result = {
            "rename": {
                "prefix": self.rename_prefix.get().strip() if hasattr(self, "rename_prefix") else "",
                "suffix": self.rename_suffix.get().strip() if hasattr(self, "rename_suffix") else "",
                "start": self.rename_start.get().strip() if hasattr(self, "rename_start") else "001",
            },
            "watermark": {
                "text": self.wm_text.get().strip() if hasattr(self, "wm_text") else "",
                "position": self.wm_position.get() if hasattr(self, "wm_position") else "bottom-right",
                "size": int(self.wm_size.get()) if hasattr(self, "wm_size") else 36,
                "opacity": int(self.wm_opacity.get()) if hasattr(self, "wm_opacity") else 120,
            },
            "compress": {
                "quality": int(self.cp_quality.get()) if hasattr(self, "cp_quality") else 80,
                "max_w": int(self.cp_max_w.get()) if hasattr(self, "cp_max_w") else 1920,
                "max_h": int(self.cp_max_h.get()) if hasattr(self, "cp_max_h") else 1920,
            },
        }
        self.destroy()


# ── 主 GUI ─────────────────────────────────────────────────


class WorkflowApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("图片工作流（重命名 → 水印 → 压缩）")
        self.root.geometry("520x400")
        self.root.resizable(False, False)

        self.cancel_event = threading.Event()

        self.do_rename = tk.BooleanVar(value=True)
        self.do_watermark = tk.BooleanVar(value=True)
        self.do_compress = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="就绪")
        self.detail_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0.0)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="工作流步骤（可多选）", font=("", 12, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Checkbutton(frame, text="① 批量重命名", variable=self.do_rename).pack(anchor="w", padx=20)
        ttk.Checkbutton(frame, text="② 批量文字水印", variable=self.do_watermark).pack(anchor="w", padx=20)
        ttk.Checkbutton(frame, text="③ 批量压缩输出", variable=self.do_compress).pack(anchor="w", padx=20)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        note = (
            "说明：工作流在临时目录中操作，原图不会被修改。\n"
            "点击「开始」后将依次选择输入/输出目录并填写参数。"
        )
        ttk.Label(frame, text=note, foreground="gray").pack(anchor="w")

        btn_bar = ttk.Frame(frame)
        btn_bar.pack(pady=12)
        self.run_btn = ttk.Button(btn_bar, text="▶ 开始执行", command=self.run)
        self.run_btn.pack(side="left", padx=4)
        self.cancel_btn = ttk.Button(btn_bar, text="取消", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=4)
        self.quit_btn = ttk.Button(btn_bar, text="退出", command=root.destroy)
        self.quit_btn.pack(side="left", padx=4)

        self.progress_bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=(8, 2))
        ttk.Label(frame, textvariable=self.status_var).pack()
        ttk.Label(frame, textvariable=self.detail_var, foreground="gray").pack()

    # ── 公开方法 ──────────────────────────────────────

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

        # 参数表单
        form = ParamsForm(self.root, self.do_rename.get(), self.do_watermark.get(), self.do_compress.get())
        self.root.wait_window(form)
        if form.result is None:
            return  # 用户取消

        p = form.result
        rename_params = None
        wm_params = None
        compress_params = None

        if self.do_rename.get():
            r = p["rename"]
            if not r["start"].isdigit():
                messagebox.showerror("输入错误", "起始编号必须为数字。", parent=self.root)
                return
            rename_params = (r["prefix"], r["suffix"], r["start"])

        if self.do_watermark.get():
            wm = p["watermark"]
            if not wm["text"]:
                messagebox.showerror("输入错误", "水印文字不能为空。", parent=self.root)
                return
            wm_params = (wm["text"], wm["position"], wm["size"], wm["opacity"])

        if self.do_compress.get():
            cp = p["compress"]
            compress_params = (cp["quality"], cp["max_w"], cp["max_h"])

        self._enter_running()
        threading.Thread(
            target=self._run_workflow_async,
            args=(Path(input_dir), Path(output_dir), rename_params, wm_params, compress_params),
            daemon=True,
        ).start()

    # ── 内部方法 ──────────────────────────────────────

    def _enter_running(self) -> None:
        self.cancel_event.clear()
        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.quit_btn.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("正在执行，请稍候...")
        self.detail_var.set("")

    def _enter_idle(self) -> None:
        self.run_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.quit_btn.config(state="normal")
        self.status_var.set("就绪")
        self.detail_var.set("")
        self.progress_var.set(100)

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.status_var.set("正在取消...")
        self.detail_var.set("")
        self.cancel_btn.config(state="disabled")

    def _run_workflow_async(
        self,
        input_dir: Path,
        output_dir: Path,
        rename_params: tuple[str, str, str] | None,
        wm_params: tuple[str, str, int, int] | None,
        compress_params: tuple[int, int, int] | None,
    ) -> None:
        all_errors: list[str] = []
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

                offsets = {name: i * total for i, name in enumerate(stages)}
                total_units = max(1, len(stages) * total)

                def update(stage: str, idx: int, stage_total: int, fname: str) -> None:
                    if self.cancel_event.is_set():
                        return
                    pct = max(0.0, min(100.0, (offsets[stage] + idx) * 100.0 / total_units))
                    self.root.after(0, lambda: self._set_progress(pct, f"正在{stage}...", f"{stage} {idx}/{stage_total}: {fname}"))

                logs: list[str] = [f"已加载图片: {total} 张"]

                if rename_params:
                    res = run_rename(work, *rename_params, progress_cb=lambda i, t, n: update("重命名", i, t, n), cancel_event=self.cancel_event)
                    logs.append(f"重命名完成: {res['done']} 张")
                    all_errors.extend(res["errors"])

                if wm_params and not self.cancel_event.is_set():
                    res = run_watermark(work, *wm_params, progress_cb=lambda i, t, n: update("水印", i, t, n), cancel_event=self.cancel_event)
                    logs.append(f"水印完成: {res['done']} 张")
                    all_errors.extend(res["errors"])

                if self.cancel_event.is_set():
                    logs.append("⚠ 用户取消，已处理的部分文件已丢弃。")
                    self.root.after(0, lambda: self._finish_info("已取消", "\n".join(logs)))
                    return

                if compress_params:
                    res = run_compress(work, output_dir, *compress_params, progress_cb=lambda i, t, n: update("压缩", i, t, n), cancel_event=self.cancel_event)
                    logs.append(f"压缩输出完成: {res['done']} 张")
                    all_errors.extend(res["errors"])
                else:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    final_images = list_images(work)
                    for i, p in enumerate(final_images, start=1):
                        shutil.copy2(p, output_dir / p.name)
                        update("输出", i, len(final_images), p.name)
                    logs.append(f"输出完成: {len(final_images)} 张")

                if all_errors:
                    logs.append(f"\n⚠ 以下文件处理出错 ({len(all_errors)} 项):")
                    logs.extend(all_errors[:10])  # 最多显示 10 条
                    if len(all_errors) > 10:
                        logs.append(f"  ... 及其他 {len(all_errors) - 10} 项错误")

                self.root.after(0, lambda: self._finish_info("工作流完成", "\n".join(logs) + f"\n输出目录: {output_dir}"))
        except Exception as exc:
            self.root.after(0, lambda: self._finish_error("工作流失败", str(exc)))
        finally:
            self.root.after(0, self._enter_idle)

    def _set_progress(self, percent: float, status: str, detail: str) -> None:
        self.progress_var.set(percent)
        self.status_var.set(status)
        self.detail_var.set(detail)

    def _finish_info(self, title: str, msg: str) -> None:
        self._enter_idle()
        messagebox.showinfo(title, msg, parent=self.root)

    def _finish_error(self, title: str, msg: str) -> None:
        self._enter_idle()
        messagebox.showerror(title, msg, parent=self.root)


# ── 入口 ───────────────────────────────────────────────────


def main() -> None:
    root = tk.Tk()
    WorkflowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
