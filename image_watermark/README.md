# 图片批量水印工具（Windows 图形版）

在 Windows 下可直接在 PyCharm/其他编译器运行。

## 功能

- 批量给图片添加文字水印
- 支持位置：`top-left` / `top-right` / `bottom-left` / `bottom-right` / `center`
- 可设置字体大小、透明度
- 输出到新文件夹，不覆盖原图

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

1. 打开 `image_watermark/main.py`
2. 直接运行脚本
3. 按弹窗步骤操作：
   - 选择输入图片文件夹
   - 选择输出文件夹
   - 输入水印文字
   - 输入位置
   - 输入字体大小
   - 输入透明度

## 支持格式

`.jpg` `.jpeg` `.png` `.bmp` `.webp` `.tif` `.tiff`
