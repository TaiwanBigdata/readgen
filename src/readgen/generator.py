# This is the main module for ReadGen.

from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
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

    def _is_path_excluded(self, current_path: Path, exclude_patterns: Set[str]) -> bool:
        """Check if the path should be excluded based on the exclude patterns.

        Supports three types of pattern matching:
        1. Full path matching (e.g., 'src/readgen/utils')
        2. Directory name matching (e.g., 'utils')
        3. Path pattern matching (e.g., 'src/*/utils')

        Args:
            current_path: Path to check
            exclude_patterns: Set of exclude patterns

        Returns:
            bool: True if the path should be excluded
        """
        rel_path = current_path.relative_to(self.root_dir)
        rel_path_str = str(rel_path).replace("\\", "/")

        for pattern in exclude_patterns:
            # Case 1: Full path matching
            if fnmatch(rel_path_str, pattern):
                return True

            # Case 2: Directory name matching
            if fnmatch(current_path.name, pattern):
                return True

            # Case 3: Path pattern matching (e.g., 'src/*/utils')
            pattern_parts = pattern.split("/")
            path_parts = rel_path_str.split("/")

            if len(pattern_parts) <= len(path_parts):
                matches = True
                for pattern_part, path_part in zip(pattern_parts, path_parts):
                    if not fnmatch(path_part, pattern_part):
                        matches = False
                        break
                if matches:
                    return True

        return False

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

    def _scan_project_structure(self) -> List[Dict]:
        """Scan project structure and return directory information"""
        try:
            init_files = []
            if not self.config.directory["enable"]:
                return []

            exclude_dirs = self.config.directory["exclude_dirs"]
            max_depth = self.config.directory["max_depth"]
            root_path_len = len(self.root_dir.parts)

            for root, dirs, files in os.walk(self.root_dir):
                root_path = Path(root)

                # Exclude hidden directories and directories matching exclude patterns
                if any(
                    part.startswith(".") for part in root_path.parts
                ) or self._is_path_excluded(root_path, exclude_dirs):
                    dirs.clear()  # Stop recursion
                    continue

                # Check depth
                if root_path != self.root_dir:
                    current_depth = len(root_path.parts) - root_path_len

                    if max_depth is not None and current_depth > max_depth:
                        dirs.clear()  # Stop recursion
                        continue

                    init_files.append(
                        {
                            "path": str(root_path.relative_to(self.root_dir)).replace(
                                "\\", "/"
                            ),
                            "doc": "",
                        }
                    )

                # If the maximum depth is reached, do not recurse further
                if (
                    max_depth is not None
                    and (len(root_path.parts) - root_path_len) >= max_depth
                ):
                    dirs.clear()

                if "__init__.py" in files:
                    file_path = root_path / "__init__.py"
                    if doc_info := self._read_init_file(file_path):
                        for item in init_files:
                            if item["path"] == doc_info["path"]:
                                item["doc"] = doc_info["doc"]
                                break

            return sorted(init_files, key=lambda x: x["path"])
        except Exception as e:
            print(f"Error in _scan_project_structure: {e}")
            return []

    def _read_file_docstring(self, file_path: Path) -> Optional[str]:
        """Read docstring from a Python file"""
        try:
            if file_path.suffix == ".py":
                with open(file_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#"):
                        return first_line[1:].strip()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        return None

    def _generate_toc(self, path, prefix="", show_files=False):
        """Generate directory tree structure with aligned comments"""
        entries = sorted(os.scandir(path), key=lambda e: e.name)
        exclude_dirs = self.config.directory["exclude_dirs"]
        exclude_files = self.config.directory["exclude_files"]
        show_files = self.config.directory["show_files"]
        show_comments = self.config.directory["show_comments"]
        max_depth = self.config.directory["max_depth"]
        root_path_len = len(self.root_dir.parts)

        current_path = Path(path)

        # Calculate the current depth
        current_depth = len(current_path.parts) - root_path_len

        # If the depth exceeds or equals the maximum, stop further traversal
        if max_depth is not None and current_depth >= max_depth:
            return []

        # Filter items
        entries = [
            e
            for e in entries
            if (show_files or e.is_dir())
            and not (
                e.is_dir()
                and (
                    self._is_path_excluded(Path(e.path), exclude_dirs)
                    or e.name.startswith(".")
                )
            )
            and not (
                e.is_file()
                and (
                    any(fnmatch(e.name, pattern) for pattern in exclude_files)
                    or e.name == "__init__.py"
                )
            )
        ]

        # The rest of the method remains unchanged...
        max_length = (
            max(
                len(prefix + "└── " + e.name + ("/" if e.is_dir() else ""))
                for e in entries
            )
            if entries
            else 0
        )

        tree_lines = []
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = "└──" if is_last else "├──"

            # Prepare filenames
            name = f"{entry.name}/" if entry.is_dir() else entry.name

            # Get comments
            comment = None
            if show_comments:
                if entry.is_dir():
                    init_path = Path(entry.path) / "__init__.py"
                    if init_path.exists():
                        comment = self._read_file_docstring(init_path)
                elif entry.is_file() and entry.name.endswith(".py"):
                    comment = self._read_file_docstring(Path(entry.path))

            # Calculate the full length of the current line
            current_line_length = len(prefix + connector + " " + name)

            # Assemble the output line, ensuring comments are aligned
            if comment:
                padding = " " * (max_length - current_line_length)
                line = f"{prefix}{connector} {name}{padding} # {comment}"
            else:
                line = f"{prefix}{connector} {name}"

            tree_lines.append(line)

            # Recursively process subdirectories, but check the depth first
            if entry.is_dir():
                next_depth = len(Path(entry.path).parts) - root_path_len
                if max_depth is None or next_depth < max_depth:
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
                env_title = self.config.env.get("title", "Environment Variables")
                env_content = self.config.env.get("content", "")
                sections.extend(
                    [
                        f"# {env_title}",
                        env_content,
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

            project_structure = self._scan_project_structure()
            if project_structure and self.config.directory["enable"]:
                directory_title = self.config.directory.get(
                    "title", "Directory Structure"
                )
                directory_content = self.config.directory.get("content", "")
                tree_content = [
                    f"# {directory_title}",
                    directory_content,
                    "",
                    "```",
                    f"{self.root_dir.name}/",
                    *self._generate_toc(self.root_dir),
                    "```",
                    "",
                ]
                sections.extend(tree_content)

            sections.extend(
                [
                    "\n",
                    "---",
                    "> This document was automatically generated by [ReadGen](https://github.com/TaiwanBigdata/readgen).",
                ]
            )

            return "\n".join(filter(None, sections))

        except Exception as e:
            print(f"Error generating README: {e}")
            return "Unable to generate README content. Please check the error message."
