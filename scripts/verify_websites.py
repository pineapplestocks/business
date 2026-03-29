#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import read_leads, write_leads
from automation.website_verifier import WebsiteVerifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the second-pass website check against search results so only real no-website leads "
            "move forward to generation and outbound sales."
        )
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.csv"), help="Input lead CSV.")
    parser.add_argument("--output", type=Path, default=Path("data/leads.csv"), help="Verified lead CSV.")
    parser.add_argument(
        "--search-results",
        type=int,
        default=5,
        help="Maximum non-directory search results to inspect per query.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    leads = read_leads(args.input)
    verifier = WebsiteVerifier(max_results_per_query=args.search_results)
    verified = verifier.verify_leads(leads)
    write_leads(args.output, verified)

    counts = Counter(lead.website_verification_status for lead in verified)
    print(f"Wrote {len(verified)} verified leads to {args.output}")
    print(f"Website verification summary: {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
