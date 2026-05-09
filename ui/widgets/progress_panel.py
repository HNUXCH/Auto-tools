"""进度面板 — 进度条 + 状态文本 + 详情文本。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ProgressPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.progress_var = tk.DoubleVar(value=0.0)
        self._bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self._bar.pack(fill="x", pady=(4, 2))

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status_var).pack()

        self.detail_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.detail_var, foreground="gray").pack()

    def update(self, percent: float, status: str, detail: str) -> None:
        self.progress_var.set(percent)
        self.status_var.set(status)
        self.detail_var.set(detail)

    def reset(self) -> None:
        self.progress_var.set(0)
        self.status_var.set("就绪")
        self.detail_var.set("")
