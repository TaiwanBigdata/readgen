# Handle command line interface (CLI) logic
import sys
import argparse
from pathlib import Path
from typing import Optional
from readgen.generator import ReadmeGenerator


def main() -> Optional[int]:
    """CLI main entry point

    Returns:
        Optional[int]: Execution status code, 0 indicates success, 1 indicates failure
    """
    parser = argparse.ArgumentParser(
        description="""
Generate a README.md file in the current directory.

This tool will:
1. Read project information from pyproject.toml
2. Read custom content from readgen.toml
3. Scan the project directory structure
4. Extract docstrings from `__init__.py` files in each folder
5. Generate a standardized README.md
        """,
        epilog="Example: readgen -f -o README.md",
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force overwrite if README.md already exists",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="README.md",
        help="Specify the output file name (default: README.md)",
    )

    args = parser.parse_args()

    try:
        # Check if the output file already exists
        output_path = Path(args.output)
        if output_path.exists() and not args.force:
            print(
                f"Error: {args.output} already exists. Use the --force option to overwrite."
            )
            return 1

        # Create an instance of the generator
        generator = ReadmeGenerator()

        # Generate README content
        readme_content = generator.generate()

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        print(f"✨ Successfully generated {args.output}!")
        return 0

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
