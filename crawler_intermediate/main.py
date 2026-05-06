from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import csv
import sqlite3
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"


@dataclass
class BookRow:
    product_url: str
    title: str
    price_gbp: str
    rating: str
    availability: str
    upc: str
    scraped_at: str


def fetch_with_retry(session: requests.Session, url: str, retries: int = 3, timeout: int = 15) -> str:
    last_err: Exception | None = None
    for i in range(retries):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # pragma: no cover
            last_err = exc
            if i < retries - 1:
                time.sleep(1.2 * (i + 1))
    raise RuntimeError(f"请求失败: {url}; 错误: {last_err}")


def parse_rating(classes: list[str]) -> str:
    for c in classes:
        if c != "star-rating":
            return c
    return ""


def list_book_links(session: requests.Session, max_pages: int) -> list[str]:
    links: list[str] = []
    page_url = urljoin(BASE_URL, "catalogue/page-1.html")
    for _ in range(max_pages):
        html = fetch_with_retry(session, page_url)
        soup = BeautifulSoup(html, "html.parser")
        for article in soup.select("article.product_pod h3 a"):
            href = article.get("href", "")
            full = urljoin(page_url, href)
            links.append(full)
        next_btn = soup.select_one("li.next > a")
        if not next_btn:
            break
        page_url = urljoin(page_url, next_btn.get("href", ""))
    return links


def parse_book_detail(session: requests.Session, url: str) -> BookRow:
    html = fetch_with_retry(session, url)
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1")
    price = soup.select_one("div.product_main p.price_color")
    rating_el = soup.select_one("div.product_main p.star-rating")
    availability = soup.select_one("div.product_main p.instock.availability")

    upc = ""
    for row in soup.select("table.table.table-striped tr"):
        key = row.select_one("th")
        val = row.select_one("td")
        if key and val and key.get_text(strip=True) == "UPC":
            upc = val.get_text(strip=True)
            break

    return BookRow(
        product_url=url,
        title=title.get_text(strip=True) if title else "",
        price_gbp=price.get_text(strip=True) if price else "",
        rating=parse_rating(rating_el.get("class", [])) if rating_el else "",
        availability=availability.get_text(" ", strip=True) if availability else "",
        upc=upc,
        scraped_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            product_url TEXT PRIMARY KEY,
            title TEXT,
            price_gbp TEXT,
            rating TEXT,
            availability TEXT,
            upc TEXT,
            scraped_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def upsert_books(conn: sqlite3.Connection, rows: list[BookRow]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for row in rows:
        cur = conn.execute("SELECT product_url FROM books WHERE product_url = ?", (row.product_url,))
        exists = cur.fetchone() is not None
        conn.execute(
            """
            INSERT INTO books (product_url, title, price_gbp, rating, availability, upc, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_url) DO UPDATE SET
                title=excluded.title,
                price_gbp=excluded.price_gbp,
                rating=excluded.rating,
                availability=excluded.availability,
                upc=excluded.upc,
                scraped_at=excluded.scraped_at
            """,
            (
                row.product_url,
                row.title,
                row.price_gbp,
                row.rating,
                row.availability,
                row.upc,
                row.scraped_at,
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1
    conn.commit()
    return inserted, updated


def export_csv(rows: list[BookRow], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["product_url", "title", "price_gbp", "rating", "availability", "upc", "scraped_at"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def run_crawl(max_pages: int, workers: int) -> list[BookRow]:
    session = requests.Session()
    links = list_book_links(session, max_pages=max_pages)

    # Deduplicate links to avoid repeated processing.
    unique_links = sorted(set(links))
    rows: list[BookRow] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(parse_book_detail, session, url) for url in unique_links]
        for fut in as_completed(futures):
            rows.append(fut.result())
    return rows


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    pages = simpledialog.askinteger("中级爬虫", "抓取页数（建议 1-20）", parent=root, initialvalue=5, minvalue=1, maxvalue=100)
    if pages is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    workers = simpledialog.askinteger("并发线程数", "输入并发线程数（建议 4-10）", parent=root, initialvalue=6, minvalue=1, maxvalue=20)
    if workers is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    db_path_str = filedialog.asksaveasfilename(
        parent=root,
        title="选择 SQLite 数据库文件",
        defaultextension=".db",
        initialfile="books_intermediate.db",
        filetypes=[("SQLite DB", "*.db")],
    )
    if not db_path_str:
        messagebox.showinfo("已取消", "未选择数据库文件。", parent=root)
        return

    csv_path_str = filedialog.asksaveasfilename(
        parent=root,
        title="选择导出 CSV 路径（可取消）",
        defaultextension=".csv",
        initialfile="books_intermediate.csv",
        filetypes=[("CSV files", "*.csv")],
    )

    try:
        rows = run_crawl(max_pages=pages, workers=workers)
        conn = ensure_db(Path(db_path_str))
        try:
            inserted, updated = upsert_books(conn, rows)
        finally:
            conn.close()

        if csv_path_str:
            export_csv(rows, Path(csv_path_str))
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("失败", f"抓取失败：{exc}", parent=root)
        return

    messagebox.showinfo(
        "完成",
        f"本次抓取：{len(rows)} 条\n新增：{inserted} 条\n更新：{updated} 条\n数据库：{db_path_str}",
        parent=root,
    )


if __name__ == "__main__":
    main()
