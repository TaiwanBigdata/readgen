import os
import sys
import argparse
from pathlib import Path
from typing import Optional
from readgen.generator import ReadmeGenerator


def main() -> Optional[int]:
    """CLI 主程式入口

    Returns:
        Optional[int]: 執行狀態碼，0 表示成功，1 表示失敗
    """
    parser = argparse.ArgumentParser(
        description="在當前目錄產生 README.md 檔案", epilog="Example: readgen"
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="若 README.md 已存在則強制覆寫"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="README.md",
        help="指定輸出檔案名稱（預設：README.md）",
    )

    args = parser.parse_args()

    try:
        # 檢查輸出檔案是否已存在
        output_path = Path(args.output)
        if output_path.exists() and not args.force:
            print(f"錯誤：{args.output} 已存在。使用 --force 參數來覆寫現有檔案。")
            return 1

        # 建立產生器實例
        generator = ReadmeGenerator()

        # 產生 README 內容
        readme_content = generator.generate()

        # 寫入檔案
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        print(f"✨ 成功產生 {args.output}！")
        return 0

    except Exception as e:
        print(f"錯誤：{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
