#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.crm import crm_stats, sync_crm_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync the simple local CRM store from the generated lead CSV while preserving "
            "notes, deal stage, and call history."
        )
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"), help="Generated lead CSV.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/crm_records.json"),
        help="CRM JSON store path.",
    )
    parser.add_argument(
        "--include-unknown-status",
        action="store_true",
        help="Include unknown-status leads in the CRM store if they otherwise qualify.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = sync_crm_store(
        leads_path=args.input,
        store_path=args.output,
        include_unknown_status=args.include_unknown_status,
    )
    stats = crm_stats(store["records"])
    print(f"Synced CRM store to {args.output}")
    print(f"Active records: {stats['total']}")
    print(f"Won deals: {stats['won']}")
    print(f"Follow-ups scheduled: {stats['follow_up']}")


if __name__ == "__main__":
    main()
