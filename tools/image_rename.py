"""批量重命名图片 Tool。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


@dataclass
class ImageRenameParams(ToolParams):
    prefix: str = ""
    suffix: str = ""
    start: str = "001"


class ImageRenameTool(Tool):
    name = "批量重命名"
    name_slug = "image_rename"
    icon = "✏️"
    category = "image"
    input_mode = InputMode.DIRECTORY

    def params_type(self) -> type[ToolParams]:
        return ImageRenameParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: ImageRenameParams = params
        if not p.start.isdigit():
            return ["起始编号必须为纯数字"]
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: ImageRenameParams = params
        images = sorted(
            [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: f.name.lower(),
        )
        width = len(p.start)
        start_num = int(p.start)

        plans: list[tuple[Path, Path]] = []
        for i, old_path in enumerate(images):
            parts: list[str] = []
            if p.prefix:
                parts.append(p.prefix)
            parts.append(str(start_num + i).zfill(width))
            if p.suffix:
                parts.append(p.suffix)
            new_name = "_".join(parts) + old_path.suffix.lower()
            plans.append((old_path, old_path.with_name(new_name)))

        target_names = [new.name for _, new in plans]
        if len(target_names) != len(set(target_names)):
            return ToolResult(done=0, total=len(images), errors=["目标文件名冲突"])

        temp_paths: list[tuple[Path, Path]] = []
        for idx, (old_path, _) in enumerate(plans):
            tmp = old_path.with_name(f"__wf_tmp_{idx}__{old_path.name}")
            old_path.rename(tmp)
            temp_paths.append((tmp, old_path))

        errors: list[str] = []
        renamed = 0
        for idx, (tmp, _) in enumerate(temp_paths):
            if cancel_event.is_set():
                break
            try:
                _, final_path = plans[idx]
                tmp.rename(final_path)
                renamed += 1
            except OSError as exc:
                errors.append(f"重命名失败 [{tmp.name}]: {exc}")
            on_progress(renamed, len(temp_paths), plans[idx][1].name)

        return ToolResult(done=renamed, total=len(temp_paths), errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(ImageRenameTool())
