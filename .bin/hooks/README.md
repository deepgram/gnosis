# Git Hooks

This directory contains Git hooks to ensure consistent commit message formatting and enforce the project's contribution guidelines.

## Available Hooks

1. **commit-msg**: Validates that commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) format.
   - Checks for proper format: `<type>(<scope>): <description>`
   - Ensures a blank line between subject and body
   - Requires a proper body when multi-line commits are made

2. **prepare-commit-msg**: Provides a template for creating well-formatted commit messages.
   - Creates a template in your editor when you commit
   - Includes guidance for writing good commit messages
   - Reminds you to include file references

## Installation

Run the install script from the project root:

```bash
./.bin/hooks/install-hooks.sh
```

This will copy the hooks to your local `.git/hooks` directory and make them executable.

## Manual Installation

If you prefer to install manually:

1. Copy the hooks to your `.git/hooks` directory:
   ```bash
   cp .bin/hooks/commit-msg .git/hooks/
   cp .bin/hooks/prepare-commit-msg .git/hooks/
   ```

2. Make them executable:
   ```bash
   chmod +x .git/hooks/commit-msg
   chmod +x .git/hooks/prepare-commit-msg
   ```

## Conventional Commits Format

Commit messages must follow this format:

```
<type>(<scope>): <description>

<body>

References:
file1.py (lines x-y)
file2.py (lines a-b)
```

Where:
- **type**: The category of change (feat, fix, docs, style, refactor, perf, test, chore)
- **scope**: (Optional) The part of the codebase affected
- **description**: A short summary of the change
- **body**: Detailed explanation of the change
- **references**: List of files changed with line numbers 