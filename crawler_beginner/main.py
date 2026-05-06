from __future__ import annotations

from pathlib import Path
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://quotes.toscrape.com"


def fetch_page(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_quotes(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    for quote in soup.select("div.quote"):
        text_el = quote.select_one("span.text")
        author_el = quote.select_one("small.author")
        tags = [t.get_text(strip=True) for t in quote.select("div.tags a.tag")]
        items.append(
            {
                "quote": text_el.get_text(strip=True) if text_el else "",
                "author": author_el.get_text(strip=True) if author_el else "",
                "tags": ",".join(tags),
            }
        )
    return items


def crawl_quotes(max_pages: int) -> list[dict[str, str]]:
    all_items: list[dict[str, str]] = []
    url = BASE_URL
    for _ in range(max_pages):
        html = fetch_page(url)
        all_items.extend(parse_quotes(html))
        soup = BeautifulSoup(html, "html.parser")
        next_btn = soup.select_one("li.next > a")
        if not next_btn:
            break
        next_href = next_btn.get("href")
        if not next_href:
            break
        url = f"{BASE_URL}{next_href}"
    return all_items


def save_csv(rows: list[dict[str, str]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["quote", "author", "tags"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update()

    pages = simpledialog.askinteger("入门爬虫", "抓取页数（建议 1-10）", parent=root, initialvalue=3, minvalue=1, maxvalue=50)
    if pages is None:
        messagebox.showinfo("已取消", "操作已取消。", parent=root)
        return

    output_path = filedialog.asksaveasfilename(
        parent=root,
        title="保存 CSV",
        defaultextension=".csv",
        initialfile="quotes_beginner.csv",
        filetypes=[("CSV files", "*.csv")],
    )
    if not output_path:
        messagebox.showinfo("已取消", "未选择输出路径。", parent=root)
        return

    try:
        rows = crawl_quotes(pages)
        save_csv(rows, Path(output_path))
    except Exception as exc:  # pragma: no cover
        messagebox.showerror("失败", f"抓取失败：{exc}", parent=root)
        return

    messagebox.showinfo("完成", f"抓取完成：{len(rows)} 条\n输出：{output_path}", parent=root)


if __name__ == "__main__":
    main()
