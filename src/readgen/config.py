import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
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
        self.block_order: List[str] = []
        self.directory = {
            "title": "Directory Structure",
            "content": "",
            "enable": True,
            "exclude_patterns": set(),
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
        """Read pyproject.toml with support for PEP 621 and setuptools>=61.0.0"""
        project_path = self.root_path / "pyproject.toml"
        if project_path.exists():
            try:
                with open(project_path, "rb") as f:
                    data = tomllib.load(f)

                # Handle dynamic fields if present
                project_data = data.get("project", {})
                if "dynamic" in project_data:
                    dynamic_fields = project_data["dynamic"]
                    # For now we just acknowledge dynamic fields exist
                    # Future: implement dynamic field resolution

                # Handle dependencies
                if "dependencies" in project_data:
                    # Convert dependencies to a more readable format for README
                    deps = project_data["dependencies"]
                    if isinstance(deps, list):
                        project_data["formatted_dependencies"] = "\n".join(
                            f"- {dep}" for dep in deps
                        )

                # Handle optional dependencies
                if "optional-dependencies" in project_data:
                    opt_deps = project_data["optional-dependencies"]
                    if isinstance(opt_deps, dict):
                        formatted_opt_deps = {}
                        for env, deps in opt_deps.items():
                            formatted_opt_deps[env] = "\n".join(
                                f"- {dep}" for dep in deps
                            )
                        project_data["formatted_optional_dependencies"] = (
                            formatted_opt_deps
                        )

                return data
            except Exception as e:
                print(f"Error reading pyproject.toml: {e}")
        return {}

    def _format_author(self, author: Dict[str, str]) -> str:
        """Format author information with optional email

        Args:
            author: Author dictionary with name and optional email
        """
        if not isinstance(author, dict) or "name" not in author:
            return str(author)

        parts = [author["name"]]
        if email := author.get("email"):
            parts.append(f"({email})")
        return " ".join(parts)

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

            # Format different value types
            if isinstance(value, dict):
                # Handle special cases
                if "text" in value:  # For license and similar fields
                    return value["text"]
                if "name" in value:  # For single author and similar fields
                    return self._format_author(value)
                return ", ".join(f"{k}: {v}" for k, v in value.items())
            elif isinstance(value, list):
                # Format list as bullet points
                if all(isinstance(item, str) for item in value):
                    # Simple string list
                    return "\n- " + "\n- ".join(value)
                elif all(isinstance(item, dict) for item in value):
                    # List of dictionaries (e.g., authors)
                    formatted_items = []
                    for item in value:
                        if "name" in item:  # Author information
                            formatted_items.append(self._format_author(item))
                        else:
                            formatted_items.append(
                                ", ".join(f"{k}: {v}" for k, v in item.items())
                            )
                    return "\n- " + "\n- ".join(formatted_items)
                return ", ".join(str(item) for item in value)
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

            self.block_order = list(config.keys())

            # Handle directory settings
            if directory_config := config.pop("directory", None):
                self.directory.update(directory_config)

                # Handle exclude patterns
                if "exclude_patterns" in directory_config:
                    self.directory["exclude_patterns"] = set(
                        directory_config["exclude_patterns"]
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
