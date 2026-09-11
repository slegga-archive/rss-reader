# Gotchas

- `data/RSS.db` er en del av repoet og skal versjonkontrolleres.
- Hard exit på feil (bruk `sys.exit(1)` / `die()`-ekvivalent).
- Skriptene bruker PEP 723 inline-metadata slik at `uv run` automatisk
  installerer avhengighetene uten et virtuelt miljø.
- `bin/rss-reader` resolver `data/RSS.db` relativt til prosjektroten
  (via `Path(__file__).resolve().parent.parent`), ikke arbeidskatalogen.
- `feedparser` returnerer `published_parsed` som en `time.struct_time` i
  UTC — konverter med `calendar.timegm()`, ikke `time.mktime()`.
- SQLite `REPLACE INTO` krever at alle NOT NULL-kolonner er med i
  INSERT-setningen; pass på at `id` alltid er satt.
- `--list` uten verdi gir 7 (standard); `--list=0` er gyldig og gir ingen
  resultater.
