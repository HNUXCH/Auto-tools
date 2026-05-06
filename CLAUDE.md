# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概览

一组独立的 Python GUI 自动化工具，面向 Windows 平台。每个工具位于独立目录，入口均为 `main.py`。所有工具使用 `tkinter` 实现文件对话框和简单输入提示。模块之间互不共享代码，各自完全独立。

## 运行方式

每个模块在其自身目录下运行。先安装依赖，再运行脚本：

```bash
# 安装指定工具的依赖
pip install -r <模块名>/requirements.txt

# 运行（使用 tkinter GUI，无命令行参数）
python <模块名>/main.py
```

本项目无顶层包或构建系统，也没有测试。

## 模块一览

| 目录 | 依赖 | 功能 |
|---|---|---|
| `crawler_beginner` | `requests`, `beautifulsoup4` | 抓取 quotes.toscrape.com → CSV |
| `crawler_intermediate` | `requests`, `beautifulsoup4` | 抓取 books.toscrape.com → SQLite + CSV，支持线程池并发、重试、upsert 增量入库 |
| `image_compress` | `Pillow` | 批量压缩/缩放图片 |
| `image_renamer` | （仅标准库） | 按前缀/编号/后缀批量重命名图片 |
| `image_watermark` | `Pillow` | 批量添加文字水印 |
| `image_workflow` | `Pillow` | 组合 GUI 工作流：重命名 → 水印 → 压缩（后台线程异步执行，使用临时目录，原图不被修改） |
| `pdf_tools` | `pypdf` | PDF 合并、拆分、提取文本、旋转 |
| `pdf_to_word` | `pdf2docx` | 批量 PDF → DOCX |
| `word_to_pdf` | `docx2pdf` | 批量 DOCX → PDF（需本机安装 Microsoft Word） |

仓库根目录的 `spiral_matrix.py` 是一个独立的算法练习（生成 n×n 螺旋矩阵）。

## 编码约定

- Python 3.10+，使用 `from __future__ import annotations`
- 多数模块使用 `tkinter.Tk().withdraw()` 实现仅弹窗模式；`image_workflow` 和 `pdf_tools` 使用完整 GUI 窗口
- 输出目录通过 `Path.mkdir(parents=True, exist_ok=True)` 创建
- CSV 输出使用 `utf-8-sig` 编码（便于 Windows Excel 打开）
- 所有用户界面文字均为中文
