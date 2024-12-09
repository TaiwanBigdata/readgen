import re
from pathlib import Path
from typing import Dict, Any, Optional
import tomllib


class ReadmeConfig:
    """處理 readgen.toml 設定檔案

    主要負責：
    1. 讀取與解析 readgen.toml
    2. 提供結構化的設定值
    3. 處理變數替換
    """

    SYSTEM_SECTION = "settings"
    VARIABLE_PATTERN = re.compile(r"\${([^}]+)}")

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.content_blocks: Dict[str, str] = {}
        self.settings = {"exclude_dirs": [], "depth_limits": {}}
        self.project_data: Dict[str, Any] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """載入所有設定檔"""
        self.project_data = self._read_project_file()
        self._load_readgen_config()

    def _read_project_file(self) -> Dict[str, Any]:
        """讀取 pyproject.toml"""
        project_path = self.root_path / "pyproject.toml"
        if project_path.exists():
            try:
                with open(project_path, "rb") as f:
                    return tomllib.load(f)
            except Exception as e:
                print(f"Error reading pyproject.toml: {e}")
        return {}

    def _get_variable_value(self, var_path: str) -> str:
        """從 project_data 取得變數值

        Args:
            var_path: 變數路徑，例如 "project.name" 或 "project.authors[0].name"
        """
        try:
            # 處理陣列索引
            parts = []
            for part in var_path.split("."):
                if "[" in part:
                    name, idx = part[:-1].split("[")
                    parts.extend([name, int(idx)])
                else:
                    parts.append(part)

            # 遞迴取值
            value = self.project_data
            for part in parts:
                if isinstance(part, int):
                    value = value[part]
                else:
                    value = value.get(part, "")
            return str(value)
        except Exception:
            return ""

    def _replace_variables(self, content: str) -> str:
        """替換內容中的變數"""

        def replace(match):
            var_path = match.group(1)
            return self._get_variable_value(var_path)

        return self.VARIABLE_PATTERN.sub(replace, content)

    def _load_readgen_config(self) -> None:
        """讀取並解析 readgen.toml"""
        config_path = self.root_path / "readgen.toml"
        if not config_path.exists():
            return

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # 處理系統設定
            if settings := config.pop(self.SYSTEM_SECTION, None):
                self.settings["exclude_dirs"] = settings.get("exclude_dirs", [])
                self.settings["depth_limits"] = {
                    k: v for k, v in settings.items() if k != "exclude_dirs"
                }

            # 處理內容區塊
            self.content_blocks = {}
            for section, data in config.items():
                if isinstance(data, dict):
                    # 如果區塊包含 title 和 content
                    block = {
                        "title": self._replace_variables(data.get("title", section)),
                        "content": self._replace_variables(data.get("content", "")),
                    }
                    self.content_blocks[section] = block
                else:
                    # 向後相容：直接使用字串內容
                    self.content_blocks[section] = self._replace_variables(data)
        except Exception as e:
            print(f"Error reading readgen.toml: {e}")
