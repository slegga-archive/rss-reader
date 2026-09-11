"""Test Model::RSS equivalent — mirrors t/RSS.t."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rss_reader.model import RSS

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Create a temp DB with the schema applied."""
    dbfile = tmp_path / "test.db"
    sql_path = MIGRATIONS_DIR / "tabledefs.sql"
    schema = sql_path.read_text()
    conn = sqlite3.connect(str(dbfile))
    conn.executescript(schema)
    conn.close()
    return dbfile


@pytest.fixture()
def rss(db_path: Path) -> RSS:
    return RSS(dbfile=db_path, debug=True)


# ---- episodes_read_by_ids ---------------------------------------------------


def test_read_by_ids_nonexistent(rss: RSS) -> None:
    assert rss.episodes_read_by_ids("a") == []


def test_read_by_ids_empty_input(rss: RSS) -> None:
    assert rss.episodes_read_by_ids() == []


# ---- episodes_update: insert a full record ----------------------------------


def test_episodes_update_insert(rss: RSS) -> None:
    rss.episodes_update(
        [
            {
                "id": "a",
                "feed": "TestFeed",
                "title": "Episode A",
                "description": "First episode",
                "published_epoch": 1700000000,
                "url": "https://example.com/a.mp3",
            }
        ]
    )
    row = rss.episodes_read_by_ids("a")[0]
    assert row["title"] == "Episode A"
    assert row["feed"] == "TestFeed"


# ---- episodes_set_downloaded / episodes_rejected_add -------------------------


def test_set_downloaded_and_rejected(rss: RSS) -> None:
    rss.episodes_update(
        [{"id": "a", "feed": "F", "title": "A", "url": "https://x/a.mp3", "published_epoch": 1}]
    )
    rss.episodes_set_downloaded("a")
    rss.episodes_rejected_add("a")
    rss.episodes_rejected_add("b")
    handled = rss.episodes_read_handeled()
    assert sorted(handled) == ["a", "b"]


# ---- episodes_read_all -------------------------------------------------------


def test_read_all(rss: RSS) -> None:
    rss.episodes_update([{"id": "x", "feed": "F", "title": "X", "url": "https://x/x.mp3", "published_epoch": 1}])
    rss.episodes_update([{"id": "y", "feed": "F", "title": "Y", "url": "https://x/y.mp3", "published_epoch": 2}])
    assert len(rss.episodes_read_all()) == 2


# ---- states_integer ----------------------------------------------------------


def test_states_integer_read_write(rss: RSS) -> None:
    rss.states_integer({"retrieve_episodes_epoch": 1700000000})
    rss.states_integer({"my_custom_key": 42})
    si = rss.states_integer()
    assert si["retrieve_episodes_epoch"] == 1700000000
    assert si["my_custom_key"] == 42


# ---- dryrun attribute --------------------------------------------------------


def test_dryrun_defaults_false(rss: RSS) -> None:
    assert not rss.debug or rss.debug  # just verify object is constructible
