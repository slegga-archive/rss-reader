# rss-reader

En liten CLI i Python som henter podkast-RSS-feeds, lister de nyeste
uspilte episodene, og lar deg markere episoder som avviste eller laste dem
ned til en lokal katalog.  Tilstanden lagres i en lokal SQLite-database.

## Funksjoner

- Henter og parser flere podkast-feeds (RSS 2.0 / Atom) parallelt.
- Liste over N nyeste ikke-nedlastede, ikke-avviste episoder.
- Markere enkeltepisoder som avviste etter id.
- Laste ned valgte episoder med `requests` til en konfigurerbar katalog.
- Hopper over episoder der tittel eller beskrivelse matcher uønskede
  nøkkelord (standard: `antipanel`, `reprise`, `trær`, `plante`).
- Oppdaterer feed-cachen automatisk maks én gang per 7. dag; tving
  full oppdatering med `--update`.
- Respekterer `--dryrun` for alle muterende handlinger.

## Krav

- Python 3.11 eller nyere.
- [uv](https://docs.astral.sh/uv/) (anbefalt) eller pip for
  pakkehåndtering.
- Avhengigheter (håndteres automatisk av `uv run`):
  - `feedparser`
  - `pyyaml`
  - `requests`
- `data/RSS.db` er en del av repoet og versjonkontrolleres.

## Installering

```bash
# Med uv (anbefalt):
git clone <repo-url> rss-reader
cd rss-reader
uv sync

# Eller med pip:
pip install -e .
```

## Konfigurasjon

`rss-reader` leser en YAML-konfigurasjonsfil:

```
$CONFIG_DIR/rss-reader.yml
# eller, hvis $CONFIG_DIR ikke er satt:
$HOME/etc/rss-reader.yml
```

Nødvendig nøkkel er `downloaddir`:

```yaml
downloaddir: /mnt/usb/podcasts
```

## Bruk

```bash
# List de 7 siste ikke-nedlastede/avviste episodene (standard).
rss-reader --list

# List 20.
rss-reader --list=20

# Marker to episoder som avviste.
rss-reader --reject=guid1,guid2

# Last ned to episoder til den konfigurerte katalogen.
rss-reader --download=guid3,guid4

# Overskriv nedlastingskatalogen for én kjøring.
rss-reader --download=guid5 --downloaddir=/tmp/dl

# Tving full feed-oppdatering (ignorer 7-dagersvinduet).
rss-reader --update

# Skriv ut hva som ville skjedd uten å gjøre endringer.
rss-reader --download=guid6 --dryrun
```

Du kan kombinere `--update` med `--list`/`--reject`/`--download`.

## Kjøring direkte med uv

Skriptene har en PEP 723-metadata-blokk slik at `uv run` automatisk
installerer avhengighetene:

```bash
uv run bin/rss-reader --list
```

## Tilstand

Kjøretidsdata lagres i `data/RSS.db` (en SQLite-database).  Skjemaet
finnes i `migrations/tabledefs.sql`:

- `episodes(id, feed, title, description, published_epoch, url, ...)` — én
  rad per hentet episode.
- `states_integer(name, value)` — nøkkel/verdi-par; verktøyet bruker
  `retrieve_episodes_epoch` for å spore siste vellykkede oppdatering.

For å starte på nytt, slett `data/RSS.db` og kjør på nytt med `--update`.

## Tester

```bash
# Kjør alle tester
uv run pytest tests/ -v

# Kjør lint
uv run ruff check src/ bin/ tests/
```

Testsuiten kjører disse testfilene:

- `tests/test_model.py` — integrasjonstest for `RSS`-modellen mot en
  midlertidig SQLite-DB.
- `tests/test_cli.py` — røyketest for CLI-ens `--help`.
- `tests/test_compile.py` — verifiserer at alle skript i `bin/` parserer
  uten syntaksfeil.
- `tests/test_help.py` — verifiserer at alle skript med argparse støtter
  `--help`.

## Prosjektoppsett

```
rss-reader/
├── bin/
│   ├── rss-reader              # hoved-CLI (Python)
│   ├── apple-url-finder        # Apple-podkast-inspektør
│   └── mp3-tags                # MP3-tag-inspektør
├── src/
│   └── rss_reader/
│       ├── __init__.py
│       ├── __main__.py
│       ├── model.py            # SQLite-basert episode-lager
│       └── cli.py              # CLI-logikk (valgfritt modulbruk)
├── tests/                      # pytest-testsuite
├── migrations/
│   └── tabledefs.sql           # SQLite-skjema
├── data/                       # runtime SQLite-DB (i repoet)
├── t/                          # gamle Perl-tester (bevart for historikk)
├── pyproject.toml              # prosjektmetadata og avhengigheter
├── README.md
└── LICENSE
```

## Mount USB på WSL

```bash
sudo mkdir -p /mnt/d
sudo mount -t drvfs D: /mnt/d
```

## Lisens

MIT — se `LICENSE`.
