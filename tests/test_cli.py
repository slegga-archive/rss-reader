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


def test_wsl_mount_hint_suggests_mount_for_slash_mnt_letter() -> None:
    from rss_reader.cli import wsl_mount_hint

    hint = wsl_mount_hint(Path("/mnt/d/episode.mp3"))
    assert hint.startswith("sudo mount -t drvfs D: /mnt/d ")
    assert "uid=" in hint and "gid=" in hint and "umask=022" in hint


def test_wsl_mount_hint_matches_bare_mountpoint() -> None:
    from rss_reader.cli import wsl_mount_hint

    assert "D: /mnt/d" in wsl_mount_hint(Path("/mnt/d"))


def test_wsl_mount_hint_empty_for_non_wsl_path() -> None:
    from rss_reader.cli import wsl_mount_hint

    assert wsl_mount_hint(Path("/home/stein/episode.mp3")) == ""
    assert wsl_mount_hint(Path("/mnt/share/episode.mp3")) == ""


def test_show_progress_with_total(capsys) -> None:
    from rss_reader.cli import show_progress

    show_progress(50, 100)
    err = capsys.readouterr().err
    assert err.startswith("\r[")
    assert "#" * 25 in err
    assert "50%" in err


def test_show_progress_caps_at_100_percent(capsys) -> None:
    from rss_reader.cli import show_progress

    show_progress(200, 100)
    err = capsys.readouterr().err
    assert "100%" in err


def test_show_progress_without_total(capsys) -> None:
    from rss_reader.cli import show_progress

    show_progress(1234, None)
    err = capsys.readouterr().err
    assert err == "\r1234 bytes"
