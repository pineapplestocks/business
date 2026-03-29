#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from time import strftime

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import Lead, read_leads, write_leads
from automation.website_verifier import WebsiteVerifier


def log_progress(message: str, *, enabled: bool = True) -> None:
    if not enabled:
        return
    timestamp = strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def format_lead_brief(lead: Lead) -> str:
    location = ", ".join(part for part in [lead.city, lead.state] if part)
    trade = lead.trade or lead.category or "local_service"
    phone = f" | {lead.phone}" if lead.phone else ""
    location_text = f" | {location}" if location else ""
    return f"{lead.business_name} | {trade}{location_text}{phone}"


def print_pitchable_preview(leads: list[Lead], *, heading: str, limit: int = 10) -> None:
    if not leads:
        return
    print(heading)
    for lead in leads[:limit]:
        print(f"- {format_lead_brief(lead)}")
    remaining = len(leads) - limit
    if remaining > 0:
        print(f"- ... and {remaining} more")


def print_pitchable_groups(
    leads: list[Lead],
    *,
    heading: str,
    max_groups: int = 8,
    leads_per_group: int = 5,
) -> None:
    if not leads:
        return

    grouped: dict[tuple[str, str, str], list[Lead]] = {}
    for lead in sorted(leads, key=lambda item: (item.city, item.state, item.trade, item.business_name)):
        key = (lead.city, lead.state, lead.trade)
        grouped.setdefault(key, []).append(lead)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1], item[0][2]),
    )

    print(heading)
    for (city, state, trade), group_leads in ranked_groups[:max_groups]:
        location = ", ".join(part for part in [city, state] if part) or "Unknown location"
        print(f"{location} | {trade} ({len(group_leads)})")
        for lead in group_leads[:leads_per_group]:
            phone = f" | {lead.phone}" if lead.phone else ""
            print(f"  - {lead.business_name}{phone}")
        remaining = len(group_leads) - leads_per_group
        if remaining > 0:
            print(f"  - ... and {remaining} more")

    extra_groups = len(ranked_groups) - max_groups
    if extra_groups > 0:
        print(f"... and {extra_groups} more city/trade group(s)")


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
    parser.add_argument(
        "--save-every",
        type=int,
        default=100,
        help="Checkpoint the output CSV every N verified leads. Use 0 to disable.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce terminal progress logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.save_every < 0:
        raise SystemExit("--save-every must be 0 or greater.")

    leads = read_leads(args.input)
    verifier = WebsiteVerifier(max_results_per_query=args.search_results)
    log_progress(
        f"Loaded {len(leads)} lead(s) for website verification.",
        enabled=not args.quiet,
    )

    verified = []
    for index, lead in enumerate(leads, start=1):
        log_progress(f"[verify {index}/{len(leads)}] {lead.business_name}", enabled=not args.quiet)
        verified.append(verifier.verify_lead(lead))
        if args.save_every > 0 and index % args.save_every == 0:
            write_leads(args.output, verified + leads[index:])
            log_progress(
                f"Checkpoint saved to {args.output} after {index} verified lead(s).",
                enabled=not args.quiet,
            )

    write_leads(args.output, verified)
    log_progress(f"Wrote verified leads to {args.output}", enabled=not args.quiet)

    counts = Counter(lead.website_verification_status for lead in verified)
    pitchable = [lead for lead in verified if lead.qualifies_for_pitch()]
    manual_review = [lead for lead in verified if lead.website_verification_status == "needs_manual_review"]
    search_error = [lead for lead in verified if lead.website_verification_status == "search_error"]
    print(f"Wrote {len(verified)} verified leads to {args.output}")
    print(f"Pitchable leads ready now: {len(pitchable)}")
    print(f"Leads needing manual review: {len(manual_review)}")
    print(f"Leads with search errors: {len(search_error)}")
    print(f"Website verification summary: {dict(sorted(counts.items()))}")
    print_pitchable_preview(pitchable, heading="Pitchable no-website leads:")
    print_pitchable_groups(pitchable, heading="Pitchable no-website leads by city/trade:")


if __name__ == "__main__":
    main()
