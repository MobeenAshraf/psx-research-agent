"""Shared utilities for the project."""

from pathlib import Path


def find_repo_root() -> Path:
    """Find the repository root by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()

