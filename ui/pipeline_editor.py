"""流水线编辑器 — 添加/移除/配置流水线步骤。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core.pipeline import PipelineStep
from core.tool_base import Tool, ToolParams


class PipelineEditor(ttk.LabelFrame):
    """流水线步骤编排面板。每个步骤：工具名 + 参数按钮 + 删除。"""

    def __init__(self, parent: tk.Widget, tools: list[Tool]) -> None:
        super().__init__(parent, text="流水线编辑器", padding=8)
        self._tools = {t.name_slug: t for t in tools}
        self._steps: list[PipelineStep] = []
        self._step_frames: list[ttk.Frame] = []

        self._controls = ttk.Frame(self)
        self._controls.pack(fill="x", pady=(0, 6))

        self._tool_var = tk.StringVar()
        tool_names = [t.name for t in tools]
        if tool_names:
            self._tool_var.set(tool_names[0])
        cb = ttk.Combobox(
            self._controls, textvariable=self._tool_var,
            values=tool_names, state="readonly", width=20,
        )
        cb.pack(side="left", padx=(0, 6))

        ttk.Button(self._controls, text="+ 添加步骤", command=self._add_step).pack(side="left")

    def get_steps(self) -> list[PipelineStep]:
        return list(self._steps)

    def _add_step(self) -> None:
        name = self._tool_var.get()
        tool = self._tools.get(self._tool_name_to_slug(name))
        if tool is None:
            return
        params_cls = tool.params_type()
        params = params_cls()
        step = PipelineStep(tool=tool, params=params)
        self._steps.append(step)

        row = len(self._step_frames)
        frame = ttk.Frame(self)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text=f"{tool.icon} {tool.name}", width=22).pack(side="left")
        ttk.Button(frame, text="参数", width=5, command=lambda i=row: self._edit_params(i)).pack(side="right", padx=2)
        ttk.Button(frame, text="×", width=3, command=lambda i=row: self._remove_step(i)).pack(side="right")

        self._step_frames.append(frame)

    def _edit_params(self, index: int) -> None:
        from ui.widgets.param_form import ParamForm

        step = self._steps[index]
        params_cls = step.tool.params_type()

        dialog = tk.Toplevel(self)
        dialog.title(f"参数 — {step.tool.name}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        form = ParamForm(dialog, params_cls)
        form.pack(padx=12, pady=12, fill="both", expand=True)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))

        def _on_ok() -> None:
            step.params = form.get_params()
            errs = step.tool.validate_params(step.params)
            if errs:
                messagebox.showerror("参数错误", "\n".join(errs), parent=dialog)
                return
            dialog.destroy()

        ttk.Button(btn_frame, text="确定", command=_on_ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)
        dialog.bind("<Return>", lambda e: _on_ok())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _remove_step(self, index: int) -> None:
        del self._steps[index]
        self._step_frames[index].destroy()
        del self._step_frames[index]
        # 重新绑定 index
        for i, f in enumerate(self._step_frames):
            for child in f.winfo_children():
                if isinstance(child, ttk.Button):
                    if child.cget("text") == "参数":
                        child.configure(command=lambda idx=i: self._edit_params(idx))
                    elif child.cget("text") == "×":
                        child.configure(command=lambda idx=i: self._remove_step(idx))

    def _tool_name_to_slug(self, name: str) -> str:
        for t in self._tools.values():
            if t.name == name:
                return t.name_slug
        return ""
