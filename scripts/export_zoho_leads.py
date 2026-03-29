#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import Lead, read_leads


ZOHO_FIELDS = [
    "Company",
    "Last Name",
    "Phone",
    "Street",
    "City",
    "State",
    "Lead Source",
    "Lead Status",
    "Description",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a Zoho CRM Leads import CSV. By default it only includes open leads "
            "that are verified to have no website and do have a phone number."
        )
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"), help="Input lead CSV.")
    parser.add_argument("--output", type=Path, default=Path("data/zoho_leads.csv"), help="Zoho output CSV.")
    parser.add_argument(
        "--lead-source",
        default="",
        help="Optional Zoho Lead Source value to prefill on every exported row.",
    )
    parser.add_argument(
        "--lead-status",
        default="",
        help="Optional Zoho Lead Status value to prefill on every exported row.",
    )
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


def humanize_trade(value: str) -> str:
    return value.replace("_", " ").strip().title() if value else ""


def filter_pitchable_leads(leads: list[Lead], args: argparse.Namespace) -> list[Lead]:
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
    return filtered


def build_description(lead: Lead) -> str:
    details: list[str] = []
    details.append("Pre-qualified outbound lead from the no-website website pipeline.")

    trade = humanize_trade(lead.trade)
    if trade:
        details.append(f"Trade: {trade}")
    if lead.category:
        details.append(f"Google Maps category: {lead.category}")
    if lead.rating or lead.review_count:
        rating_parts = [part for part in [lead.rating, f"{lead.review_count} reviews" if lead.review_count else ""] if part]
        details.append(f"Reputation: {' | '.join(rating_parts)}")

    details.append(f"Business status: {lead.business_status}")
    details.append(f"Website verification: {lead.website_verification_status}")

    if lead.website_verification_notes:
        details.append(f"Verification notes: {lead.website_verification_notes}")
    if lead.generated_site_url:
        details.append(f"Demo site ready: {lead.generated_site_url}")
    if lead.google_maps_url:
        details.append(f"Google Maps: {lead.google_maps_url}")
    if lead.source_query:
        details.append(f"Source query: {lead.source_query}")
    if lead.notes:
        details.append(f"Internal notes: {lead.notes}")

    return "\n".join(detail for detail in details if detail)


def zoho_row(lead: Lead, *, lead_source: str, lead_status: str) -> dict[str, str]:
    business_name = lead.business_name.strip() or lead.slug or "Local Business"
    return {
        "Company": business_name,
        "Last Name": business_name,
        "Phone": lead.phone,
        "Street": lead.address,
        "City": lead.city,
        "State": lead.state,
        "Lead Source": lead_source,
        "Lead Status": lead_status,
        "Description": build_description(lead),
    }


def main() -> None:
    args = parse_args()
    leads = read_leads(args.input)
    filtered = filter_pitchable_leads(leads, args)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ZOHO_FIELDS)
        writer.writeheader()
        for lead in filtered:
            writer.writerow(
                zoho_row(
                    lead,
                    lead_source=args.lead_source,
                    lead_status=args.lead_status,
                )
            )

    print(f"Wrote {len(filtered)} Zoho lead rows to {args.output}")


if __name__ == "__main__":
    main()
