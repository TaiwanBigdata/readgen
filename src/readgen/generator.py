from pathlib import Path
from typing import Dict, List, Optional, Any
import re
import os
from readgen.utils import paths
from readgen.config import ReadmeConfig


class ReadmeGenerator:
    """README Generator"""

    def __init__(self):
        self.root_dir = paths.ROOT_PATH
        self.config = ReadmeConfig(self.root_dir)
        self.doc_pattern = re.compile(r'"""(.*?)"""', re.DOTALL)

    def _get_env_vars(self) -> List[Dict[str, str]]:
        """Retrieve environment variable descriptions from .env.example"""
        env_vars = []
        env_path = self.root_dir / self.config.env["env_file"]
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
                print(f"Error reading .env: {e}")
        return env_vars

    def _extract_docstring(self, content: str) -> Optional[str]:
        """Extract docstring from __init__.py content"""
        matches = self.doc_pattern.findall(content)
        if matches:
            return matches[0].strip()
        return None

    def _read_init_file(self, file_path: Path) -> Optional[Dict]:
        """Read and parse the __init__.py file"""
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
        try:
            init_files = []
            if not self.config.directory["enable"]:
                return []

            exclude_dirs = self.config.directory["exclude_dirs"]
            depth_limits = self.config.directory["depth_limits"]

            for root, dirs, files in os.walk(self.root_dir):
                root_path = Path(root)

                if any(
                    part.startswith(".") or part in exclude_dirs
                    for part in root_path.parts
                ):
                    continue

                if root_path != self.root_dir:
                    rel_path = str(root_path.relative_to(self.root_dir)).replace(
                        "\\", "/"
                    )
                    should_skip = False

                    path_parts = rel_path.split("/")
                    current_path = ""
                    matched_depth = None
                    matched_prefix = ""

                    # Find the most matching depth limit rule
                    for part in path_parts:
                        if current_path:
                            current_path += "/"
                        current_path += part

                        if current_path in depth_limits:
                            matched_depth = depth_limits[current_path]
                            matched_prefix = current_path

                    # Calculate remaining depth
                    if matched_depth is not None:
                        remaining_path = rel_path[len(matched_prefix) :].strip("/")
                        current_depth = (
                            len(remaining_path.split("/")) if remaining_path else 0
                        )

                        if current_depth > matched_depth:
                            should_skip = True

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

    def _read_file_docstring(self, file_path: Path) -> Optional[str]:
        """Read docstring from a Python file"""
        try:
            if file_path.suffix == ".py":
                with open(file_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('"""') or first_line.startswith("'''"):
                        return first_line.strip("\"\"\"'''").strip()
                    return None
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        return None

    def _generate_toc(self, path, prefix="", show_files=True):
        """Generate directory tree structure with complete vertical connectors

        Args:
            path: Path to generate structure for
            prefix: Indentation prefix characters
            show_files: Whether to show files, default is False to show only directories
        """
        entries = sorted(os.scandir(path), key=lambda e: e.name)
        exclude_dirs = self.config.directory.get("exclude_dirs", [])
        show_files = self.config.directory.get("show_files", True)
        show_docstrings = self.config.directory.get("show_docstrings", True)

        # Filter conditions
        entries = [
            e
            for e in entries
            if (show_files or e.is_dir())
            and not e.name.startswith(".")
            and not any(exclude in e.path for exclude in exclude_dirs)
        ]

        tree_lines = []
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = "└──" if is_last else "├──"

            if entry.is_file() and show_docstrings:
                docstring = self._read_file_docstring(Path(entry.path))
                if docstring:
                    name = f"{entry.name} # {docstring}"
                else:
                    name = entry.name
            else:
                # If it's a directory, add "/"
                name = f"{entry.name}/" if entry.is_dir() else entry.name

            tree_lines.append(f"{prefix}{connector} {name}")

            if entry.is_dir():
                # If it's the last item, the new indentation doesn't need a vertical line
                extension = "    " if is_last else "│   "
                tree_lines.extend(
                    self._generate_toc(entry.path, prefix + extension, show_files)
                )

        return tree_lines

    def generate(self) -> str:
        """Generate the complete README content"""
        try:
            sections = []

            for section, block in self.config.content_blocks.items():
                if isinstance(block, dict):
                    title = block.get("title", section)
                    content = block.get("content", "")
                else:
                    title = section
                    content = block

                sections.extend([f"# {title}", "", content, ""])

            env_vars = self._get_env_vars()
            if env_vars and self.config.env["enable"]:
                sections.extend(
                    [
                        "# Environment Variables",
                        "",
                        "| Variable Name | Description |",
                        "| --- | --- |",
                        *[
                            f"| {var['key']} | {var['description']} |"
                            for var in env_vars
                        ],
                        "",
                    ]
                )

            docs = self._find_init_files()
            if docs:
                # 產生樹狀結構
                tree_content = [
                    f"# {self.config.directory['title']}",
                    "",
                    "```",
                    f"{self.root_dir.name}/",
                    *self._generate_toc(self.root_dir),
                    "```",
                    "",
                ]
                sections.extend(tree_content)

            sections.extend(
                ["\n", "---", "> This document was automatically generated by ReadGen."]
            )

            return "\n".join(filter(None, sections))

        except Exception as e:
            print(f"Error generating README: {e}")
            return "Unable to generate README content. Please check the error message."
