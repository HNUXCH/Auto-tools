# PDF 转 Word（Windows 图形版）

可在 Windows 下直接用 PyCharm/其他编译器运行。

## 功能

- 选择单个或多个 PDF 批量转换为 Word（`.docx`）
- 弹窗选择输出目录
- 转换失败文件自动跳过，不影响其它文件

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

1. 打开并运行 `pdf_to_word/main.py`
2. 选择一个或多个 PDF 文件
3. 选择 Word 输出文件夹
4. 等待弹窗提示结果

## 说明

- 对“文字型 PDF”效果更好
- 对“扫描件 PDF”（图片型）通常需要 OCR 才能得到可编辑文字
