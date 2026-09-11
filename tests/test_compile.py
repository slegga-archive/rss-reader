"""Test that all Python scripts parse without syntax errors.

Equivalent to t/basic-script-compile.t.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parent.parent / "bin"

SCRIPTS = sorted(
    p for p in BIN_DIR.iterdir()
    if p.is_file() and not p.name.startswith(".") and not p.suffix == ".py"
)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_script_compiles(script: Path) -> None:
    source = script.read_text(encoding="utf-8")
    # Skip the shebang / PEP 723 metadata block for AST parsing
    lines = source.splitlines()
    clean_lines: list[str] = []
    in_metadata = False
    for line in lines:
        if line.strip().startswith("# /// script"):
            in_metadata = True
            continue
        if in_metadata and line.strip().startswith("# ///"):
            in_metadata = False
            continue
        if in_metadata:
            continue
        if line.startswith("#!") and clean_lines == []:
            continue
        clean_lines.append(line)
    code = "\n".join(clean_lines)
    ast.parse(code, filename=str(script))
