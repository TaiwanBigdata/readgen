# ReadGen

A simple yet powerful Python project README.md generator.

## Features

-   Automatically scans project structure and generates directory descriptions
-   Reads project settings from `project.yaml`
-   Supports parsing `.env.example` to generate environment variable documentation
-   Automatically extracts docstrings from **init**.py files in each folder
-   Generates standardized Markdown format documentation

## Installation

```bash
$ pip install tbi-readgen

# Recommendation, as it can be used globally.
$ pipx install tbi-readgen
```

## Usage

### Basic Usage

```bash
$ readgen
```

### Project Configuration File

Create a project.yaml file in the project root:

```yaml
project:
    name: 'Project Name'
    description: 'Project Description'

authors:
    - name: 'Author Name'
      email: 'email@example.com'

dependencies:
    - python >= 3.7
    - PyYAML >= 6.0.1
```

## Compatibility

-   Supports Python 3.7 and above
-   Compatible with Windows, macOS, and Linux

## License

This project is licensed under the MIT License. See the LICENSE file for details.
