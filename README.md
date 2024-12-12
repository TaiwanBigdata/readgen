# ReadGen
## This document was automatically generated by ReadGen as well!
### tbi-readgen (0.0.9)
A simple yet powerful Python project README.md generator.

# Features
1. Read project information from pyproject.toml
2. Read custom content from readgen.toml
    - Support variable substitution from pyproject.toml
    - Configure directory structure display with depth control
    - Toggle directory section display
3. Scan the project directory structure
4. Extract docstrings from `__init__.py` files in each folder
5. Generate a standardized README.md

# Installation
```bash
$ pip install tbi-readgen

# Recommendation, as it can be used globally.
$ pipx install tbi-readgen
```

# Usage
## CLI
```bash
$ readgen

# Overwrite README.md.
$ readgen -f
```

## Project Configuration File
Create a `readgen.toml` file in the project root:
````toml
[Title]
title = "Method to overwrite [Title], with support for spaces."
content = "Content of the Title Block"

[Markdown]
content = """
## This is a markdown block
1. Read project information from pyproject.toml
2. Read custom content from readgen.toml
3. Scan the project directory structure
4. Extract docstrings from `__init__.py` files in each folder
5. Generate a standardized README.md

```bash
$ pipx install tbi-readgen
```
"""

[Variables]
content = """
Examples of variables from pyproject.toml:
- Use ${project.version} to get the project version
- Use ${project.name} to get the project name
"""

[directory] # `directory` is a built-in method and will not be listed.
title = "Directory Structure" # You can customize block names to override the default "Directory Structure."
content = "123"
enable = false # Default is true. If `enable = false`, it won't list all directories or scan the init instructions.
exclude_dirs = [".git", "venv", "__pycache__", ".venv", "env", "build", "dist"] # Exclude directories from scanning.
depth_limits = { "root" = 1, "root/mother" = 2 } # List the depth of directories, list all by default.
show_files = false # Default is true. Show files in the directory structure.

[env] # `env` is a built-in method and will not be listed.
enable = false # Default is true. Show the environment variables in the project.
env_file = ".env" # Default is ".env". The file to read the environment variables from.
````

### .env file
If `.env` variables include comments, they will follow this format:
```sh
PROJECT_ID=tbi-readgen # Project identification code used for service registration and resource management
APP_ENV=dev # Application runtime environment (dev/stage/prod)
```
| Variable Name | Description |
| --- | --- |
| PROJECT_ID | Project identification code used for service registration and resource management |
| APP_ENV | Application runtime environment (dev/stage/prod) |


# Development
### Setup
```bash
git clone https://github.com/TaiwanBigdata/readgen.git
cd readgen
python -m venv env
source env/bin/activate  # Linux/Mac
pip install -e .
```

# License
This project is licensed under the MIT License.
# Environment Variables
| Variable Name | Description |
| --- | --- |
| PROJECT_ID | This is the project ID description |
| APP_ENV | 這是環境變數的說明 |


---
> This document was automatically generated by ReadGen.