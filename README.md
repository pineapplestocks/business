# business

This repo now contains two layers:

1. The existing static business demo pages already checked into the repo.
2. A new automation pipeline to scrape leads, generate demo sites, and power a simple local CRM.

## What the new pipeline does

- Scrapes Google Maps search results and normalizes the business data into CSV.
- Checks Google Maps for a listed website.
- Runs a second web search for each no-website lead to catch businesses whose site is missing from Google Maps.
- Only treats leads as pitchable when they are `verified_no_website`.
- Generates one demo website per verified no-website lead plus a directory page.
- Exports a CRM-ready CSV for manual calling.
- Syncs a simple local CRM store that tracks call notes, stage, follow-ups, and sales.

## Files

- `scripts/scrape_google_maps.py`: Playwright-based Google Maps scraper.
- `scripts/verify_websites.py`: Re-checks existing leads with the search-based website verifier.
- `scripts/generate_sites.py`: Builds demo sites from structured lead data.
- `scripts/export_crm.py`: Builds the outbound calling list.
- `scripts/run_pipeline.py`: One command to scrape, verify, generate, and export.
- `scripts/sync_crm.py`: Syncs the persistent CRM JSON store from generated leads.
- `scripts/serve_crm.py`: Runs the simple local CRM web app.
- `samples/leads.sample.csv`: Sample lead file for generator testing.
- `samples/queries.sample.csv`: Sample Google Maps query file.
- `crm/`: Browser UI for the simple local CRM.
- `automation/`: Shared models, renderers, and scraper helpers.

## Install

The generator and CRM exporter only use the Python standard library.

The Google Maps scraper needs Playwright in a local virtualenv:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

## Quick Start

Generate sample demo sites without scraping first:

```bash
python3 scripts/generate_sites.py \
  --input samples/leads.sample.csv \
  --output-root generated \
  --output-leads data/leads.generated.csv \
  --site-base-url https://pineapplestocks.github.io/business
```

Export the CRM call list:

```bash
python3 scripts/export_crm.py \
  --input data/leads.generated.csv \
  --output data/crm_to_call.csv
```

Run the full outbound pipeline in one command:

```bash
.venv/bin/python scripts/run_pipeline.py \
  --query-file samples/queries.sample.csv \
  --output-root generated \
  --site-base-url https://pineapplestocks.github.io/business
```

That command now also updates the persistent CRM store at `data/crm_records.json`.

Run only the Google Maps scrape plus website verification:

```bash
.venv/bin/python scripts/scrape_google_maps.py \
  --query-file samples/queries.sample.csv \
  --output data/leads.csv \
  --max-results 20
```

Or run a direct single query and pass the city/state defaults explicitly:

```bash
.venv/bin/python scripts/scrape_google_maps.py \
  --query "landscaper in Tucson AZ" \
  --trade landscaper \
  --city Tucson \
  --state AZ \
  --output data/leads.csv \
  --max-results 20
```

Re-run only the website verification step for an existing lead CSV:

```bash
.venv/bin/python scripts/verify_websites.py \
  --input data/leads.csv \
  --output data/leads.csv
```

Sync the simple local CRM store from generated leads:

```bash
python3 scripts/sync_crm.py \
  --input data/leads.generated.csv \
  --output data/crm_records.json
```

Launch the local CRM in your browser:

```bash
python3 scripts/serve_crm.py \
  --input data/leads.generated.csv \
  --data data/crm_records.json
```

Then open `http://127.0.0.1:8765`.

## Safe Defaults

The generator writes to `generated/` by default so it does not overwrite the current published repo pages.

When you are ready to publish directly into the repo root, point the generator at `--output-root .`.

## Suggested Workflow

1. Scrape new leads into `data/leads.csv`.
2. Let the verifier mark each lead as `found_on_google_maps`, `found_by_search`, `verified_no_website`, or `needs_manual_review`.
3. Review only the `needs_manual_review` rows if you want to be extra careful.
4. Generate demo sites into `generated/` or the repo root.
5. Export `data/crm_to_call.csv`.
6. Open the local CRM and update `pitch_status`, `call_outcome`, notes, follow-ups, and any sale info.

## Notes

- Google Maps markup changes over time, so the scraper is written to be practical rather than guaranteed forever-stable.
- Google Maps alone is not trusted. The pipeline also checks search results before a lead is treated as pitchable.
- The generator and CRM export default to `verified_no_website` leads only.
- The simple CRM is file-backed, not a hosted SaaS. Your notes live in `data/crm_records.json`.
