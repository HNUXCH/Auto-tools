"""Auto-tools 统一平台入口。"""

from __future__ import annotations

import tkinter as tk

# 导入所有工具模块完成注册
import tools.image_rename       # noqa: F401
import tools.image_watermark    # noqa: F401
import tools.image_compress     # noqa: F401
import tools.pdf_merge          # noqa: F401
import tools.pdf_split          # noqa: F401
import tools.pdf_extract_text   # noqa: F401
import tools.pdf_rotate         # noqa: F401
import tools.pdf_to_word        # noqa: F401
import tools.word_to_pdf        # noqa: F401
import tools.crawler_beginner   # noqa: F401
import tools.crawler_intermediate  # noqa: F401

from ui.app import MainWindow


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
