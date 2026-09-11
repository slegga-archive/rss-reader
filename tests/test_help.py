"""Test that scripts support --help.

Equivalent to t/basic-script-help.t.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parent.parent / "bin"

SCRIPTS = sorted(
    p for p in BIN_DIR.iterdir()
    if p.is_file() and not p.name.startswith(".") and not p.suffix == ".py"
)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_help_flag(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--help failed for {script.name}: {result.stderr}"
    assert script.name in result.stdout or script.stem in result.stdout, (
        f"--help output for {script.name} does not mention the script name"
    )
