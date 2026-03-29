#!/usr/bin/env python3
"""Generate is.gd short URLs for every lead that has a generated_site_url but no short_url."""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import Lead, read_leads, write_leads

ISGD_API = "https://is.gd/create.php"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def shorten(long_url: str) -> str:
    """Return an is.gd short URL. Raises on failure."""
    params = urllib.parse.urlencode({"format": "simple", "url": long_url})
    req = urllib.request.Request(f"{ISGD_API}?{params}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = resp.read().decode().strip()
    if not result.startswith("https://is.gd/"):
        raise ValueError(f"Unexpected is.gd response: {result!r}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add is.gd short URLs to leads that have a generated_site_url."
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"))
    parser.add_argument("--output", type=Path, default=None,
                        help="Output CSV path (default: overwrites input)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be shortened without calling is.gd.")
    parser.add_argument("--delay", type=float, default=1.1,
                        help="Seconds between is.gd requests (default: 1.1).")
    parser.add_argument("--force", action="store_true",
                        help="Re-shorten leads that already have a short_url.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or args.input
    leads = read_leads(args.input)

    need_shortening = [
        lead for lead in leads
        if lead.generated_site_url and (args.force or not lead.short_url)
    ]

    print(f"Leads total: {len(leads)}")
    print(f"Need short URL: {len(need_shortening)}")

    if not need_shortening:
        print("Nothing to do.")
        return

    done = skipped = errors = 0
    for i, lead in enumerate(need_shortening, 1):
        if args.dry_run:
            print(f"  [dry-run] {lead.business_name}: {lead.generated_site_url}")
            done += 1
            continue
        try:
            short = shorten(lead.generated_site_url)
            lead.short_url = short
            done += 1
            if i % 25 == 0 or i == len(need_shortening):
                print(f"  [{i}/{len(need_shortening)}] {lead.business_name} -> {short}")
            if i < len(need_shortening):
                time.sleep(args.delay)
        except Exception as exc:
            errors += 1
            print(f"  [error] {lead.business_name}: {exc}", file=sys.stderr)

    if not args.dry_run:
        write_leads(output, leads)
        print(f"\nDone. Shortened: {done} | Errors: {errors}")
        print(f"Saved to {output}")


if __name__ == "__main__":
    main()
