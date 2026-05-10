"""自动参数表单 — 根据 ToolParams dataclass 的字段类型自动构建 tkinter 表单。"""

import dataclasses
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, get_args, get_origin, get_type_hints

from core.tool_base import ToolParams

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore[assignment]


def _resolve_type(raw):
    """将字符串注解解析为真实类型。处理被 PEP 563 字符串化的类型。"""
    if isinstance(raw, str):
        mapping = {"int": int, "str": str, "bool": bool, "float": float, "Path": Path}
        return mapping.get(raw, str)
    return raw


class ParamForm(ttk.Frame):
    """根据 ToolParams 的子类 dataclass 自动生成表单。"""

    def __init__(self, parent: tk.Widget, params_cls: type[ToolParams]) -> None:
        super().__init__(parent)
        self._params_cls = params_cls
        self._widgets: dict[str, tk.Widget] = {}
        self._stringvars: dict[str, tk.StringVar] = {}
        self._boolvars: dict[str, tk.BooleanVar] = {}

        # 解析真实类型（处理 from __future__ import annotations 导致的字符串化）
        self._resolved_types: dict[str, Any] = {}
        for field in dataclasses.fields(params_cls):
            self._resolved_types[field.name] = _resolve_type(field.type)

        pad = {"padx": 6, "pady": 3}
        for idx, field in enumerate(dataclasses.fields(params_cls)):
            label = ttk.Label(self, text=f"{field.name}:")
            label.grid(row=idx, column=0, sticky="e", **pad)

            widget = self._build_widget(field)
            widget.grid(row=idx, column=1, sticky="ew", **pad)
            self._widgets[field.name] = widget

        self.columnconfigure(1, weight=1)

    def _build_widget(self, field: dataclasses.Field) -> tk.Widget:
        field_type = field.type
        origin = get_origin(field_type)
        args = get_args(field_type)

        # Optional[X] → 内部类型 X
        if type(None) in args:
            args = tuple(a for a in args if a is not type(None))
            field_type = args[0] if args else field_type
            origin = get_origin(field_type)
            args = get_args(field_type)

        # 解析字符串注解
        resolved_type = self._resolved_types[field.name]

        default = field.default if field.default is not dataclasses.MISSING else field.default_factory
        if default is not dataclasses.MISSING and callable(default):
            default = default()

        # Literal → Combobox
        if origin is Literal:
            values = [str(v) for v in args]
            sv = tk.StringVar(value=str(default) if default is not dataclasses.MISSING else values[0])
            self._stringvars[field.name] = sv
            cb = ttk.Combobox(self, textvariable=sv, values=values, state="readonly", width=22)
            return cb

        # bool → Checkbutton
        if resolved_type is bool:
            bv = tk.BooleanVar(value=bool(default) if default is not dataclasses.MISSING else False)
            self._boolvars[field.name] = bv
            ch = ttk.Checkbutton(self, variable=bv)
            return ch

        # int / float → Entry
        if resolved_type in (int, float):
            init = str(default) if default is not dataclasses.MISSING else ""
            sv = tk.StringVar(value=init)
            self._stringvars[field.name] = sv
            e = ttk.Entry(self, textvariable=sv, width=24)
            return e

        # Path → Entry + 浏览按钮
        if resolved_type is Path:
            init = str(default) if default is not dataclasses.MISSING else ""
            sv = tk.StringVar(value=init)
            self._stringvars[field.name] = sv
            frame = ttk.Frame(self)
            e = ttk.Entry(frame, textvariable=sv, width=18)
            e.pack(side="left", fill="x", expand=True)
            btn = ttk.Button(
                frame, text="浏览", width=6,
                command=lambda sv=sv: self._browse_path(sv),
            )
            btn.pack(side="right", padx=(4, 0))
            return frame

        # str 及其他 → Entry
        init = str(default) if default is not dataclasses.MISSING else ""
        sv = tk.StringVar(value=init)
        self._stringvars[field.name] = sv
        e = ttk.Entry(self, textvariable=sv, width=24)
        return e

    @staticmethod
    def _browse_path(sv: tk.StringVar) -> None:
        path = filedialog.askdirectory(title="选择路径")
        if path:
            sv.set(path)

    def get_params(self) -> ToolParams:
        """读取表单值，返回 ToolParams 实例。"""
        kwargs: dict[str, Any] = {}
        for field in dataclasses.fields(self._params_cls):
            if field.name in self._boolvars:
                kwargs[field.name] = self._boolvars[field.name].get()
            elif field.name in self._stringvars:
                raw = self._stringvars[field.name].get()
                resolved_type = self._resolved_types[field.name]
                if resolved_type is int:
                    try:
                        kwargs[field.name] = int(raw) if raw else 0
                    except ValueError:
                        kwargs[field.name] = raw
                elif resolved_type is float:
                    try:
                        kwargs[field.name] = float(raw) if raw else 0.0
                    except ValueError:
                        kwargs[field.name] = raw
                else:
                    kwargs[field.name] = raw
        return self._params_cls(**kwargs)
