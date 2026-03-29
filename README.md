# business

This repo now contains two layers:

1. The existing static business demo pages already checked into the repo.
2. A new automation pipeline to scrape leads, generate demo sites, and feed Zoho CRM.

## What the new pipeline does

- Scrapes Google Maps search results and normalizes the business data into CSV.
- Checks Google Maps for a listed website.
- Runs a second web search for each no-website lead to catch businesses whose site is missing from Google Maps.
- Only treats leads as pitchable when they are `verified_no_website`.
- Generates one demo website per verified no-website lead plus a directory page.
- Exports a Zoho CRM Leads import CSV so the verified leads can move into a real sales pipeline quickly.

## Files

- `scripts/scrape_google_maps.py`: Playwright-based Google Maps scraper.
- `scripts/verify_websites.py`: Re-checks existing leads with the search-based website verifier.
- `scripts/generate_sites.py`: Builds demo sites from structured lead data.
- `scripts/export_zoho_leads.py`: Builds a Zoho CRM Leads import CSV from the same verified lead set.
- `scripts/run_pipeline.py`: One command to scrape, verify, generate, and export.
- `samples/leads.sample.csv`: Sample lead file for generator testing.
- `samples/queries.sample.csv`: Sample Google Maps query file.
- `automation/`: Shared models, renderers, and scraper helpers.

## Install

The generator and Zoho export scripts use the Python standard library.

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

Export a Zoho-ready leads import file:

```bash
python3 scripts/export_zoho_leads.py \
  --input data/leads.generated.csv \
  --output data/zoho_leads.csv
```

Run the full outbound pipeline in one command:

```bash
.venv/bin/python scripts/run_pipeline.py \
  --query-file samples/queries.sample.csv \
  --output-root generated \
  --site-base-url https://pineapplestocks.github.io/business
```

That command writes a Zoho import file to `data/zoho_leads.csv`.

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

## Zoho CRM

Zoho CRM is the recommended place to manage call notes, follow-ups, pipeline stages, and closed deals.
This repo should focus on lead generation, website verification, and demo-site creation, then hand the qualified leads off to Zoho.

The fastest flow is:

1. Run the generator pipeline so it creates `data/zoho_leads.csv`.
2. In Zoho CRM, import that CSV into the `Leads` module.
3. Map the exported columns to the standard Zoho fields:
   - `Company`
   - `Last Name`
   - `Phone`
   - `Street`
   - `City`
   - `State`
   - `Lead Source`
   - `Lead Status`
   - `Description`
4. Use `Description` to keep the Google Maps link, verification notes, and demo site URL attached to the lead from day one.

If you want to prefill Zoho picklist values during export, pass them into the pipeline:

```bash
.venv/bin/python scripts/run_pipeline.py \
  --query-file samples/queries.sample.csv \
  --output-root generated \
  --site-base-url https://pineapplestocks.github.io/business \
  --zoho-lead-source "Google Maps" \
  --zoho-lead-status "Not Contacted"
```

## Safe Defaults

The generator writes to `generated/` by default so it does not overwrite the current published repo pages.

When you are ready to publish directly into the repo root, point the generator at `--output-root .`.

## Suggested Workflow

1. Scrape new leads into `data/leads.csv`.
2. Let the verifier mark each lead as `found_on_google_maps`, `found_by_search`, `verified_no_website`, or `needs_manual_review`.
3. Review only the `needs_manual_review` rows if you want to be extra careful.
4. Generate demo sites into `generated/` or the repo root.
5. Export or import `data/zoho_leads.csv` into Zoho CRM.
6. Track call notes, follow-ups, and sales in Zoho.

## Notes

- Google Maps markup changes over time, so the scraper is written to be practical rather than guaranteed forever-stable.
- Google Maps alone is not trusted. The pipeline also checks search results before a lead is treated as pitchable.
- The generator and Zoho export default to `verified_no_website` leads only.
- `scripts/export_zoho_leads.py` uses the business name for both `Company` and `Last Name` so the file imports cleanly into Zoho Leads even when you only have business info.
