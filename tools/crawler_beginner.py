"""入门爬虫 Tool — 抓取 quotes.toscrape.com → CSV（独立运行）。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import threading

import requests
from bs4 import BeautifulSoup

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

BASE_URL = "https://quotes.toscrape.com"


@dataclass
class CrawlerBeginnerParams(ToolParams):
    max_pages: int = 3


class CrawlerBeginnerTool(Tool):
    name = "入门爬虫"
    name_slug = "crawler_beginner"
    icon = "🕷️"
    category = "web"
    input_mode = InputMode.NONE

    def params_type(self) -> type[ToolParams]:
        return CrawlerBeginnerParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: CrawlerBeginnerParams = params
        if p.max_pages < 1:
            return ["页数至少为 1"]
        return []

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: CrawlerBeginnerParams = params
        all_items: list[dict[str, str]] = []
        url = BASE_URL
        errors: list[str] = []

        for page_num in range(p.max_pages):
            if cancel_event.is_set():
                break
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for quote in soup.select("div.quote"):
                    text_el = quote.select_one("span.text")
                    author_el = quote.select_one("small.author")
                    tags = [t.get_text(strip=True) for t in quote.select("div.tags a.tag")]
                    all_items.append({
                        "quote": text_el.get_text(strip=True) if text_el else "",
                        "author": author_el.get_text(strip=True) if author_el else "",
                        "tags": ",".join(tags),
                    })

                next_btn = soup.select_one("li.next > a")
                if not next_btn:
                    break
                next_href = next_btn.get("href")
                if not next_href:
                    break
                url = f"{BASE_URL}{next_href}"
                on_progress(page_num + 1, p.max_pages, f"Page {page_num+1}")
            except Exception as exc:
                errors.append(f"抓取失败 (page {page_num+1}): {exc}")
                break

        csv_path = work_dir / "quotes_beginner.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["quote", "author", "tags"])
            writer.writeheader()
            writer.writerows(all_items)

        return ToolResult(done=len(all_items), total=p.max_pages, errors=errors)


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(CrawlerBeginnerTool())
