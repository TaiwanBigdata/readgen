import re
from pathlib import Path
from typing import Dict, Any, Optional
import tomllib


class ReadmeConfig:
    """Handles the readgen.toml configuration file

    Responsibilities:
    1. Read and parse readgen.toml
    2. Provide structured configuration values
    3. Handle variable substitution
    """

    VARIABLE_PATTERN = re.compile(r"\${([^}]+)}")

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.content_blocks: Dict[str, str] = {}
        self.directory = {
            "title": "Directory Structure",
            "content": "",
            "enable": True,
            "exclude_dirs": set(),
            "exclude_files": set(),
            "max_depth": None,
            "show_files": True,
            "show_comments": True,
        }
        self.env = {
            "title": "Environment Variables",
            "content": "",
            "enable": True,
            "env_file": ".env",
        }
        self.project_data: Dict[str, Any] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load all configuration files"""
        self.project_data = self._read_project_file()
        self._load_readgen_config()

    def _read_project_file(self) -> Dict[str, Any]:
        """Read pyproject.toml"""
        project_path = self.root_path / "pyproject.toml"
        if project_path.exists():
            try:
                with open(project_path, "rb") as f:
                    return tomllib.load(f)
            except Exception as e:
                print(f"Error reading pyproject.toml: {e}")
        return {}

    def _get_variable_value(self, var_path: str) -> str:
        """Retrieve variable value from project_data

        Args:
            var_path: The variable path, e.g., "project.name" or "project.authors[0].name"
        """
        try:
            parts = []
            for part in var_path.split("."):
                if "[" in part:
                    name, idx = part[:-1].split("[")
                    parts.extend([name, int(idx)])
                else:
                    parts.append(part)

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
        """Replace variables but preserve escaped variables"""

        def replace(match):
            start = match.start()
            if start > 0 and content[start - 1] == "\\":
                return match.group(0)
            return self._get_variable_value(match.group(1))

        result = self.VARIABLE_PATTERN.sub(replace, content)
        return result.replace("\\${", "${")

    def _load_readgen_config(self) -> None:
        """Read and parse readgen.toml"""
        config_path = self.root_path / "readgen.toml"
        if not config_path.exists():
            return

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Handle directory settings
            if directory_config := config.pop("directory", None):
                self.directory.update(directory_config)
                self.directory["exclude_dirs"] = set(
                    directory_config.get("exclude_dirs", [])
                )
                self.directory["exclude_files"] = set(
                    directory_config.get("exclude_files", [])
                )

            # Handle env settings
            if env_config := config.pop("env", None):
                self.env.update(env_config)

            # Handle content blocks
            self.content_blocks = {}
            for section, data in config.items():
                if isinstance(data, dict):
                    block = {
                        "title": self._replace_variables(data.get("title", section)),
                        "content": self._replace_variables(data.get("content", "")),
                    }
                    self.content_blocks[section] = block
                else:
                    self.content_blocks[section] = self._replace_variables(data)
        except Exception as e:
            print(f"Error reading readgen.toml: {e}")
