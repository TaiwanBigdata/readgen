from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import os
from readgen.utils import paths
from readgen.config import ReadmeConfig
from pathlib import Path


class ReadmeGenerator:
    """README Generator"""

    # File patterns that support comments
    SUPPORTED_FILE_PATTERNS = {
        # Extensions
        "*.py",
        "*.toml",
        "*.yaml",
        "*.yml",
        "*.r",
        "*.sh",
        "*.bash",
        "*.zsh",
        "*.pl",
        # Special files
        "dockerfile*",
        "makefile",
    }

    def __init__(self):
        self.root_dir = paths.ROOT_PATH
        self.config = ReadmeConfig(self.root_dir)
        self.max_tree_width = 0

    def _is_path_excluded(self, current_path: Path, exclude_patterns: Set[str]) -> bool:
        """
        Check if path should be excluded based on patterns
        Handles:
        - Recursive patterns (**/foo)
        - Simple wildcards (*.pyc)
        - Directory specific patterns (foo/)
        """
        try:
            if not isinstance(current_path, Path):
                current_path = Path(current_path)

            rel_path = current_path.relative_to(self.root_dir)
            rel_path_str = str(rel_path).replace("\\", "/")

            for pattern in exclude_patterns:
                # Handle directory specific patterns
                if pattern.endswith("/"):
                    if not current_path.is_dir():
                        continue
                    pattern = pattern[:-1]

                # Handle recursive patterns
                if "**/" in pattern:
                    parts = pattern.split("**/")
                    target = parts[-1].rstrip("/")
                    if target in rel_path_str.split("/"):
                        return True
                # Handle simple patterns
                elif fnmatch(rel_path_str, pattern.rstrip("/")):
                    return True

            return False
        except Exception as e:
            print(f"Error in path exclusion for {current_path}: {e}")
            return True

    def _should_include_entry(
        self, path: Path, is_dir: bool, show_files: bool = True
    ) -> bool:
        """Check if the entry should be included based on configuration rules"""
        # Always exclude __init__.py from file listing since its comments are shown at directory level
        if path.name == "__init__.py":
            return False

        if not show_files and not is_dir:
            return False

        return not self._is_path_excluded(
            path, self.config.directory["exclude_patterns"]
        )

    def _is_supported_file(self, file_path: Path) -> bool:
        """
        Check if the file is supported for comment extraction using fnmatch

        Args:
            file_path: Path to check

        Returns:
            bool: True if file is supported
        """
        name_lower = file_path.name.lower()
        return any(
            fnmatch(name_lower, pattern.lower())
            for pattern in self.SUPPORTED_FILE_PATTERNS
        )

    def _read_file_first_comment(self, file_path: Path) -> Optional[str]:
        """Read first line comment from supported files

        Args:
            file_path: Path to the file

        Returns:
            Optional[str]: First line comment if exists, otherwise None
        """
        try:
            if not self._is_supported_file(file_path):
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                # Skip empty lines
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("#"):
                        return line[1:].strip()
                    # If we find a non-comment line, stop searching
                    break

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

    def _sort_entries(self, entries: List[Path]) -> List[Path]:
        """Sort entries VSCode style - directories first, then files"""
        return sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower()))

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

                # Just filter directories, no need to sort here
                dirs[:] = [
                    d for d in dirs if self._should_include_entry(root_path / d, True)
                ]

                if root_path != self.root_dir:
                    current_depth = len(root_path.parts) - root_path_len
                    if max_depth is not None and current_depth > max_depth:
                        dirs.clear()
                        continue

                    # Add directory info
                    dir_info = {
                        "path": str(root_path.relative_to(self.root_dir)).replace(
                            "\\", "/"
                        ),
                        "doc": "",
                    }

                    if "__init__.py" in files:
                        init_path = root_path / "__init__.py"
                        comment = self._read_file_first_comment(init_path)
                        if comment:
                            dir_info["doc"] = comment

                    init_files.append(dir_info)

                if (
                    max_depth is not None
                    and len(root_path.parts) - root_path_len >= max_depth
                ):
                    dirs.clear()

            # Final sort using _sort_entries
            path_mapping = {self.root_dir / info["path"]: info for info in init_files}
            sorted_paths = self._sort_entries(list(path_mapping.keys()))
            return [path_mapping[path] for path in sorted_paths]

        except Exception as e:
            print(f"Error in _scan_project_structure: {e}")
            return []

    def _calculate_tree_width(self, path: str, prefix: str = "") -> int:
        """Calculate the maximum width needed for the tree structure"""
        entries = self._sort_entries(list(Path(path).iterdir()))
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
        entries = self._sort_entries(list(current_path.iterdir()))
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
                base_line = f"{prefix}{connector} {name}"

                comment = None
                if show_comments:
                    if entry.is_dir():
                        # # Read comments from directory's __init__.py
                        init_path = entry / "__init__.py"
                        if init_path.exists():
                            comment = self._read_file_first_comment(init_path)
                    elif entry.name != "__init__.py" and self._is_supported_file(entry):
                        # Read comments for non-__init__.py supported files
                        comment = self._read_file_first_comment(entry)

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

            # Process all blocks in the order defined in toml file
            for block_name in self.config.block_order:
                if block_name == "directory" and self.config.directory["enable"]:
                    # Handle directory structure block
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

                elif block_name == "env" and self.config.env["enable"]:
                    # Handle environment variables block
                    env_vars = self._get_env_vars()
                    if env_vars:
                        env_title = self.config.env.get(
                            "title", "Environment Variables"
                        )
                        env_content = self.config.env.get("content", "")

                        env_section = [f"# {env_title}", ""]
                        if env_content:
                            env_section.extend([env_content, ""])
                        env_section.extend(self._format_env_vars(env_vars))
                        sections.extend(self._normalize_content(env_section))
                        sections.extend(["", ""])

                elif block_name in self.config.content_blocks:
                    # Handle regular content blocks
                    block = self.config.content_blocks[block_name]
                    if isinstance(block, dict):
                        title = block.get("title", block_name)
                        content = block.get("content", "").strip()
                    else:
                        title = block_name
                        content = block.strip()

                    block_content = self._normalize_content([f"# {title}", "", content])
                    sections.extend(block_content)
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
