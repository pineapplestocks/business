#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.google_maps import GoogleMapsScraper, SearchQuery
from automation.models import Lead, dedupe_leads, read_leads, write_leads
from automation.website_verifier import WebsiteVerifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Google Maps search results, flag leads with and without websites, "
            "and save normalized lead data to CSV."
        )
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help='Search query, for example: --query "plumber in Salt Lake City UT"',
    )
    parser.add_argument(
        "--query-file",
        type=Path,
        help="CSV file with headers: query,trade,city,state",
    )
    parser.add_argument("--trade", default="", help="Default trade for direct --query values.")
    parser.add_argument("--city", default="", help="Default city for direct --query values.")
    parser.add_argument("--state", default="", help="Default state for direct --query values.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/leads.csv"),
        help="Output CSV path for normalized leads.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum results to collect per query.",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show the browser while scraping instead of using headless mode.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Overwrite the output file instead of merging with existing leads.",
    )
    parser.add_argument(
        "--skip-web-verification",
        action="store_true",
        help="Skip the second website check from search results. Not recommended for production qualification.",
    )
    parser.add_argument(
        "--search-results",
        type=int,
        default=5,
        help="Maximum non-directory search results to inspect per verification query.",
    )
    return parser.parse_args()


def load_queries(args: argparse.Namespace) -> list[SearchQuery]:
    searches: list[SearchQuery] = [
        SearchQuery(query=item, trade=args.trade, city=args.city, state=args.state) for item in args.query
    ]

    if args.query_file:
        with args.query_file.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                query = (row.get("query") or "").strip()
                if not query:
                    continue
                searches.append(
                    SearchQuery(
                        query=query,
                        trade=(row.get("trade") or "").strip(),
                        city=(row.get("city") or "").strip(),
                        state=(row.get("state") or "").strip(),
                    )
                )

    if not searches:
        raise SystemExit("Provide at least one --query or a --query-file.")

    return searches


def main() -> None:
    args = parse_args()
    searches = load_queries(args)

    existing: list[Lead] = []
    if args.output.exists() and not args.replace:
        existing = read_leads(args.output)

    with GoogleMapsScraper(headless=not args.headful, max_results=args.max_results) as scraper:
        scraped = scraper.scrape(searches)

    merged = dedupe_leads([*existing, *scraped])
    if not args.skip_web_verification:
        verifier = WebsiteVerifier(max_results_per_query=args.search_results)
        merged = verifier.verify_leads(merged)

    write_leads(args.output, merged)

    no_website = sum(1 for lead in merged if not lead.has_website)
    open_leads = sum(1 for lead in merged if lead.business_status == "open")
    verification_counts = Counter(lead.website_verification_status for lead in merged)
    verified_no_website = sum(1 for lead in merged if lead.is_verified_no_website())

    print(f"Wrote {len(merged)} total leads to {args.output}")
    print(f"Open leads: {open_leads}")
    print(f"Leads without websites by any check: {no_website}")
    print(f"Verified no-website leads: {verified_no_website}")
    print(f"Website verification summary: {dict(sorted(verification_counts.items()))}")


if __name__ == "__main__":
    main()
