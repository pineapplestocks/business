#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import read_leads


CRM_FIELDS = [
    "business_name",
    "trade",
    "city",
    "state",
    "phone",
    "category",
    "google_maps_url",
    "generated_site_url",
    "website_verification_status",
    "website_verification_notes",
    "pitch_status",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a CRM-ready CSV for manual calling. By default it only includes open leads "
            "that are verified to have no website and do have a phone number."
        )
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"), help="Input lead CSV.")
    parser.add_argument("--output", type=Path, default=Path("data/crm_to_call.csv"), help="CRM output CSV.")
    parser.add_argument(
        "--include-unknown-status",
        action="store_true",
        help="Include leads with unknown business status in addition to open leads.",
    )
    parser.add_argument(
        "--include-website-leads",
        action="store_true",
        help="Include leads that already have a website.",
    )
    parser.add_argument(
        "--include-unverified-no-website",
        action="store_true",
        help="Include no-website leads even if they still need manual review.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    leads = read_leads(args.input)

    allowed_statuses = {"open"}
    if args.include_unknown_status:
        allowed_statuses.add("unknown")

    filtered = [
        lead
        for lead in leads
        if lead.business_status in allowed_statuses
        and lead.phone
        and (args.include_website_leads or not lead.has_website)
        and (
            args.include_website_leads
            or args.include_unverified_no_website
            or lead.is_verified_no_website()
        )
    ]
    filtered.sort(key=lambda lead: (lead.city, lead.trade, lead.business_name))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CRM_FIELDS)
        writer.writeheader()
        for lead in filtered:
            writer.writerow(
                {
                    "business_name": lead.business_name,
                    "trade": lead.trade,
                    "city": lead.city,
                    "state": lead.state,
                    "phone": lead.phone,
                    "category": lead.category,
                    "google_maps_url": lead.google_maps_url,
                    "generated_site_url": lead.generated_site_url,
                    "website_verification_status": lead.website_verification_status,
                    "website_verification_notes": lead.website_verification_notes,
                    "pitch_status": lead.pitch_status,
                    "notes": lead.notes,
                }
            )

    print(f"Wrote {len(filtered)} CRM rows to {args.output}")


if __name__ == "__main__":
    main()
