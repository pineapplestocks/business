#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SITE_BASE_URL = "https://pineapplestocks.github.io/business/generated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full outbound pipeline: scrape Google Maps, verify websites, "
            "generate demo sites, and sync to Zoho CRM."
        )
    )
    parser.add_argument("--query", action="append", default=[], help="Direct Google Maps query.")
    parser.add_argument("--query-file", type=Path, help="CSV file with headers: query,trade,city,state")
    parser.add_argument("--trade", default="", help="Default trade for direct --query values.")
    parser.add_argument("--city", default="", help="Default city for direct --query values.")
    parser.add_argument("--state", default="", help="Default state for direct --query values.")
    parser.add_argument("--max-results", type=int, default=20, help="Maximum Google Maps results per query.")
    parser.add_argument(
        "--scroll-rounds",
        type=int,
        default=12,
        help="How many consecutive no-growth scroll passes to allow before stopping a query.",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1500,
        help="Milliseconds to wait between Google Maps scroll passes.",
    )
    parser.add_argument(
        "--search-results",
        type=int,
        default=5,
        help="Maximum non-directory search results to inspect per verification query.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel Google Maps browser workers to use while scraping queries.",
    )
    parser.add_argument(
        "--auto-workers",
        action="store_true",
        help="Pick a sane worker count automatically from query count and available CPU threads.",
    )
    parser.add_argument("--headful", action="store_true", help="Show the browser during scraping.")
    parser.add_argument("--replace", action="store_true", help="Overwrite the lead file instead of merging.")
    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="Collect as many results as possible by removing the result cap and increasing scroll depth.",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=100,
        help="Checkpoint the lead CSV every N leads. Use 0 to disable.",
    )
    parser.add_argument("--verbose", action="store_true", help="Show extra per-lead verification progress.")
    parser.add_argument("--quiet", action="store_true", help="Reduce terminal progress logging.")
    parser.add_argument("--leads-output", type=Path, default=Path("data/leads.csv"), help="Verified lead CSV.")
    parser.add_argument(
        "--generated-leads-output",
        type=Path,
        default=Path("data/leads.generated.csv"),
        help="Generated-site lead CSV.",
    )
    parser.add_argument(
        "--site-base-url",
        default=DEFAULT_SITE_BASE_URL,
        help=f"Public base URL for generated sites (default: {DEFAULT_SITE_BASE_URL})",
    )
    parser.add_argument("--output-root", type=Path, default=Path("generated"), help="Generated site root.")
    parser.add_argument(
        "--skip-zoho-sync",
        action="store_true",
        help="Skip the Zoho CRM sync step at the end of the pipeline.",
    )
    parser.add_argument(
        "--zoho-dry-run",
        action="store_true",
        help="Run the Zoho sync step in dry-run mode (no API calls).",
    )
    return parser.parse_args()


def build_scrape_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "scripts/scrape_google_maps.py",
        "--output",
        str(args.leads_output),
        "--max-results",
        str(args.max_results),
        "--scroll-rounds",
        str(args.scroll_rounds),
        "--wait-ms",
        str(args.wait_ms),
        "--search-results",
        str(args.search_results),
        "--save-every",
        str(args.save_every),
    ]
    if args.auto_workers:
        command.append("--auto-workers")
    else:
        command.extend(["--workers", str(args.workers)])
    for query in args.query:
        command.extend(["--query", query])
    if args.query_file:
        command.extend(["--query-file", str(args.query_file)])
    if args.trade:
        command.extend(["--trade", args.trade])
    if args.city:
        command.extend(["--city", args.city])
    if args.state:
        command.extend(["--state", args.state])
    if args.headful:
        command.append("--headful")
    if args.replace:
        command.append("--replace")
    if args.exhaustive:
        command.append("--exhaustive")
    if args.verbose:
        command.append("--verbose")
    if args.quiet:
        command.append("--quiet")
    return command


def run_step(label: str, command: list[str]) -> None:
    print(f"\n[{label}] {' '.join(command)}")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    args = parse_args()
    if not args.query and not args.query_file:
        raise SystemExit("Provide at least one --query or a --query-file.")

    # Step 1: Scrape Google Maps + verify websites
    run_step("scrape", build_scrape_command(args))

    # Step 2: Generate static demo sites
    run_step(
        "generate",
        [
            sys.executable,
            "scripts/generate_sites.py",
            "--input",
            str(args.leads_output),
            "--output-root",
            str(args.output_root),
            "--output-leads",
            str(args.generated_leads_output),
            "--site-base-url",
            args.site_base_url,
        ],
    )

    # Step 3: Generate short URLs via is.gd
    run_step(
        "shorten",
        [
            sys.executable,
            "scripts/shorten_links.py",
            "--input",
            str(args.generated_leads_output),
        ],
    )

    # Step 4: Sync to Zoho CRM
    if not args.skip_zoho_sync:
        zoho_cmd = [
            sys.executable,
            "scripts/sync_zoho_crm.py",
            "--input",
            str(args.generated_leads_output),
        ]
        if args.zoho_dry_run:
            zoho_cmd.append("--dry-run")
        run_step("zoho-sync", zoho_cmd)
    else:
        print("\n[zoho-sync] Skipped (--skip-zoho-sync)")


if __name__ == "__main__":
    main()
