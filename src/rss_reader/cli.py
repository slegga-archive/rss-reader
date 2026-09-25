"""CLI logic for rss-reader."""

from __future__ import annotations

import argparse
import calendar
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests
import yaml

from rss_reader.model import RSS

DEFAULT_FEEDS = [
    "http://vettogvitenskap.libsyn.com/rss",
    "https://rss.podplaystudio.com/608.xml",
    "https://feeds.acast.com/public/shows/30-minutter-inn-i-fremtiden",
    "https://sindrel.github.io/nrk-pod-feeds/rss/abels_taarn.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/burde_vaert_pensum.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/ekko_-_et_aktuelt_samfunnsprogram.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/kjente_boeker_paa_4_minutter.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/oppdatert.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/trygdekontoret.xml",
    "https://feed.podbean.com/vertshuset/feed.xml",
    "https://media.rss.com/spacepodden/feed.xml",
]

UNWANTED_KEYWORDS = ["antipanel", "reprise", "trær", "plante"]

NORE = 300


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="rss-reader",
        description="RSS Reader.  Pick episodes to download.",
    )
    p.add_argument("--list", type=int, nargs="?", const=7, default=7,
                   help="List the N best episodes (default 7).")
    p.add_argument("--dryrun", action="store_true",
                   help="Print to screen instead of doing changes.")
    p.add_argument("--reject", type=str, default=None,
                   help="Comma-separated list of episode ids to reject.")
    p.add_argument("--download", type=str, default=None,
                   help="Comma-separated list of episode ids to download.")
    p.add_argument("--downloaddir", type=str, default=None,
                   help="Directory to download episodes into.")
    p.add_argument("--update", action="store_true",
                   help="Force full update of database based on feeds.")
    return p.parse_args(argv)


def load_config() -> dict:
    config_dir = os.environ.get("CONFIG_DIR", os.path.join(os.environ.get("HOME", ""), "etc"))
    configfile = os.path.join(config_dir, "rss-reader.yml")
    if not os.path.isfile(configfile):
        return {}
    with open(configfile, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_downloaddir(args: argparse.Namespace, config: dict) -> str:
    dd = args.downloaddir or config.get("downloaddir")
    if not dd:
        config_dir = os.environ.get("CONFIG_DIR", os.path.join(os.environ.get("HOME", ""), "etc"))
        die(f"Missing config downloaddir: in file {config_dir}/rss-reader.yml")
    return dd


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def wsl_mount_hint(dest: Path) -> str:
    m = re.match(r"^/mnt/([a-zA-Z])(?:/|$)", str(dest))
    if not m:
        return ""
    letter = m.group(1).lower()
    return f"sudo mount -t drvfs {letter.upper()}: /mnt/{letter} -o uid={os.getuid()},gid={os.getgid()},umask=022"


def _fetch_single_feed(url: str, nore: int) -> list[dict]:
    """Fetch one RSS feed and return a list of normalised item dicts."""
    try:
        resp = feedparser.parse(url)
    except Exception as exc:
        print(f"  WARN: failed to fetch {url}: {exc}", file=sys.stderr)
        return []

    items: list[dict] = []
    for entry in resp.entries[:nore]:
        item: dict = {}

        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            item["published_epoch"] = int(calendar.timegm(published))
        else:
            pub_raw = entry.get("published") or entry.get("updated") or ""
            try:
                dt = parsedate_to_datetime(pub_raw)
                item["published_epoch"] = int(dt.timestamp())
            except Exception:
                item["published_epoch"] = 0

        item["feed"] = resp.feed.get("title", url)
        item["title"] = entry.get("title", "")
        item["description"] = entry.get("summary", entry.get("description", ""))
        item["id"] = entry.get("id") or entry.get("link", "")

        enclosures = entry.get("enclosures", [])
        if enclosures:
            url_val = enclosures[0].get("href") or enclosures[0].get("url", "")
        else:
            url_val = entry.get("link", "")
        if not url_val or "mp3" not in url_val.lower():
            continue
        item["url"] = url_val

        items.append(item)

    return items


def get_new_episodes(
    rss: RSS,
    feeds: list[str],
    nore: int,
    rejected: set[str],
    states: dict,
) -> list[dict]:
    """Fetch new episodes from all feeds and insert them into the DB."""
    print("Update the database")
    now = int(time.time())

    all_items: list[dict] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_single_feed, url, nore): url for url in feeds}
        for fut in as_completed(futures):
            url = futures[fut]
            print(f"  {url}")
            try:
                all_items.extend(fut.result())
            except Exception as exc:
                print(f"  WARN: {url}: {exc}", file=sys.stderr)

    retrieve_epoch = states.get("retrieve_episodes_epoch", 0)
    filtered: list[dict] = []
    for item in all_items:
        if retrieve_epoch and item.get("published_epoch", 0) <= retrieve_epoch:
            continue
        title = item.get("title", "")
        desc = item.get("description", "")
        if any(re.search(kw, title, re.IGNORECASE) for kw in UNWANTED_KEYWORDS):
            continue
        if any(re.search(kw, desc, re.IGNORECASE) for kw in UNWANTED_KEYWORDS):
            continue
        if item["id"] in rejected:
            continue
        filtered.append(item)

    rss.episodes_update(filtered)
    rss.states_integer({"retrieve_episodes_epoch": now})
    return filtered


