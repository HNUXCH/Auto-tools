# Word 转 PDF（Windows 图形版）

可在 Windows 下直接用 PyCharm/其他编译器运行。

## 功能

- 选择单个或多个 `.docx` 文件批量转换为 PDF
- 弹窗选择输出目录
- 转换失败文件自动跳过，不影响其它文件

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

1. 打开并运行 `word_to_pdf/main.py`
2. 选择一个或多个 Word 文件（`.docx`）
3. 选择 PDF 输出文件夹
4. 等待弹窗提示结果

## 注意事项

- 依赖 `docx2pdf`，Windows 通常需要本机已安装 Microsoft Word
- 目前默认支持 `.docx`，不建议直接处理老格式 `.doc`
