"""Utilities to resolve project asset directories regardless of CWD."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def project_root() -> Path:
    """Return the absolute path to the repository root."""

    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=None)
def assets_dir(*extra: str | Path) -> Path:
    """Return the absolute path to the ``assets`` directory (optionally joined).

    Parameters
    ----------
    *extra:
        Optional path components to append to the base ``assets`` directory.
    """

    base = project_root() / "assets"
    if extra:
        return base.joinpath(*extra)
    return base
