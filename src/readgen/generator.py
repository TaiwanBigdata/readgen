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
        """Find all __init__.py files and extract documentation"""
        try:
            init_files = []
            exclude_dirs = self.config.settings["exclude_dirs"]
            depth_limits = self.config.settings["depth_limits"]

            for root, dirs, files in os.walk(self.root_dir):
                root_path = Path(root)

                # Check for excluded directories
                should_skip = any(
                    part.startswith(".") or part in exclude_dirs
                    for part in root_path.parts
                )

                if should_skip:
                    continue

                # Check depth limits
                if root_path != self.root_dir:
                    rel_path = str(root_path.relative_to(self.root_dir)).replace(
                        "\\", "/"
                    )

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
        """Generate directory structure and module descriptions"""
        if not docs:
            return "## Directory Structure and Module Descriptions\n\n*No directory information available*"

        sections = ["# Directory Structure", ""]
        project_name = self.root_dir.name  # Get the root directory name
        sections.append(
            f"* **{project_name}**"
        )  # Use the root directory name as the top level

        for doc in docs:
            path = doc["path"].replace("\\", "/")
            indent = "  " * (path.count("/") + 1)  # Increase indentation for sub-items

            if doc["doc"]:
                doc_text = doc["doc"].split("\n")[0].strip()
                sections.append(f"{indent}* **{path}**: {doc_text}")
            else:
                sections.append(f"{indent}* **{path}**")

        return "\n".join(sections)

    def generate(self) -> str:
        """Generate the complete README content"""
        try:
            sections = []

            # Process all content blocks with h1 titles
            for section, block in self.config.content_blocks.items():
                # Retrieve block content, which may be a string or dictionary
                if isinstance(block, dict):
                    title = block.get("title", section)  # Use title if provided
                    content = block.get("content", "")  # Retrieve content
                else:
                    title = section
                    content = block

                sections.extend(
                    [f"# {title}", "", content, ""]  # Use custom title or section name
                )

            # Process environment variables
            env_vars = self._get_env_vars()
            if env_vars:
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

            # Generate directory structure (always last)
            docs = self._find_init_files()
            if docs:
                toc_content = self._generate_toc(docs)
                toc_content = toc_content.replace(
                    "## Directory Structure and Module Descriptions",
                    "# Directory Structure",
                )
                sections.extend([toc_content, ""])

            # Add footer
            sections.extend(
                ["---", "> This document was automatically generated by readgen."]
            )

            return "\n".join(filter(None, sections))

        except Exception as e:
            print(f"Error generating README: {e}")
            return "Unable to generate README content. Please check the error message."


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
