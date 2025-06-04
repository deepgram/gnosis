#!/bin/sh
#
# Script to install Git hooks for the project
#
# Installation: Run this script from the project root
# Usage: ./.bin/hooks/install-hooks.sh

# Set script to exit on any error
set -e

# Get the absolute path to the hooks directory
HOOKS_DIR=$(cd "$(dirname "$0")" && pwd)
GIT_DIR=$(git rev-parse --git-dir)

echo "Installing Git hooks from $HOOKS_DIR to $GIT_DIR/hooks"

# Copy and make executable each hook
for hook in commit-msg prepare-commit-msg; do
    # Check if the hook exists in our hooks directory
    if [ -f "$HOOKS_DIR/$hook" ]; then
        echo "Installing $hook hook..."
        cp "$HOOKS_DIR/$hook" "$GIT_DIR/hooks/"
        chmod +x "$GIT_DIR/hooks/$hook"
    else
        echo "Warning: $hook hook not found in $HOOKS_DIR"
    fi
done

echo "Git hooks installation complete!"
echo "The following hooks were installed:"
echo "- commit-msg: Validates that commit messages follow conventional commits format"
echo "- prepare-commit-msg: Provides a template for writing conventional commits"

exit 0 