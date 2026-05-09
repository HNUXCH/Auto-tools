"""工具抽象接口 — 所有工具必须满足此协议。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import threading
from typing import Callable


class InputMode(Enum):
    DIRECTORY = auto()   # 批处理目录，流水线适用
    FILES = auto()       # 选择多个文件，独立运行
    NONE = auto()        # 无文件输入（如爬虫），独立运行


@dataclass
class ToolParams:
    """工具参数基类。子类用 dataclass 声明字段，平台自动生成表单。"""
    pass


@dataclass
class ToolResult:
    done: int
    total: int
    errors: list[str] = field(default_factory=list)


class Tool:
    """工具协议 — 平台只依赖此接口。

    子类必须提供:
      name: str         — 显示名
      name_slug: str    — 程序标识
      icon: str         — emoji 图标
      category: str     — "image" | "pdf" | "web"
      input_mode: InputMode — 输入模式

    子类必须实现:
      params_type() -> type[ToolParams]
      run(work_dir, params, on_progress, cancel_event) -> ToolResult
    """

    name: str
    name_slug: str
    icon: str
    category: str
    input_mode: InputMode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return ToolParams

    def validate_params(self, params: ToolParams) -> list[str]:
        """返回错误列表。空列表表示通过。子类可覆盖。"""
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: Callable[[int, int, str], None],
        cancel_event: threading.Event,
    ) -> ToolResult:
        raise NotImplementedError


# 类型别名，方便平台代码引用
ProgressCallback = Callable[[int, int, str], None]
