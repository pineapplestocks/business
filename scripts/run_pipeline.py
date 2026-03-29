#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full outbound pipeline: scrape Google Maps, verify websites via search, "
            "generate demo sites, and export the CRM call list."
        )
    )
    parser.add_argument("--query", action="append", default=[], help="Direct Google Maps query.")
    parser.add_argument("--query-file", type=Path, help="CSV file with headers: query,trade,city,state")
    parser.add_argument("--trade", default="", help="Default trade for direct --query values.")
    parser.add_argument("--city", default="", help="Default city for direct --query values.")
    parser.add_argument("--state", default="", help="Default state for direct --query values.")
    parser.add_argument("--max-results", type=int, default=20, help="Maximum Google Maps results per query.")
    parser.add_argument(
        "--search-results",
        type=int,
        default=5,
        help="Maximum non-directory search results to inspect per verification query.",
    )
    parser.add_argument("--headful", action="store_true", help="Show the browser during scraping.")
    parser.add_argument("--replace", action="store_true", help="Overwrite the lead file instead of merging.")
    parser.add_argument("--leads-output", type=Path, default=Path("data/leads.csv"), help="Verified lead CSV.")
    parser.add_argument(
        "--generated-leads-output",
        type=Path,
        default=Path("data/leads.generated.csv"),
        help="Generated-site lead CSV.",
    )
    parser.add_argument("--crm-output", type=Path, default=Path("data/crm_to_call.csv"), help="CRM export CSV.")
    parser.add_argument(
        "--crm-db-output",
        type=Path,
        default=Path("data/crm.sqlite3"),
        help="Central CRM SQLite database path.",
    )
    parser.add_argument(
        "--crm-snapshot-output",
        type=Path,
        default=Path("data/crm_records.json"),
        help="Public CRM snapshot JSON path used by the static CRM view.",
    )
    parser.add_argument("--output-root", type=Path, default=Path("generated"), help="Generated site root.")
    parser.add_argument("--site-base-url", default="", help="Public base URL for generated pages.")
    return parser.parse_args()


def build_scrape_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "scripts/scrape_google_maps.py",
        "--output",
        str(args.leads_output),
        "--max-results",
        str(args.max_results),
        "--search-results",
        str(args.search_results),
    ]
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
    return command


def run_step(label: str, command: list[str]) -> None:
    print(f"\n[{label}] {' '.join(command)}")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    args = parse_args()
    if not args.query and not args.query_file:
        raise SystemExit("Provide at least one --query or a --query-file.")

    run_step("scrape", build_scrape_command(args))
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
    run_step(
        "crm",
        [
            sys.executable,
            "scripts/export_crm.py",
            "--input",
            str(args.generated_leads_output),
            "--output",
            str(args.crm_output),
        ],
    )
    run_step(
        "crm-sync",
        [
            sys.executable,
            "scripts/sync_crm.py",
            "--input",
            str(args.generated_leads_output),
            "--db",
            str(args.crm_db_output),
            "--snapshot",
            str(args.crm_snapshot_output),
        ],
    )


if __name__ == "__main__":
    main()
