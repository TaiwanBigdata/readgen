import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from utils import paths


class ReadmeGenerator:
    def __init__(self):
        self.root_dir = paths.ROOT_PATH
        self.doc_pattern = re.compile(r'"""(.*?)"""', re.DOTALL)

    def _read_project_file(self) -> Dict[str, Any]:
        """從 project.yaml 讀取專案資訊

        Returns:
            Dict[str, Any]: 專案配置內容
        """
        project_path = self.root_dir / "project.yaml"
        if project_path.exists():
            try:
                with open(project_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error reading project.yaml: {e}")
        return {}

    def _format_value(self, value: Any, indent_level: int = 0) -> List[str]:
        """格式化值為 Markdown 格式的列表

        Args:
            value: 要格式化的值
            indent_level: 目前的縮排層級

        Returns:
            List[str]: 格式化後的字串列表
        """
        indent = "  " * indent_level
        result = []

        if value is None:
            return []

        # 處理基本類型
        if isinstance(value, (int, float, bool)):
            return [f"{indent}* {value}"]

        if isinstance(value, str):
            return [f"{indent}* {value}"]

        # 處理字典：檢查是否為 name/email 格式
        if isinstance(value, dict):
            if "name" in value and len(value) <= 2:  # name/email 格式
                name = value.get("name", "")
                email = value.get("email", "")
                formatted = name
                if email:
                    formatted += f" ({email})"
                return [f"{indent}* {formatted}"]

            # 一般字典處理
            for key, val in value.items():
                display_key = key.replace("_", " ").title()

                if isinstance(val, (str, int, float, bool)):
                    result.append(f"{indent}* **{display_key}**：{val}")
                else:
                    result.append(f"{indent}* **{display_key}**：")
                    result.extend(self._format_value(val, indent_level + 1))
            return result

        # 處理列表
        if isinstance(value, (list, tuple)):
            for item in value:
                result.extend(self._format_value(item, indent_level))
            return result

        return [f"{indent}* {str(value)}"]

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
            # 基本排除目錄
            exclude_dirs = {".git", "venv", "__pycache__", ".venv", "env"}

            # 顯示到第幾層的配置 (path/to/dir 形式)
            show_until_patterns = {
                "app/web/bootstrap": 0,
                "app/web/static": 0,
                "backups": 0,
                "caches": 0,
                "secrets": 0,
            }

            for root, dirs, files in os.walk(self.root_dir):
                root_path = Path(root)

                # 檢查基本排除目錄
                should_skip = any(
                    part.startswith(".") or part in exclude_dirs
                    for part in root_path.parts
                )

                if should_skip:
                    continue

                # 檢查是否超過顯示深度
                if root_path != self.root_dir:
                    rel_path = str(root_path.relative_to(self.root_dir)).replace(
                        "\\", "/"
                    )

                    # 檢查是否需要跳過這個路徑
                    for pattern, depth in show_until_patterns.items():
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

                    # 加入目錄結構
                    init_files.append({"path": rel_path, "doc": ""})

                # 如果有 __init__.py，讀取其文檔
                if "__init__.py" in files:
                    file_path = root_path / "__init__.py"
                    if doc_info := self._read_init_file(file_path):
                        # 更新現有的目錄文檔
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

        sections = ["## 目錄結構與模組說明", ""]

        for doc in docs:
            path = doc["path"].replace("\\", "/")
            indent = path.count("/") * "  "

            if doc["doc"]:
                doc_text = doc["doc"].split("\n")[0].strip()
                sections.append(f"{indent}* **{path}**：{doc_text}")
            else:
                sections.append(f"{indent}* **{path}**")

            sections.append("")

        return "\n".join(sections)

    def generate(self) -> str:
        """產生完整的 README 內容"""
        try:
            # 讀取專案設定
            project_data = self._read_project_file()

            sections = []

            # 處理專案資訊
            if project_data:
                for section_name, section_content in project_data.items():
                    # 如果是 project 區段，特別處理
                    if section_name == "project":
                        if name := section_content.get("name"):
                            sections.extend([f"# {name}", ""])
                        if description := section_content.get("description"):
                            sections.extend([description, "", ""])

                    # 將區段名稱轉換為標題
                    title = section_name.replace("_", " ").title()
                    sections.append(f"## {title}")
                    sections.extend(self._format_value(section_content))
                    sections.append("")  # 加入空行

            # 處理環境變數
            env_vars = self._get_env_vars()
            if env_vars:
                sections.extend(
                    [
                        "## 環境變數",
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

            # 處理目錄結構
            docs = self._find_init_files() or []
            sections.extend([self._generate_toc(docs), ""])

            # 加入頁尾
            sections.extend(["---", "> 本文件由 update_readme.py 自動產生"])

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


if __name__ == "__main__":
    main()
