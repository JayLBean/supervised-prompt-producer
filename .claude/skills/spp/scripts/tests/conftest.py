"""Test config: ensure ``.claude/skills/spp/scripts`` is importable.

The scripts live at ``.claude/skills/spp/scripts/``, which is not a
conventional package path. Tests import the modules directly via a
synthetic ``spp_scripts`` package alias that points at the script
directory.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
PARENT = SCRIPTS_DIR.parent  # .claude/skills/spp


def _install_alias() -> None:
    if "spp_scripts" in sys.modules:
        return
    # Add the parent so the directory ``scripts`` is importable as a
    # package, then alias it to ``spp_scripts`` for cleaner test imports.
    if str(PARENT) not in sys.path:
        sys.path.insert(0, str(PARENT))
    pkg = importlib.import_module("scripts")
    sys.modules["spp_scripts"] = pkg


_install_alias()
