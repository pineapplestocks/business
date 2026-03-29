#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import Lead, read_leads, write_leads
from automation.render import render_business_page, render_directory_page
from automation.utils import directory_url, ensure_parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate business demo pages plus a directory page from normalized lead data. "
            "By default the output goes to ./generated so the current published pages are not overwritten, "
            "and only verified no-website leads are generated."
        )
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.csv"), help="Input lead CSV.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("generated"),
        help="Root directory for generated HTML output.",
    )
    parser.add_argument(
        "--output-leads",
        type=Path,
        default=Path("data/leads.generated.csv"),
        help="CSV file with generated_site_url and generated_site_path filled in.",
    )
    parser.add_argument(
        "--site-base-url",
        default="",
        help="Optional public base URL for generated sites, for example https://example.com/business",
    )
    parser.add_argument(
        "--include-existing-websites",
        action="store_true",
        help="Generate pages for every lead instead of only the no-website leads.",
    )
    parser.add_argument(
        "--include-unverified-no-website",
        action="store_true",
        help="Generate pages for leads without a website even if they still need manual review.",
    )
    parser.add_argument(
        "--include-non-open",
        action="store_true",
        help="Generate pages even when the business status is not 'open'.",
    )
    return parser.parse_args()


def should_generate(
    lead: Lead,
    include_existing_websites: bool,
    include_unverified_no_website: bool,
    include_non_open: bool,
) -> bool:
    if not include_existing_websites and lead.has_website:
        return False
    if not include_existing_websites and not include_unverified_no_website and not lead.is_verified_no_website():
        return False
    if not include_non_open and lead.business_status != "open":
        return False
    return True


def main() -> None:
    args = parse_args()
    leads = read_leads(args.input)
    args.output_root.mkdir(parents=True, exist_ok=True)

    selected: list[Lead] = []
    for lead in leads:
        if not should_generate(
            lead,
            args.include_existing_websites,
            args.include_unverified_no_website,
            args.include_non_open,
        ):
            continue
        page_path = args.output_root / lead.slug / "index.html"
        lead.generated_site_path = str(page_path)
        lead.generated_site_url = directory_url(args.site_base_url, lead.slug)
        ensure_parent(page_path)
        page_path.write_text(render_business_page(lead), encoding="utf-8")
        selected.append(lead)

    index_path = args.output_root / "index.html"
    index_path.write_text(render_directory_page(selected, args.site_base_url or None), encoding="utf-8")
    write_leads(args.output_leads, selected)

    print(f"Generated {len(selected)} business sites in {args.output_root}")
    print(f"Directory page: {index_path}")
    print(f"Lead export with generated URLs: {args.output_leads}")


if __name__ == "__main__":
    main()
