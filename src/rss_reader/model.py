"""SQLite-backed episode store.

Equivalent to the Perl Model::RSS module.  All communication with the
RSS.db database goes through the :class:`RSS` class.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class RSS:
    """Handle all communication with the SQLite database."""

    def __init__(self, dbfile: str | Path = "data/RSS.db", *, debug: bool = False) -> None:
        self.dbfile = Path(dbfile)
        self.debug = debug
        self._conn: sqlite3.Connection | None = None

    # -- connection helpers ---------------------------------------------------

    def _resolve_dbfile(self) -> Path:
        p = self.dbfile
        if p.is_absolute():
            return p
        # Resolve relative to the project root (three levels up from
        # src/rss_reader/model.py).
        return Path(__file__).resolve().parent.parent.parent / p

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            dbpath = self._resolve_dbfile()
            if not dbpath.exists():
                dbpath.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(dbpath))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- internal helpers -----------------------------------------------------

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        try:
            cur = self.conn.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            raise RuntimeError(f"DB ERROR: {exc}  sql={sql!r}  params={params!r}") from exc

    def _execute(self, sql: str, params: tuple = ()) -> None:
        try:
            self.conn.execute(sql, params)
            self.conn.commit()
        except Exception as exc:
            raise RuntimeError(f"DB ERROR: {exc}  sql={sql!r}  params={params!r}") from exc

    def _episode_write(self, episode: dict) -> None:
        if "id" not in episode:
            raise ValueError("Missing id as key")

        old_rows = self._query("SELECT * FROM episodes WHERE id = ?", (episode["id"],))
        if old_rows:
            old = old_rows[0]
            for key, val in old.items():
                if key not in episode or episode[key] is None or (isinstance(episode[key], str) and not episode[key]):
                    episode[key] = val

        keys = list(episode.keys())
        values = [episode[k] for k in keys]
        placeholders = ", ".join("?" for _ in values)
        col_names = ", ".join(keys)
        sql = f"REPLACE INTO episodes({col_names}) VALUES({placeholders})"
        self._execute(sql, tuple(values))

    # -- public API -----------------------------------------------------------

    def episodes_update(self, hashes: list[dict]) -> None:
        """Update / insert a list of episode dicts."""
        for h in hashes:
            merged = dict(h)
            if "id" in merged:
                old_rows = self.episodes_read_by_ids(merged["id"])
                if old_rows:
                    old = dict(old_rows[0])
                    old.update(merged)
                    merged = old
            keys = list(merged.keys())
            values = [merged[k] for k in keys]
            placeholders = ", ".join("?" for _ in values)
            col_names = ", ".join(keys)
            sql = f"REPLACE INTO episodes({col_names}) VALUES({placeholders})"
            self._execute(sql, tuple(values))

    def episodes_rejected_add(self, *ids: str) -> None:
        """Mark one or more episodes as rejected."""
        for ep_id in ids:
            self._episode_write({"id": ep_id, "is_rejected": 1})

    def episodes_read_handeled(self) -> list[str]:
        """Return ids of episodes that are either rejected or downloaded."""
        rows = self._query("SELECT id FROM episodes WHERE is_rejected = 1 OR is_downloaded = 1")
        return [r["id"] for r in rows]

    def episodes_read_all(self) -> list[dict]:
        """Return all episodes."""
        return self._query("SELECT * FROM episodes")

    def episodes_read_by_ids(self, *ids: str) -> list[dict]:
        """Get episodes by ids."""
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        return self._query(f"SELECT * FROM episodes WHERE id IN ({placeholders})", ids)

    def episodes_set_downloaded(self, *ids: str) -> None:
        """Register that episodes have been downloaded."""
        for ep_id in ids:
            self._episode_write({"id": ep_id, "is_downloaded": 1})

    def states_integer(self, update: dict | None = None) -> dict:
        """Read or update integer state key/value pairs.

        If *update* is a dict, write each pair and return all states.
        If *update* is None, just return all states.
        """
        if update is not None:
            for name, value in update.items():
                self._execute(
                    "REPLACE INTO states_integer(name, value) VALUES(?, ?)",
                    (name, value),
                )
        rows = self._query("SELECT name, value FROM states_integer")
        return {r["name"]: r["value"] for r in rows}
