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

    SYSTEM_SECTION = "settings"
    VARIABLE_PATTERN = re.compile(r"\${([^}]+)}")

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.content_blocks: Dict[str, str] = {}
        self.settings = {"exclude_dirs": [], "depth_limits": {}}
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
            # Handle array indices
            parts = []
            for part in var_path.split("."):
                if "[" in part:
                    name, idx = part[:-1].split("[")
                    parts.extend([name, int(idx)])
                else:
                    parts.append(part)

            # Recursive value retrieval
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
        """Replace variables in the content"""

        def replace(match):
            var_path = match.group(1)
            return self._get_variable_value(var_path)

        return self.VARIABLE_PATTERN.sub(replace, content)

    def _load_readgen_config(self) -> None:
        """Read and parse readgen.toml"""
        config_path = self.root_path / "readgen.toml"
        if not config_path.exists():
            return

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Handle system settings
            if settings := config.pop(self.SYSTEM_SECTION, None):
                self.settings["exclude_dirs"] = settings.get("exclude_dirs", [])
                self.settings["depth_limits"] = {
                    k: v for k, v in settings.items() if k != "exclude_dirs"
                }

            # Handle content blocks
            self.content_blocks = {}
            for section, data in config.items():
                if isinstance(data, dict):
                    # If the block contains title and content
                    block = {
                        "title": self._replace_variables(data.get("title", section)),
                        "content": self._replace_variables(data.get("content", "")),
                    }
                    self.content_blocks[section] = block
                else:
                    # Backward compatibility: directly use string content
                    self.content_blocks[section] = self._replace_variables(data)
        except Exception as e:
            print(f"Error reading readgen.toml: {e}")
