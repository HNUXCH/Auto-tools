"""预设系统 — 保存 / 加载 / 列出 / 删除流水线预设（JSON）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .registry import ToolRegistry

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"


@dataclass
class PresetStep:
    tool_slug: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Preset:
    name: str
    steps: list[PresetStep] = field(default_factory=list)


def _path(name: str) -> Path:
    return PRESETS_DIR / f"{name}.json"


def save_preset(preset: Preset) -> Path:
    """保存预设到 presets/<name>.json，覆盖同名文件。"""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "name": preset.name,
        "steps": [{"tool": s.tool_slug, "params": s.params} for s in preset.steps],
    }
    path = _path(preset.name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_preset(name: str) -> Preset:
    """从 JSON 加载预设，通过 ToolRegistry 还原每个步骤的 ToolParams。"""
    path = _path(name)
    if not path.exists():
        raise FileNotFoundError(f"预设文件不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    steps: list[PresetStep] = []
    for s in data["steps"]:
        tool = ToolRegistry.get_by_slug(s["tool"])
        params_cls = tool.params_type()
        params_instance = params_cls(**s["params"])
        steps.append(PresetStep(tool_slug=s["tool"], params=params_instance.__dict__))
    return Preset(name=data["name"], steps=steps)


def list_presets() -> list[str]:
    """返回预设名列表（不含 .json 扩展名）。"""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for p in PRESETS_DIR.glob("*.json"):
        names.append(p.stem)
    return sorted(names)


def delete_preset(name: str) -> bool:
    path = _path(name)
    if path.exists():
        path.unlink()
        return True
    return False
