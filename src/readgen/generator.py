from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import os
from readgen.utils import paths
from readgen.config import ReadmeConfig


class ReadmeGenerator:
    """README Generator"""

    # Supported file types for comments
    SUPPORTED_EXTENSIONS = {
        ".py",
        ".toml",
        ".yaml",
        ".yml",
        ".r",
        ".sh",
        ".bash",
        ".zsh",
        ".pl",
    }

    def __init__(self):
        self.root_dir = paths.ROOT_PATH
        self.config = ReadmeConfig(self.root_dir)
        self.max_tree_width = 0

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
        try:
            if not hasattr(current_path, "relative_to"):
                current_path = Path(current_path)
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
        except Exception as e:
            print(f"Error in _is_path_excluded: {str(e)}")
            return True

    def _should_include_entry(
        self, path: Path, is_dir: bool, show_files: bool = True
    ) -> bool:
        """Check if the entry should be included based on configuration rules"""
        exclude_dirs = self.config.directory["exclude_dirs"]
        exclude_files = self.config.directory["exclude_files"]

        if is_dir:
            return not (
                self._is_path_excluded(path, exclude_dirs) or path.name.startswith(".")
            )
        return (
            show_files
            and not any(fnmatch(path.name, pattern) for pattern in exclude_files)
            and path.name != "__init__.py"
        )

    def _read_file_first_comment(self, file_path: Path) -> Optional[str]:
        """Read first line comment from various file types

        Args:
            file_path: Path to the file

        Returns:
            Optional[str]: First line comment if exists, otherwise None
        """
        COMMENT_PATTERNS = {
            ".py": "#",
            ".toml": "#",
            ".yaml": "#",
            ".yml": "#",
            ".r": "#",
            ".sh": "#",
            ".bash": "#",
            ".zsh": "#",
            ".pl": "#",
        }

        try:
            suffix = file_path.suffix.lower()

            if suffix not in self.SUPPORTED_EXTENSIONS:
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("#"):
                    return first_line[1:].strip()

            return None

        except Exception as e:
            print(f"Error reading comment from {file_path}: {str(e)}")
            return None

    def _get_env_vars(self) -> List[Dict[str, Any]]:
        """Retrieve environment variable descriptions from .env.example with category support"""
        env_vars = []
        current_category = "General"  # Default category
        current_vars = []

        env_path = self.root_dir / self.config.env["env_file"]
        if not env_path.exists():
            return []

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue

                    # Check if this is a category comment
                    if line.startswith("#"):
                        # If we have variables in the current category, save them
                        if current_vars:
                            env_vars.append(
                                {
                                    "category": current_category,
                                    "variables": current_vars,
                                }
                            )
                            current_vars = []
                        current_category = line[1:].strip()
                        continue

                    # Process variable lines
                    if "=" in line:
                        key = line.split("=")[0].strip()
                        current_vars.append(key)

            # Don't forget to add the last category
            if current_vars:
                env_vars.append(
                    {"category": current_category, "variables": current_vars}
                )

        except Exception as e:
            print(f"Error reading .env: {e}")

        return env_vars

    def _scan_project_structure(self) -> List[Dict]:
        """Scan project structure and return directory information"""
        init_files = []
        if not self.config.directory["enable"]:
            return []

        max_depth = self.config.directory["max_depth"]
        root_path_len = len(self.root_dir.parts)

        try:
            for root, dirs, files in os.walk(self.root_dir):
                root_path = Path(root)

                # Skip if directory should be excluded
                if not self._should_include_entry(root_path, True):
                    dirs.clear()
                    continue

                # Remove excluded directories from dirs list to prevent walking into them
                dirs[:] = [
                    d for d in dirs if self._should_include_entry(root_path / d, True)
                ]

                # Check depth
                if root_path != self.root_dir:
                    current_depth = len(root_path.parts) - root_path_len

                    if max_depth is not None and current_depth > max_depth:
                        dirs.clear()
                        continue

                    # Add directory to structure
                    dir_info = {
                        "path": str(root_path.relative_to(self.root_dir)).replace(
                            "\\", "/"
                        ),
                        "doc": "",
                    }

                    # Read comment if __init__.py exists
                    if "__init__.py" in files:
                        init_path = root_path / "__init__.py"
                        comment = self._read_file_first_comment(init_path)
                        if comment:
                            dir_info["doc"] = comment

                    init_files.append(dir_info)

                # Stop recursion if max depth reached
                if (
                    max_depth is not None
                    and len(root_path.parts) - root_path_len >= max_depth
                ):
                    dirs.clear()

            return sorted(init_files, key=lambda x: x["path"])

        except Exception as e:
            print(f"Error in _scan_project_structure: {e}")
            return []

    def _calculate_tree_width(self, path: str, prefix: str = "") -> int:
        """Calculate the maximum width needed for the tree structure"""
        entries = sorted(Path(path).iterdir(), key=lambda e: e.name)
        max_width = 0

        filtered_entries = [
            e
            for e in entries
            if self._should_include_entry(
                e, e.is_dir(), self.config.directory["show_files"]
            )
        ]

        for idx, entry in enumerate(filtered_entries):
            is_last = idx == len(filtered_entries) - 1
            connector = "└── " if is_last else "├── "
            name = entry.name + ("/" if entry.is_dir() else "")
            width = len(prefix + connector + name)
            max_width = max(max_width, width)

            if entry.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                subtree_width = self._calculate_tree_width(str(entry), next_prefix)
                max_width = max(max_width, subtree_width)

        return max_width

    def _generate_toc(
        self, path: str, prefix: str = "", first_call: bool = True
    ) -> List[str]:
        """Generate directory tree structure with aligned comments"""
        current_path = Path(path)
        entries = sorted(current_path.iterdir(), key=lambda e: e.name)
        show_comments = self.config.directory["show_comments"]
        max_depth = self.config.directory["max_depth"]
        root_path_len = len(self.root_dir.parts)
        show_files = self.config.directory["show_files"]

        # Calculate current depth and stop if max depth reached
        current_depth = len(current_path.parts) - root_path_len
        if max_depth is not None and current_depth >= max_depth:
            return []

        # Filter entries
        filtered_entries = []
        for entry in entries:
            try:
                if self._should_include_entry(entry, entry.is_dir(), show_files):
                    filtered_entries.append(entry)
            except Exception as e:
                print(f"Error filtering entry {entry}: {str(e)}")
                continue

        # Calculate max width on first call
        if first_call:
            self.max_tree_width = self._calculate_tree_width(str(current_path))

        tree_lines = []
        for idx, entry in enumerate(filtered_entries):
            try:
                is_last = idx == len(filtered_entries) - 1
                connector = "└──" if is_last else "├──"
                name = f"{entry.name}/" if entry.is_dir() else entry.name

                comment = None
                if show_comments:
                    if entry.is_dir():
                        init_path = entry / "__init__.py"
                        if init_path.exists():
                            comment = self._read_file_first_comment(init_path)
                    elif entry.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        comment = self._read_file_first_comment(entry)

                base_line = f"{prefix}{connector} {name}"
                if comment:
                    padding = " " * (self.max_tree_width - len(base_line) + 2)
                    line = f"{base_line}{padding}# {comment}"
                else:
                    line = base_line

                tree_lines.append(line)

                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    tree_lines.extend(
                        self._generate_toc(str(entry), prefix + extension, False)
                    )
            except Exception as e:
                print(f"Error processing entry {entry}: {str(e)}")
                continue

        return tree_lines

    def _normalize_content(self, content: List[str]) -> List[str]:
        """Normalize content by removing excessive empty lines within a section"""
        # Remove empty lines from start and end
        while content and not content[0].strip():
            content.pop(0)
        while content and not content[-1].strip():
            content.pop()

        # Normalize empty lines within section
        normalized = []
        prev_empty = False

        for line in content:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            normalized.append(line)
            prev_empty = is_empty

        return normalized

    def _format_env_vars(self, env_vars: List[Dict[str, Any]]) -> List[str]:
        """Format environment variables section with proper spacing"""
        formatted = []

        for idx, category in enumerate(env_vars):
            if category["variables"]:
                if idx > 0:
                    formatted.append("")

                formatted.append(category["category"])
                formatted.append("")  # Empty line after category title
                formatted.extend([f"- `{var}`" for var in category["variables"]])

        return formatted

    def generate(self) -> str:
        """Generate the complete README content"""
        try:
            sections = []

            # Process content blocks
            for section, block in self.config.content_blocks.items():
                if isinstance(block, dict):
                    title = block.get("title", section)
                    content = block.get("content", "").strip()
                else:
                    title = section
                    content = block.strip()

                block_content = self._normalize_content([f"# {title}", "", content])
                sections.extend(block_content)
                sections.extend(["", ""])

            # Process environment variables section
            env_vars = self._get_env_vars()
            if env_vars and self.config.env["enable"]:
                env_title = self.config.env.get("title", "Environment Variables")
                env_content = self.config.env.get("content", "")

                env_section = [f"# {env_title}", ""]
                if env_content:
                    env_section.extend([env_content, ""])

                env_section.extend(self._format_env_vars(env_vars))
                sections.extend(self._normalize_content(env_section))
                sections.extend(["", ""])

            # Process directory structure section
            project_structure = self._scan_project_structure()
            if project_structure and self.config.directory["enable"]:
                directory_title = self.config.directory.get(
                    "title", "Directory Structure"
                )
                directory_content = self.config.directory.get("content", "")

                dir_section = [
                    f"# {directory_title}",
                    "",
                    directory_content,
                    "",
                    "```",
                    f"{self.root_dir.name}/",
                    *self._generate_toc(self.root_dir),
                    "```",
                ]

                sections.extend(self._normalize_content(dir_section))
                sections.extend(["", ""])

            # Add footer
            footer = [
                "---",
                "> This document was automatically generated by [ReadGen](https://github.com/TaiwanBigdata/readgen).",
            ]
            sections.extend(self._normalize_content(footer))

            # Combine all sections and ensure final newline
            final_content = "\n".join(sections)
            if not final_content.endswith("\n"):
                final_content += "\n"

            return final_content

        except Exception as e:
            print(f"Error generating README: {e}")
            return "Unable to generate README content. Please check the error message."
