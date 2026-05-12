# Auto-tools

统一的 Python GUI 自动化工具平台，面向 Windows。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 功能

### 图片工具（支持流水线串联）

| 工具 | 功能 |
|---|---|
| 批量重命名 | 按前缀/编号/后缀批量重命名 |
| 文字水印 | 批量添加文字水印（单点或满铺斜向，位置/透明度/角度可调） |
| 批量压缩 | 批量压缩/缩放（JPEG 质量、最大宽高） |

### PDF 工具

| 工具 | 功能 |
|---|---|
| PDF 合并 | 合并多个 PDF |
| PDF 拆分 | 按页拆分 PDF |
| 提取 PDF 文本 | 提取 PDF 文本到 TXT |
| PDF 旋转 | 旋转 PDF 页面（90/180/270 度） |
| PDF → Word | 批量 PDF 转 DOCX |
| Word → PDF | 批量 DOCX 转 PDF（需本机安装 Word） |

### 网页工具

| 工具 | 功能 |
|---|---|
| 入门爬虫 | 抓取 quotes.toscrape.com → CSV |
| 中级爬虫 | 抓取 books.toscrape.com → SQLite + CSV |
| CSP 真题爬虫 | 抓取 CCF CSP 认证 108 道历年真题（2013-2026）→ Markdown + CSV |
| 在线判题 | 启动本地 OJ 服务器，力扣风格在线写代码、自动判题，支持 86 道真题的样例测试 |

## 流水线

图片工具可自由组合为流水线（重命名 → 水印 → 压缩），保存为预设一键复用。

## 在线判题

内置类力扣（LeetCode）的浏览器编程环境：

1. 打开 Auto-tools → 网页标签 → CSP 真题爬虫 → 选择输出目录 → 下载 108 道 CSP 真题
2. 网页标签 → 在线判题 → 选择下载的 `problems/` 目录 → 自动打开浏览器
3. 左侧题目描述（Markdown 渲染），右侧 CodeMirror 代码编辑器
4. 写 Python 代码 → 点击运行 → 自动用真题样例判题（通过/错误/超时）

```bash
# 判题服务器默认监听 127.0.0.1 随机端口，浏览器自动打开
# 支持: subprocess 执行 Python 代码，5 秒超时，stdin/stdout 比对
```

## 特点

- 原图零修改（临时目录隔离）
- 中途取消
- 自动检测中文字体
- 参数表单自动生成
- 流水线预设保存/加载
- CSP 真题爬虫 + 在线判题一站式
