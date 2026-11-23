# Private G7 core preview

Run from the repository root with the backend dependencies installed. Place the sixteen development receipts produced by the G7 capture commands in one local directory. Each filename must be its mapping ID plus `.json`:

- `G7-CA-01`, `G7-CA-11`, `G7-CA-22`, `G7-CA-23`
- `G7-FR-01`, `G7-FR-07`, `G7-FR-11`
- `G7-US-07`, `G7-US-11`
- `G7-GB-23`, `G7-DE-23`, `G7-FR-23`, `G7-IT-23`
- `G7-JP-01`, `G7-JP-11`, `G7-JP-23`

```sh
python -m scripts.serve_g7_core_preview /path/to/receipts /path/to/new-workspace
```

From `frontend-v2`, start the existing frontend locally:

```sh
MACROLENS_V2_API_URL=http://127.0.0.1:8140 npm run dev -- --hostname 127.0.0.1
```

Open Dataset Explorer and select the **G7 core** category. The API filter is
`/api/v2/catalog?category=G7%20core`. Native observation previews and comparisons
use the same application endpoints as the regular dataset explorer. The preview
builds a new SQLite database and content-addressed snapshots. It preserves
publisher nulls and carries receipt hashes through the native ingestion engine.

To add the six Canadian and Japanese CPI histories, use the
`live/g7-cpi-development.sqlite3` database from the
[hosted CPI audit](https://github.com/thealexbfx/macro-dashboard/actions/runs/45109331455)
or a new successful six-series development refresh:

```sh
python -m scripts.serve_g7_core_preview /path/to/receipts /path/to/new-workspace \
  --cpi-database /path/to/g7-cpi-development.sqlite3
```

The importer verifies the six exact definitions and checks that the source
database has no release grants. It copies the active native histories and their
ingestion proof records into the new workspace without writing to the input
database.

Legacy metadata remains visible. The existing release database is separate.
Legacy provider fetching, scheduled refresh, and AI are disabled. Rights review
remains pending. Use private local development only.

With both local servers running and Playwright Chromium installed, run the
browser walkthrough from the repository root:

```sh
python -m scripts.test_g7_preview_browser
```

The walkthrough expects the combined 22-series preview, including the CPI
database. Set `MACROLENS_G7_PREVIEW_URL` if the frontend uses another port.

## Optional German national CPI

In Destatis GENESIS table 61111-0002, download the German CSV (Flat) ZIP for
the complete years from 1991 and a second ZIP covering the most recent years.
The selections must overlap. Use the [historical selection](https://genesis.destatis.de/datenbank/online/url/d843791e)
and the [current table](https://genesis.destatis.de/datenbank/online/table/61111-0002)
to reproduce the initial capture. Then run:

```sh
python -m scripts.capture_destatis_cpi_history history.zip recent.zip /path/to/receipts/G7-DE-07.json
python -m scripts.serve_g7_core_preview /path/to/receipts /path/to/new-workspace   --cpi-database /path/to/g7-cpi-development.sqlite3 --include-destatis-cpi
```

The importer keeps unpublished future labels in the receipt and stages the
published index only. The hosted browser walkthrough uses the explicit
`hosted` profile with 20 histories, excluding the direct BLS pair and this
manually acquired German export.

## Optional German real GDP

Download the [2026 Q2 Destatis X13 workbook](https://www.destatis.de/DE/Themen/Wirtschaft/Volkswirtschaftliche-Gesamtrechnungen-Inlandsprodukt/Publikationen/Downloads-Inlandsprodukt/inlandsprodukt-saisonbereinigt-xlsx-2180130.xlsx?__blob=publicationFile&v=60).
This edition is pinned. Recheck workbook metadata and provenance when
updating to a new edition.

```sh
python -m scripts.capture_destatis_gdp_history gdp.xlsx /path/to/receipts/G7-DE-01.json
```

Pass `--include-destatis-gdp` to the preview command to load the receipt.
With both German additions enabled, the full preview loads 24 private histories.

## Optional Italian real GDP

Use the chain-linked GDP SDMX export linked from [Istat's NSDP](https://www.istat.it/nsdp/).
Create the receipt with `python -m scripts.capture_istat_core_history G7-IT-01 gdp.xml /path/to/receipts/G7-IT-01.json`
and pass `--include-istat-gdp` to the private preview. For Italian
unemployment, download the exact `LABOR_SOURCE` URL in the capture script,
then run `python -m scripts.capture_istat_core_history G7-IT-11 unemployment.xml /path/to/receipts/G7-IT-11.json`.
Pass `--include-istat-unemployment` to load it. The six separately captured
German and Italian additions bring the full preview to 28 histories.

## Optional German ILO unemployment rate

Select all years in [Destatis table 13231-0001](https://genesis.destatis.de/datenbank/online/statistic/13231/table/13231-0001)
and download the German CSV (Flat) ZIP with quality flags.

```sh
python -m scripts.capture_destatis_unemployment_history labor.zip /path/to/receipts/G7-DE-11.json
```

Pass `--include-destatis-unemployment` to load the unadjusted original series.

## Optional Italian headline CPI

Download the exact `SOURCE` and `COEFFICIENTS` URLs in the capture script.
The importer checks both languages of the coefficient workbook, then links
the national all-items level segments using the published Istat factors.

```sh
python -m scripts.capture_istat_cpi_history nic.xml coefficients.xlsx /path/to/receipts/G7-IT-07.json
```

Pass `--include-istat-cpi` to load the linked series. The receipt retains
the original period base and value as well as the linked value.
