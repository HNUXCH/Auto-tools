"""工具注册表 — 单一全局注册点，按 slug / category 查找工具。"""

from __future__ import annotations

from .tool_base import Tool


class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        if tool.name_slug in cls._tools:
            raise ValueError(f"工具 {tool.name_slug} 已注册")
        cls._tools[tool.name_slug] = tool

    @classmethod
    def get_all(cls) -> list[Tool]:
        return list(cls._tools.values())

    @classmethod
    def get_by_slug(cls, slug: str) -> Tool:
        if slug not in cls._tools:
            raise KeyError(f"未找到工具: {slug}")
        return cls._tools[slug]

    @classmethod
    def get_by_category(cls, category: str) -> list[Tool]:
        return [t for t in cls._tools.values() if t.category == category]
