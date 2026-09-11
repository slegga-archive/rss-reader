"""Test CLI smoke — mirrors t/rss-reader.t."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin" / "rss-reader"


def test_script_parses_without_syntax_errors() -> None:
    """Equivalent to t/basic-script-compile.t — the script compiles."""
    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{BIN}').read())"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Syntax error: {result.stderr}"


def test_help_flag(capsys) -> None:
    """Equivalent to t/rss-reader.t — --help works and mentions the program name."""
    result = subprocess.run(
        [sys.executable, str(BIN), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "rss-reader" in result.stdout
