"""预设对话框 — 保存/加载/删除流水线预设。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core import preset
from core.pipeline import PipelineStep
from core.registry import ToolRegistry


def show_save_dialog(parent: tk.Widget, steps: list[PipelineStep]) -> None:
    """弹出保存预设对话框。"""
    if not steps:
        messagebox.showinfo("提示", "流水线为空，无法保存。", parent=parent)
        return

    dialog = tk.Toplevel(parent)
    dialog.title("保存预设")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    pad = {"padx": 10, "pady": 6}
    ttk.Label(dialog, text="预设名称:").pack(**pad)
    name_var = tk.StringVar()
    name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
    name_entry.pack(padx=10, pady=(0, 6))
    name_entry.focus()

    def _save() -> None:
        name = name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "预设名称不能为空。", parent=dialog)
            return
        p = preset.Preset(
            name=name,
            steps=[
                preset.PresetStep(
                    tool_slug=s.tool.name_slug,
                    params=s.params.__dict__,
                )
                for s in steps
            ],
        )
        path = preset.save_preset(p)
        messagebox.showinfo("已保存", f"预设已保存: {path}", parent=dialog)
        dialog.destroy()

    ttk.Button(dialog, text="保存", command=_save).pack(pady=(0, 10))
    dialog.bind("<Return>", lambda e: _save())
    dialog.bind("<Escape>", lambda e: dialog.destroy())


def show_load_dialog(parent: tk.Widget) -> list[PipelineStep] | None:
    """弹出加载预设对话框。返回 PipelineStep 列表或 None（取消）。"""
    names = preset.list_presets()
    if not names:
        messagebox.showinfo("提示", "没有已保存的预设。", parent=parent)
        return None

    dialog = tk.Toplevel(parent)
    dialog.title("加载预设")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    ttk.Label(dialog, text="选择预设:").pack(padx=12, pady=(12, 6))

    lb = tk.Listbox(dialog, height=min(8, len(names)), width=28)
    for n in names:
        lb.insert("end", n)
    lb.pack(padx=12, pady=(0, 8))

    result: list[PipelineStep] | None = None

    def _load() -> None:
        nonlocal result
        sel = lb.curselection()
        if not sel:
            return
        name = names[sel[0]]
        p = preset.load_preset(name)
        steps: list[PipelineStep] = []
        for ps in p.steps:
            tool = ToolRegistry.get_by_slug(ps.tool_slug)
            params = tool.params_type()(**ps.params)
            steps.append(PipelineStep(tool=tool, params=params))
        result = steps
        dialog.destroy()

    def _delete() -> None:
        sel = lb.curselection()
        if not sel:
            return
        name = names[sel[0]]
        if messagebox.askyesno("确认", f"确定删除预设「{name}」？", parent=dialog):
            preset.delete_preset(name)
            messagebox.showinfo("已删除", f"预设「{name}」已删除。", parent=dialog)
            dialog.destroy()

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(0, 10))
    ttk.Button(btn_frame, text="加载", command=_load).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="删除", command=_delete).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=4)

    dialog.bind("<Escape>", lambda e: dialog.destroy())
    dialog.wait_window()
    return result
