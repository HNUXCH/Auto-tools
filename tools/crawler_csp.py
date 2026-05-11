"""CCF CSP 软件能力认证 — 历年真题爬虫 Tool。

数据来源: 曙梦 OJ (oj.shumeng.tech)
共 108 道题，覆盖 2013~2026 年全部认证。
每道题输出为独立 Markdown 文件 + 汇总索引 CSV。
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

BASE_URL = "https://oj.shumeng.tech"
LIST_URL = f"{BASE_URL}/p?q=category%3ACSP"
DETAIL_URL = f"{BASE_URL}/p/{{pid}}"
REQUEST_DELAY = 0.8  # 请求间隔，避免给服务器造成压力
REQUEST_TIMEOUT = 20


@dataclass
class CrawlerCspParams(ToolParams):
    pass  # 无需参数，全量抓取


class CrawlerCspTool(Tool):
    name = "CSP 真题爬虫"
    name_slug = "crawler_csp"
    icon = "📝"
    category = "web"
    input_mode = InputMode.NONE

    def params_type(self) -> type[ToolParams]:
        return CrawlerCspParams

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Auto-tools CSP Crawler/1.0 (educational use)",
        })

        # ── 第一步：收集所有题目 ID ──
        problem_ids = self._collect_problem_ids(session, cancel_event)
        if cancel_event.is_set():
            return ToolResult(done=0, total=0, errors=["用户取消"])
        if not problem_ids:
            return ToolResult(done=0, total=0, errors=["未找到任何 CSP 题目"])

        total = len(problem_ids)
        on_progress(0, total, f"发现 {total} 道 CSP 题目，开始抓取...")

        # ── 第二步：逐题抓取详情 ──
        errors: list[str] = []
        rows: list[dict] = []
        problems_dir = work_dir / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)

        for i, pid in enumerate(problem_ids):
            if cancel_event.is_set():
                break
            try:
                row = self._fetch_problem(session, pid, problems_dir)
                rows.append(row)
                on_progress(i + 1, total, f"{pid}: {row['title']}")
            except Exception as exc:
                errors.append(f"{pid}: {exc}")
                on_progress(i + 1, total, f"{pid}: 失败")

            # 请求间隔
            time.sleep(REQUEST_DELAY)

        # ── 第三步：写汇总索引 CSV ──
        self._write_index(work_dir, rows)

        return ToolResult(done=len(rows), total=total, errors=errors)

    # ── 收集题目 ID ──

    def _collect_problem_ids(self, session: requests.Session, cancel_event: threading.Event) -> list[str]:
        """从搜索分页收集所有 CSP 题目 ID。"""
        ids: list[str] = []
        pattern = re.compile(r"^/p/(CSP\d{6}[A-E])$")
        page = 1

        while True:
            if cancel_event.is_set():
                break
            try:
                url = f"{LIST_URL}&page={page}" if page > 1 else LIST_URL
                resp = session.get(url, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                found = 0
                for a in soup.find_all("a", href=True):
                    m = pattern.match(a.get("href", ""))
                    if m:
                        pid = m.group(1)
                        if pid not in ids:
                            ids.append(pid)
                            found += 1

                if found == 0:
                    break
                page += 1
                time.sleep(REQUEST_DELAY)
            except Exception:
                break

        return sorted(ids)

    # ── 抓取单题 ──

    def _fetch_problem(self, session: requests.Session, pid: str, out_dir: Path) -> dict:
        """抓取单个题目的详情，保存 Markdown，返回索引行。"""
        url = DETAIL_URL.format(pid=pid)
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        # 从 HTML 中提取 UiContextNew 的 JSON payload
        html = resp.text
        try:
            data = self._extract_payload(html)
            pdoc = data["pdoc"]
            content_raw = pdoc.get("content", "{}")
            if isinstance(content_raw, str):
                content = json.loads(content_raw)
            else:
                content = content_raw
            markdown = content.get("zh", "") or content.get("en", "") or ""
            tags = pdoc.get("tag", [])
        except Exception:
            # 回退：从 og:description meta 提取信息
            markdown, tags = self._fallback_extract(html, pid)

        # 提取标题和元信息
        title = self._extract_title(markdown, pid)
        time_limit, space_limit = self._extract_limits(markdown)

        # 写 Markdown 文件
        md_path = out_dir / f"{pid}.md"
        md_path.write_text(markdown, encoding="utf-8")

        return {
            "problem_id": pid,
            "title": title,
            "year": pid[3:7],
            "month": pid[7:9],
            "problem_index": pid[9],
            "time_limit": time_limit,
            "space_limit": space_limit,
            "tags": ",".join(tags) if tags else "",
            "file": f"problems/{pid}.md",
        }

    @staticmethod
    def _extract_payload(html: str) -> dict:
        """从 HTML 中提取 window.UiContextNew 的 JSON。"""
        idx = html.index("UiContextNew")
        quote_start = html.index("'", html.index("=", idx))
        # 找匹配的闭合单引号（跳过转义）
        i = quote_start + 1
        while i < len(html):
            if html[i] == "'":
                bs = 0
                j = i - 1
                while j >= 0 and html[j] == "\\":
                    bs += 1
                    j -= 1
                if bs % 2 == 0:
                    break
            i += 1
        json_str = html[quote_start + 1 : i]
        # 修复 Hydro OJ 的 content 字段三重转义问题
        # \\" 在 JSON 中解为 \" (backslash+end_of_string)，导致解析失败
        # 改为 \" 即可保持引号在字符串内
        json_str = json_str.replace('\\\\\"', '\\\"')
        return json.loads(json_str)

    @staticmethod
    def _extract_title(md: str, pid: str) -> str:
        """从 Markdown 或 HTML meta 提取标题。"""
        for line in md.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not line.startswith("## "):
                title = line[2:].strip()
                # 去除 "CSP201809A. 卖菜 - 曙梦 OJ" 格式中的 ID 和后缀
                title = re.sub(rf"^{pid}\.\s*", "", title)
                title = re.sub(r"\s*-\s*曙梦\s*OJ$", "", title)
                if title:
                    return title
        return pid

    @staticmethod
    def _extract_limits(md: str) -> tuple[str, str]:
        """提取时间限制和空间限制。"""
        time_limit = ""
        space_limit = ""
        for line in md.split("\n"):
            line = line.strip()
            if "时间限制" in line:
                m = re.search(r"(\d+\.?\d*)\s*秒", line)
                if m:
                    time_limit = f"{m.group(1)}s"
            elif "空间限制" in line:
                m = re.search(r"(\d+)\s*(MB|GB)", line)
                if m:
                    space_limit = f"{m.group(1)}{m.group(2)}"
        return time_limit, space_limit

    @staticmethod
    def _fallback_extract(html: str, pid: str) -> tuple[str, list[str]]:
        """当 JSON 解析失败时，从 HTML meta 标签提取基本信息。"""
        soup = BeautifulSoup(html, "html.parser")
        og_desc = soup.find("meta", property="og:description")
        og_title = soup.find("meta", property="og:title")
        title_text = og_title["content"] if og_title else pid

        markdown = f"# {title_text}\n\n"
        if og_desc:
            markdown += og_desc["content"]
        return markdown, []

    # ── 写索引 CSV ──

    def _write_index(self, work_dir: Path, rows: list[dict]) -> None:
        import csv

        csv_path = work_dir / "csp_index.csv"
        fieldnames = [
            "problem_id", "title", "year", "month", "problem_index",
            "time_limit", "space_limit", "tags", "file",
        ]
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


from core.registry import ToolRegistry  # noqa: E402

ToolRegistry.register(CrawlerCspTool())