def do_list(rss: RSS, count: int) -> None:
    all_eps = rss.episodes_read_all()
    visible = [
        e for e in all_eps
        if e.get("title") and not e.get("is_rejected") and not e.get("is_downloaded")
    ]
    visible.sort(key=lambda e: e.get("published_epoch", 0), reverse=True)
    for item in visible[:count]:
        ts = datetime.fromtimestamp(item["published_epoch"], tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        print(item["id"], ts, item["feed"])
        for key in ("title", "description", "url"):
            print(item.get(key, ""))
        print("--")


def do_reject(rss: RSS, ids_str: str, *, dryrun: bool) -> None:
    ids = [s.strip() for s in ids_str.split(",") if s.strip()]
    if dryrun:
        print(f"DRYRUN: would reject {ids}")
        return
    rss.episodes_rejected_add(*ids)


def show_progress(done: int, total: int | None) -> None:
    if total:
        pct = min(100, done * 100 // total)
        sys.stderr.write(f"\r[{'#' * (pct // 2):<50}] {pct:3d}%")
    else:
        sys.stderr.write(f"\r{done} bytes")
    sys.stderr.flush()


def fetch_to_file(url: str, dest: Path) -> None:
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    total = int(r.headers.get("Content-Length") or 0) or None
    done = 0
    try:
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                done += len(chunk)
                show_progress(done, total)
    finally:
        if done:
            print(file=sys.stderr)


def do_download(rss: RSS, ids_str: str, downloaddir: str, *, dryrun: bool) -> None:
    ids = [s.strip() for s in ids_str.split(",") if s.strip()]
    episodes = rss.episodes_read_by_ids(*ids)
    dd = Path(downloaddir)
    urls = []
    for ep in episodes:
        u = ep.get("url", "")
        u = re.sub(r"\?.*", "", u)
        urls.append(u)

    if dryrun:
        print(f"DRYRUN: wget -P {dd} {' '.join(urls)}")
    else:
        dd.mkdir(parents=True, exist_ok=True)
        for url in urls:
            filename = url.rsplit("/", 1)[-1] if "/" in url else "episode.mp3"
            dest = dd / filename
            print(f"Downloading {url} -> {dest}")
            try:
                fetch_to_file(url, dest)
            except Exception as exc:
                hint = wsl_mount_hint(dest) if isinstance(exc, PermissionError) else ""
                die(f"Download failed: {exc} {url}\n{hint}" if hint else f"Download failed: {exc} {url}")

    for ep in episodes:
        rss.episodes_set_downloaded(ep["id"])

    if not dryrun and dd.is_dir():
        for p in dd.iterdir():
            if p.is_file() and not p.stat().st_size:
                die(f"File size for {p} is 0. Media is probably full.")
            m = re.match(r"^(.+)\.mp3\.(\d+)$", p.name, re.IGNORECASE)
            if m:
                newname = f"{m.group(1)}.{m.group(2)}.mp3"
                target = dd / newname
                if target.exists():
                    import random
                    newname = f"{m.group(1)}.{m.group(2)}.{random.randint(0, 99999)}.mp3"
                    target = dd / newname
                print(f"rename {p.name} to {newname}")
                p.rename(target)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_config()
    rss = RSS()
    states = rss.states_integer()

    nore = args.list if args.list else NORE
    if args.update:
        nore = NORE
        states["retrieve_episodes_epoch"] = int(time.time()) - 4 * 30 * 24 * 60 * 60

    seven_days = 7 * 24 * 60 * 60
    if states.get("retrieve_episodes_epoch", 0) < int(time.time()) - seven_days or args.update:
        rejected_ids = set(rss.episodes_read_handeled())
        get_new_episodes(rss, DEFAULT_FEEDS, nore, rejected_ids, states)

    if args.reject:
        do_reject(rss, args.reject, dryrun=args.dryrun)
        return

    if args.download:
        dd = get_downloaddir(args, config)
        do_download(rss, args.download, dd, dryrun=args.dryrun)
        return

    do_list(rss, args.list)
