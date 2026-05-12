"""在线判题 Tool — 启动本地 OJ 服务器，在浏览器中编辑和验证 CSP 代码。

依赖: Flask（需 pip install flask）
"""

from __future__ import annotations

import dataclasses
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult


@dataclass
class CodeJudgeParams(ToolParams):
    problems_dir: Path = Path(".")  # CSP 题目 Markdown 文件目录（ParamForm 会用浏览按钮选择）


class CodeJudgeTool(Tool):
    name = "在线判题"
    name_slug = "code_judge"
    icon = "⚖️"
    category = "web"
    input_mode = InputMode.NONE

    def params_type(self) -> type[ToolParams]:
        return CodeJudgeParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: CodeJudgeParams = params
        pd = Path(p.problems_dir) if isinstance(p.problems_dir, str) else p.problems_dir
        pd = pd.resolve()
        if not pd.exists():
            return [f"题目目录不存在: {pd}\n请选择 CSP 真题爬虫输出目录下的 problems/ 文件夹"]
        if not list(pd.glob("*.md")):
            return [f"所选目录没有 .md 题目文件: {pd}"]
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: CodeJudgeParams = params

        pd = Path(p.problems_dir) if isinstance(p.problems_dir, str) else p.problems_dir
        problems_dir = pd.resolve()

        if not problems_dir.exists() or not list(problems_dir.glob("*.md")):
            return ToolResult(
                done=0, total=1,
                errors=[f"题目目录无效: {problems_dir}\n请先用 CSP 真题爬虫下载题目到一个目录。"],
            )

        md_files = list(problems_dir.glob("*.md"))
        if not md_files:
            return ToolResult(
                done=0, total=1,
                errors=[f"题目目录没有 .md 文件: {problems_dir}"],
            )

        on_progress(0, 1, f"启动判题服务器 ({len(md_files)} 道题目)...")

        try:
            from ui.judge_server import app, set_problems_dir
        except ImportError as e:
            return ToolResult(done=0, total=1, errors=[f"导入失败: {e}\n请确保已安装 Flask: pip install flask"])

        set_problems_dir(problems_dir)

        # 找一个空闲端口
        import socket as _socket
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        # 在后台线程启动 Flask
        def _start_server() -> None:
            import logging
            logging.getLogger("werkzeug").setLevel(logging.WARNING)
            app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

        server_thread = threading.Thread(target=_start_server, daemon=True)
        server_thread.start()

        # 等待服务器就绪
        import time, requests as _requests
        url = f"http://127.0.0.1:{port}"
        for _ in range(30):
            time.sleep(0.1)
            try:
                r = _requests.get(f"{url}/api/problems", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                pass

        on_progress(1, 1, f"服务器已启动: {url}")

        # 打开浏览器
        webbrowser.open(url)

        return ToolResult(
            done=1, total=1,
            errors=[],
        )


from core.registry import ToolRegistry  # noqa: E402

ToolRegistry.register(CodeJudgeTool())
