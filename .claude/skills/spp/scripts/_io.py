"""Shared I/O helpers — atomic writes per /spp-loop.md §4 discipline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str) -> None:
    """Write text via tmp + fsync + rename.

    The prior file is replaced atomically; partial writes never appear at
    ``path``. On any error before the rename, the tmp file is cleaned up
    and the prior file is untouched.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def atomic_write_json(path: Path, data: Any, indent: int = 2) -> None:
    """JSON-serialize ``data`` and atomic-write to ``path``."""
    atomic_write_text(path, json.dumps(data, indent=indent, sort_keys=False) + "\n")
