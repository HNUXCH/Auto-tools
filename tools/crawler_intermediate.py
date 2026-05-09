"""中级爬虫 Tool — 抓取 books.toscrape.com → CSV + SQLite（独立运行）。"""

from __future__ import annotations

import csv
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import threading
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core.tool_base import InputMode, ProgressCallback, Tool, ToolParams, ToolResult

BASE_URL = "https://books.toscrape.com/"


@dataclass
class CrawlerIntermediateParams(ToolParams):
    max_pages: int = 5
    workers: int = 6


class CrawlerIntermediateTool(Tool):
    name = "中级爬虫"
    name_slug = "crawler_intermediate"
    icon = "🕸️"
    category = "web"
    input_mode = InputMode.NONE

    def params_type(self) -> type[ToolParams]:
        return CrawlerIntermediateParams

    def validate_params(self, params: ToolParams) -> list[str]:
        p: CrawlerIntermediateParams = params
        errs: list[str] = []
        if p.max_pages < 1:
            errs.append("页数至少为 1")
        if p.workers < 1:
            errs.append("并发线程至少为 1")
        return errs

    def run(
        self,
        work_dir: Path,
        params: ToolParams,
        on_progress: ProgressCallback,
        cancel_event: threading.Event,
    ) -> ToolResult:
        p: CrawlerIntermediateParams = params
        session = requests.Session()

        links: list[str] = []
        page_url = urljoin(BASE_URL, "catalogue/page-1.html")
        for pg in range(p.max_pages):
            if cancel_event.is_set():
                break
            try:
                html = self._fetch_with_retry(session, page_url)
                soup = BeautifulSoup(html, "html.parser")
                for article in soup.select("article.product_pod h3 a"):
                    href = article.get("href", "")
                    links.append(urljoin(page_url, href))
                next_btn = soup.select_one("li.next > a")
                if not next_btn:
                    break
                page_url = urljoin(page_url, next_btn.get("href", ""))
            except Exception as exc:
                return ToolResult(done=pg, total=p.max_pages, errors=[str(exc)])

        if not links:
            return ToolResult(done=0, total=0, errors=["未找到书籍链接"])

        links = sorted(set(links))
        rows: list[dict] = []

        with ThreadPoolExecutor(max_workers=p.workers) as pool:
            futures = [pool.submit(self._parse_detail, session, url) for url in links]
            for i, fut in enumerate(as_completed(futures)):
                if cancel_event.is_set():
                    break
                try:
                    rows.append(fut.result())
                except Exception:
                    pass
                on_progress(i + 1, len(links), f"详情 {i+1}/{len(links)}")

        db_path = work_dir / "books_intermediate.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                product_url TEXT PRIMARY KEY, title TEXT, price_gbp TEXT,
                rating TEXT, availability TEXT, upc TEXT, scraped_at TEXT
            )
        """)
        for row in rows:
            conn.execute(
                """INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(product_url) DO UPDATE SET
                   title=excluded.title, price_gbp=excluded.price_gbp,
                   rating=excluded.rating, availability=excluded.availability,
                   upc=excluded.upc, scraped_at=excluded.scraped_at""",
                (row["product_url"], row["title"], row["price_gbp"],
                 row["rating"], row["availability"], row["upc"], row["scraped_at"]),
            )
        conn.commit()
        conn.close()

        csv_path = work_dir / "books_intermediate.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "product_url", "title", "price_gbp", "rating", "availability", "upc", "scraped_at",
            ])
            writer.writeheader()
            writer.writerows(rows)

        return ToolResult(done=len(rows), total=len(links))

    @staticmethod
    def _fetch_with_retry(session: requests.Session, url: str, retries: int = 3) -> str:
        for i in range(retries):
            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
                return resp.text
            except Exception:
                if i < retries - 1:
                    time.sleep(1.2 * (i + 1))
        raise RuntimeError(f"请求失败: {url}")

    @staticmethod
    def _parse_detail(session: requests.Session, url: str) -> dict:
        html = CrawlerIntermediateTool._fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.select_one("div.product_main h1")
        price = soup.select_one("div.product_main p.price_color")
        rating_el = soup.select_one("div.product_main p.star-rating")
        availability = soup.select_one("div.product_main p.instock.availability")
        upc = ""
        for row in soup.select("table.table.table-striped tr"):
            key, val = row.select_one("th"), row.select_one("td")
            if key and val and key.get_text(strip=True) == "UPC":
                upc = val.get_text(strip=True)
                break
        return {
            "product_url": url,
            "title": title.get_text(strip=True) if title else "",
            "price_gbp": price.get_text(strip=True) if price else "",
            "rating": CrawlerIntermediateTool._parse_rating(rating_el.get("class", [])) if rating_el else "",
            "availability": availability.get_text(" ", strip=True) if availability else "",
            "upc": upc,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _parse_rating(classes: list[str]) -> str:
        for c in classes:
            if c != "star-rating":
                return c
        return ""


from core.registry import ToolRegistry  # noqa: E402
ToolRegistry.register(CrawlerIntermediateTool())
