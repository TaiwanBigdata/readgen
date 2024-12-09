from pathlib import Path
from typing import Dict, List, Optional, Any
import re
import os
from readgen.utils import paths
from readgen.config import ReadmeConfig


class ReadmeGenerator:
    """README 生成器"""

    def __init__(self):
        self.root_dir = paths.ROOT_PATH
        self.config = ReadmeConfig(self.root_dir)
        self.doc_pattern = re.compile(r'"""(.*?)"""', re.DOTALL)

    def _get_env_vars(self) -> List[Dict[str, str]]:
        """從 .env.example 取得環境變數說明"""
        env_vars = []
        env_path = self.root_dir / ".env.example"
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            key = line.split("=")[0].strip()
                            comment = ""
                            if "#" in line:
                                comment = line.split("#")[1].strip()
                            env_vars.append({"key": key, "description": comment})
            except Exception as e:
                print(f"Error reading .env.example: {e}")
        return env_vars

    def _extract_docstring(self, content: str) -> Optional[str]:
        """從 __init__.py 內容中提取 docstring"""
        matches = self.doc_pattern.findall(content)
        if matches:
            return matches[0].strip()
        return None

    def _read_init_file(self, file_path: Path) -> Optional[Dict]:
        """讀取並解析 __init__.py 檔案"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                docstring = self._extract_docstring(content)
                if docstring:
                    rel_path = str(file_path.parent.relative_to(self.root_dir))
                    return {"path": rel_path, "doc": docstring}
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        return None

    def _find_init_files(self) -> List[Dict]:
        """尋找所有 __init__.py 檔案並提取文件"""
        try:
            init_files = []
            exclude_dirs = self.config.settings["exclude_dirs"]
            depth_limits = self.config.settings["depth_limits"]

            for root, dirs, files in os.walk(self.root_dir):
                root_path = Path(root)

                # 檢查排除目錄
                should_skip = any(
                    part.startswith(".") or part in exclude_dirs
                    for part in root_path.parts
                )

                if should_skip:
                    continue

                # 檢查深度限制
                if root_path != self.root_dir:
                    rel_path = str(root_path.relative_to(self.root_dir)).replace(
                        "\\", "/"
                    )

                    # 檢查深度限制
                    for pattern, depth in depth_limits.items():
                        if rel_path.startswith(pattern):
                            remaining_path = rel_path[len(pattern) :].strip("/")
                            current_depth = (
                                len(remaining_path.split("/")) if remaining_path else 0
                            )
                            if current_depth > depth:
                                should_skip = True
                                break

                    if should_skip:
                        continue

                    init_files.append({"path": rel_path, "doc": ""})

                if "__init__.py" in files:
                    file_path = root_path / "__init__.py"
                    if doc_info := self._read_init_file(file_path):
                        for item in init_files:
                            if item["path"] == doc_info["path"]:
                                item["doc"] = doc_info["doc"]
                                break

            return sorted(init_files, key=lambda x: x["path"])
        except Exception as e:
            print(f"Error in _find_init_files: {e}")
            return []

    def _generate_toc(self, docs: List[Dict]) -> str:
        """產生目錄結構與模組說明"""
        if not docs:
            return "## 目錄結構與模組說明\n\n*尚無目錄資訊*"

        sections = ["# Directory Structure", ""]
        project_name = self.root_dir.name  # 取得根目錄名稱
        sections.append(f"* **{project_name}**")  # 將根目錄名稱作為第一層

        for doc in docs:
            path = doc["path"].replace("\\", "/")
            indent = "  " * (path.count("/") + 1)  # 增加一層縮排，作為子項目

            if doc["doc"]:
                doc_text = doc["doc"].split("\n")[0].strip()
                sections.append(f"{indent}* **{path}**：{doc_text}")
            else:
                sections.append(f"{indent}* **{path}**")

        return "\n".join(sections)

    def generate(self) -> str:
        """產生完整的 README 內容"""
        try:
            sections = []

            # 處理所有內容區塊，全部使用 h1 標題
            for section, block in self.config.content_blocks.items():
                # 取得區塊內容，可能是字串或字典
                if isinstance(block, dict):
                    title = block.get("title", section)  # 如果有 title 就用 title
                    content = block.get("content", "")  # 取得內容
                else:
                    title = section
                    content = block

                sections.extend(
                    [f"# {title}", "", content, ""]  # 使用自定義標題或區塊名
                )

            # 處理環境變數
            env_vars = self._get_env_vars()
            if env_vars:
                sections.extend(
                    [
                        "# Environment Variables",
                        "",
                        "| 變數名稱 | 說明 |",
                        "| --- | --- |",
                        *[
                            f"| {var['key']} | {var['description']} |"
                            for var in env_vars
                        ],
                        "",
                    ]
                )

            # 產生目錄結構（總是在最後）
            docs = self._find_init_files()
            if docs:
                toc_content = self._generate_toc(docs)
                # 移除原本的 ## 標題，改為使用 # 標題
                toc_content = toc_content.replace(
                    "## 目錄結構與模組說明", "# Directory Structure"
                )
                sections.extend([toc_content, ""])

            # 加入頁尾
            sections.extend(
                ["---", "> This document was automatically generated by readgen."]
            )

            return "\n".join(filter(None, sections))

        except Exception as e:
            print(f"Error generating README: {e}")
            return "無法產生 README 內容。請檢查錯誤訊息。"


def main():
    try:
        generator = ReadmeGenerator()
        new_readme = generator.generate()

        readme_path = paths.ROOT_PATH / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_readme)

        print("README.md has been generated successfully!")
    except Exception as e:
        print(f"Failed to generate README.md: {e}")
