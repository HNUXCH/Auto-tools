# Auto-tools

统一的 Python GUI 自动化工具平台，面向 Windows。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 功能

### 📷 图片工具（支持流水线串联）

| 工具 | 功能 |
|---|---|
| 批量重命名 | 按前缀/编号/后缀批量重命名 |
| 文字水印 | 批量添加文字水印（位置、透明度可调） |
| 批量压缩 | 批量压缩/缩放（JPEG 质量、最大宽高） |

### 📄 PDF 工具

| 工具 | 功能 |
|---|---|
| PDF 合并 | 合并多个 PDF |
| PDF 拆分 | 按页拆分 PDF |
| 提取 PDF 文本 | 提取 PDF 文本到 TXT |
| PDF 旋转 | 旋转 PDF 页面（90/180/270 度） |
| PDF → Word | 批量 PDF 转 DOCX |
| Word → PDF | 批量 DOCX 转 PDF（需本机安装 Word） |

### 🌐 网页工具

| 工具 | 功能 |
|---|---|
| 入门爬虫 | 抓取 quotes.toscrape.com → CSV |
| 中级爬虫 | 抓取 books.toscrape.com → SQLite + CSV |

## 流水线

图片工具可自由组合为流水线（重命名 → 水印 → 压缩），保存为预设一键复用。

## 特点

- 🛡️ 原图零修改（临时目录隔离）
- 🚫 中途取消
- 🔤 自动检测中文字体
- 📋 参数表单自动生成
- 💾 流水线预设保存/加载
