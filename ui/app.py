"""Auto-tools 主窗口 — 工具箱面板 + 流水线编辑器 + 执行控制。"""

from __future__ import annotations

import dataclasses
import shutil
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from core.pipeline import PipelineStep, PipelineResult, execute_pipeline
from core.registry import ToolRegistry
from core.tool_base import InputMode

from .pipeline_editor import PipelineEditor
from .preset_dialog import show_load_dialog, show_save_dialog
from .widgets.progress_panel import ProgressPanel


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Auto-tools")
        root.geometry("580x520")
        root.minsize(480, 400)

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)

        # ── 工具箱区域 ──
        ttk.Label(outer, text="工具箱", font=("", 12, "bold")).pack(anchor="w", pady=(0, 4))
        self._build_toolbox(outer)

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=8)

        # ── 流水线编辑器 ──
        tools = ToolRegistry.get_all()
        self._editor = PipelineEditor(outer, tools)
        self._editor.pack(fill="both", expand=False, pady=(0, 6))

        # ── 进度面板 ──
        self._progress = ProgressPanel(outer)
        self._progress.pack(fill="x", pady=(0, 8))

        # ── 按钮栏 ──
        btn_bar = ttk.Frame(outer)
        btn_bar.pack(fill="x")

        self._run_btn = ttk.Button(btn_bar, text="▶ 执行", command=self._run)
        self._run_btn.pack(side="left", padx=2)

        self._cancel_btn = ttk.Button(btn_bar, text="⏹ 取消", command=self._cancel, state="disabled")
        self._cancel_btn.pack(side="left", padx=2)

        ttk.Button(btn_bar, text="📋 保存预设", command=self._save_preset).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="📂 加载预设", command=self._load_preset).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="退出", command=root.destroy).pack(side="right", padx=2)

        self._cancel_event = threading.Event()
        self._running = False

    # ── 工具箱 ──

    def _build_toolbox(self, parent: ttk.Frame) -> None:
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="x", pady=(0, 4))

        categories = ["image", "pdf", "web"]
        labels = ["📷 图片", "📄 PDF", "🌐 网页"]
        for cat, label in zip(categories, labels):
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=label)
            tools = ToolRegistry.get_by_category(cat)
            for t in tools:
                frame = ttk.Frame(tab)
                frame.pack(fill="x", padx=4, pady=2)

                ttk.Label(frame, text=f"{t.icon} {t.name}", width=20).pack(side="left")

                if t.input_mode == InputMode.DIRECTORY:
                    ttk.Button(
                        frame, text="加入流水线", width=10,
                        command=lambda tool=t: self._add_to_pipeline(tool),
                    ).pack(side="right")
                else:
                    ttk.Button(
                        frame, text="▶ 立即运行", width=10,
                        command=lambda tool=t: self._run_standalone(tool),
                    ).pack(side="right")

    def _add_to_pipeline(self, tool) -> None:
        name = tool.name
        self._editor._tool_var.set(name)
        self._editor._add_step()

    def _run_standalone(self, tool) -> None:
        from ui.widgets.param_form import ParamForm
        from tkinter import filedialog
        from pathlib import Path

        params_cls = tool.params_type()
        if dataclasses.fields(params_cls):
            dialog = tk.Toplevel(self.root)
            dialog.title(f"参数 — {tool.name}")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.resizable(False, False)

            form = ParamForm(dialog, params_cls)
            form.pack(padx=12, pady=12, fill="both", expand=True)

            result_params = None

            def _ok() -> None:
                nonlocal result_params
                p = form.get_params()
                errs = tool.validate_params(p)
                if errs:
                    messagebox.showerror("参数错误", "\n".join(errs), parent=dialog)
                    return
                result_params = p
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=(0, 10))
            ttk.Button(btn_frame, text="确定", command=_ok).pack(side="left", padx=4)
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)
            dialog.bind("<Return>", lambda e: _ok())
            dialog.bind("<Escape>", lambda e: dialog.destroy())
            dialog.wait_window()

            if result_params is None:
                return
        else:
            result_params = params_cls()

        # 文件选择（独立工具需要输入文件和输出目录）
        input_files: list[Path] | None = None
        output_dir: Path | None = None

        if tool.input_mode == InputMode.NONE:
            if tool.category == "pdf":
                filetypes = [("PDF files", "*.pdf")] if tool.name_slug == "pdf_to_word" else [("Word files", "*.docx")]
                files = filedialog.askopenfilenames(parent=self.root, title="选择输入文件", filetypes=filetypes)
                if not files:
                    return
                input_files = [Path(f) for f in files]
            elif tool.category == "web":
                input_files = []  # 爬虫不需要输入文件
            # 选择输出目录
            out = filedialog.askdirectory(parent=self.root, title="选择输出目录")
            if not out:
                return
            output_dir = Path(out)

        self._enter_running()
        threading.Thread(
            target=self._run_standalone_async,
            args=(tool, result_params, input_files, output_dir),
            daemon=True,
        ).start()

    def _run_standalone_async(self, tool, params, input_files=None, output_dir=None) -> None:
        import tempfile
        from pathlib import Path

        try:
            with tempfile.TemporaryDirectory(prefix="autotools_") as tmp:
                work = Path(tmp) / "work"
                work.mkdir()

                # 复制输入文件到 work（独立工具）
                if input_files:
                    for f in input_files:
                        shutil.copy2(f, work / f.name)

                def _progress(i: int, t: int, name: str) -> None:
                    pct = (i / max(t, 1)) * 100
                    self.root.after(0, lambda: self._progress.update(pct, tool.name, f"{i}/{t}: {name}"))

                result = tool.run(work, params, _progress, self._cancel_event)

                # 复制输出到用户目录
                if output_dir:
                    for f in work.iterdir():
                        if f.is_file():
                            shutil.copy2(f, output_dir / f.name)

            def _finish() -> None:
                self._enter_idle()
                if result.errors:
                    msg = f"完成 {result.done}/{result.total}\n⚠ {len(result.errors)} 个错误\n" + "\n".join(result.errors[:5])
                else:
                    msg = f"完成 {result.done}/{result.total}"
                    if output_dir:
                        msg += f"\n输出目录: {output_dir}"
                messagebox.showinfo(tool.name, msg)

            self.root.after(0, _finish)
        except Exception as exc:
            self.root.after(0, lambda: self._finish_error(tool.name, str(exc)))
            self.root.after(0, self._enter_idle)

    # ── 执行 ──

    def _run(self) -> None:
        if self._running:
            return
        steps = self._editor.get_steps()
        if not steps:
            messagebox.showerror("提示", "流水线至少需要一个步骤。", parent=self.root)
            return

        # 验证参数
        for step in steps:
            errs = step.tool.validate_params(step.params)
            if errs:
                messagebox.showerror(
                    f"参数错误 — {step.tool.name}",
                    "\n".join(errs),
                    parent=self.root,
                )
                return

        # 主线程弹目录选择
        from tkinter import filedialog
        input_dir = filedialog.askdirectory(parent=self.root, title="选择输入目录")
        if not input_dir:
            return
        output_dir = filedialog.askdirectory(parent=self.root, title="选择输出目录")
        if not output_dir:
            return

        self._enter_running()
        threading.Thread(target=self._run_async, args=(steps, input_dir, output_dir), daemon=True).start()

    def _run_async(self, steps: list[PipelineStep], input_dir: str, output_dir: str) -> None:
        result = execute_pipeline(
            steps, input_dir, output_dir,
            cancel_event=self._cancel_event,
            on_status=lambda p, t, d: self.root.after(0, lambda: self._progress.update(p, t, d)),
        )

        def _finish() -> None:
            self._enter_idle()
            if result is None:
                messagebox.showerror("流水线失败", "参数验证失败。")
                return
            if result.success:
                messagebox.showinfo("流水线完成", "\n".join(result.logs))
            else:
                messagebox.showerror("流水线未完成", "\n".join(result.logs))

        self.root.after(0, _finish)

    def _finish_error(self, title: str, msg: str) -> None:
        self._enter_idle()
        messagebox.showerror(title, msg)

    # ── 预设 ──

    def _save_preset(self) -> None:
        show_save_dialog(self.root, self._editor.get_steps())

    def _load_preset(self) -> None:
        steps = show_load_dialog(self.root)
        if steps:
            for _ in range(len(self._editor._step_frames)):
                self._editor._remove_step(0)
            for step in steps:
                self._editor._tool_var.set(step.tool.name)
                self._editor._add_step()
                self._editor._steps[-1].params = step.params

    # ── 状态 ──

    def _enter_running(self) -> None:
        self._cancel_event.clear()
        self._running = True
        self._run_btn.config(state="disabled")
        self._cancel_btn.config(state="normal")
        self._progress.reset()

    def _enter_idle(self) -> None:
        self._running = False
        self._run_btn.config(state="normal")
        self._cancel_btn.config(state="disabled")

    def _cancel(self) -> None:
        self._cancel_event.set()
        self._progress.update(0, "正在取消...", "")
        self._cancel_btn.config(state="disabled")
