# 中级爬虫（Windows 图形版）

演示站点：`books.toscrape.com`（爬虫练习站）

## 抓取字段

- `product_url`：书籍详情链接
- `title`：书名
- `price_gbp`：价格
- `rating`：评分等级
- `availability`：库存信息
- `upc`：产品编码
- `scraped_at`：抓取时间

## 中级特性

- 多页抓取 + 详情页抓取
- 并发抓取（线程池）
- 请求重试（失败自动重试）
- 去重（按链接去重）
- 增量入库（SQLite，已存在记录自动更新）
- 可选导出 CSV

## 运行

1. 安装依赖：`pip install -r requirements.txt`
2. 在 IDE 运行 `main.py`
3. 依次输入页数、线程数，选择 DB 路径和 CSV 路径
