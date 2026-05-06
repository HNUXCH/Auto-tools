# Auto-tools

一组独立的 Python GUI 自动化工具，面向 Windows 平台。

## 模块

| 模块 | 功能 |
|---|---|
| `crawler_beginner` | 抓取 quotes.toscrape.com → CSV |
| `crawler_intermediate` | 抓取 books.toscrape.com → SQLite + CSV，支持并发、重试、增量入库 |
| `image_compress` | 批量压缩/缩放图片 |
| `image_renamer` | 按前缀/编号/后缀批量重命名图片 |
| `image_watermark` | 批量添加文字水印 |
| `image_workflow` | 组合 GUI 工作流：重命名 → 水印 → 压缩（不修改原图） |
| `pdf_tools` | PDF 合并、拆分、提取文本、旋转 |
| `pdf_to_word` | 批量 PDF → DOCX |
| `word_to_pdf` | 批量 DOCX → PDF（需本机安装 Word） |

## 运行

```bash
pip install -r <模块名>/requirements.txt
python <模块名>/main.py
```
